#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
入库管理 — 文章抓取队列、历史、重试
"""
import sqlite3
import time
import os
from pathlib import Path
from typing import List, Dict, Optional

_default_db = Path(__file__).parent.parent / "data" / "rss.db"
DB_PATH = Path(os.getenv("RSS_DB_PATH", str(_default_db)))


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_ingestion_table():
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ingestion_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fakeid      TEXT NOT NULL DEFAULT '',
                article_link TEXT NOT NULL DEFAULT '',
                title       TEXT NOT NULL DEFAULT '',
                channel     TEXT NOT NULL DEFAULT 'poll',
                status      TEXT NOT NULL DEFAULT 'pending',
                error_msg   TEXT NOT NULL DEFAULT '',
                fail_type   TEXT NOT NULL DEFAULT '',
                next_retry_at REAL NOT NULL DEFAULT 0.0,
                fetcher     TEXT NOT NULL DEFAULT '',
                attempt     INTEGER NOT NULL DEFAULT 0,
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL,
                FOREIGN KEY (fakeid) REFERENCES subscriptions(fakeid) ON DELETE CASCADE
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uq_ingestion_link ON ingestion_logs(fakeid, article_link);
            CREATE INDEX IF NOT EXISTS idx_ingestion_fakeid ON ingestion_logs(fakeid);
            CREATE INDEX IF NOT EXISTS idx_ingestion_status ON ingestion_logs(status);
            CREATE INDEX IF NOT EXISTS idx_ingestion_created ON ingestion_logs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_ingestion_channel ON ingestion_logs(channel);
        """)
        conn.commit()

        # Migration: check and add columns for upgrade compatibility
        cursor = conn.execute("PRAGMA table_info(ingestion_logs)")
        columns = [row[1] for row in cursor.fetchall()]
        if "title" not in columns:
            conn.execute("ALTER TABLE ingestion_logs ADD COLUMN title TEXT NOT NULL DEFAULT ''")
            conn.commit()
        if "article_link" not in columns:
            conn.execute("ALTER TABLE ingestion_logs ADD COLUMN article_link TEXT NOT NULL DEFAULT ''")
            conn.commit()
    finally:
        conn.close()


def log_ingestion_start(fakeid: str, links: List[str], channel: str = "poll") -> int:
    """批量记录入库开始，返回新任务数"""
    conn = _get_conn()
    try:
        now = time.time()
        count = 0
        for link in links:
            conn.execute(
                "INSERT OR IGNORE INTO ingestion_logs (fakeid, article_link, channel, status, created_at, updated_at) "
                "VALUES (?, ?, ?, 'pending', ?, ?)",
                (fakeid, link, channel, now, now),
            )
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def log_ingestion_result(fakeid: str, link: str, success: bool, error_msg: str = "", channel: str = "poll"):
    """记录单篇文章入库结果"""
    conn = _get_conn()
    try:
        now = time.time()
        existing = conn.execute(
            "SELECT id, attempt FROM ingestion_logs WHERE fakeid=? AND article_link=?",
            (fakeid, link),
        ).fetchone()

        if existing:
            new_attempt = existing["attempt"] + 1
            status = "success" if success else "failed_retryable"
            conn.execute(
                "UPDATE ingestion_logs SET status=?, error_msg=?, attempt=?, updated_at=? WHERE id=?",
                (status, error_msg, new_attempt, now, existing["id"]),
            )
        else:
            status = "success" if success else "failed_retryable"
            conn.execute(
                "INSERT INTO ingestion_logs (fakeid, article_link, channel, status, error_msg, attempt, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                (fakeid, link, channel, status, error_msg, now, now),
            )
        conn.commit()
    finally:
        conn.close()


def query_ingestion(fakeid: Optional[str] = None, status: Optional[str] = None,
                    channel: Optional[str] = None, keyword: Optional[str] = None,
                    page: int = 1, per_page: int = 30) -> List[Dict]:
    conn = _get_conn()
    try:
        conditions = ["1=1"]
        params = []

        if fakeid:
            conditions.append("i.fakeid = ?")
            params.append(fakeid)

        if status:
            conditions.append("i.status = ?")
            params.append(status)

        if channel:
            conditions.append("i.channel = ?")
            params.append(channel)

        if keyword:
            conditions.append("(i.article_link LIKE ? OR i.title LIKE ? OR i.error_msg LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])

        where = " AND ".join(conditions)
        offset = (page - 1) * per_page
        params.extend([per_page, offset])

        rows = conn.execute(
            f"SELECT i.*, s.nickname, a.title AS article_title, "
            f"a.digest, a.cover, a.publish_time "
            f"FROM ingestion_logs i "
            f"LEFT JOIN subscriptions s ON i.fakeid = s.fakeid "
            f"LEFT JOIN articles a ON i.fakeid = a.fakeid "
            f"  AND i.article_link = a.link "
            f"WHERE {where} ORDER BY i.updated_at DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_ingestion(fakeid: Optional[str] = None, status: Optional[str] = None,
                    channel: Optional[str] = None, keyword: Optional[str] = None) -> int:
    conn = _get_conn()
    try:
        conditions = ["1=1"]
        params = []

        if fakeid:
            conditions.append("fakeid = ?")
            params.append(fakeid)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if channel:
            conditions.append("channel = ?")
            params.append(channel)

        if keyword:
            conditions.append("(article_link LIKE ? OR title LIKE ? OR error_msg LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])

        where = " AND ".join(conditions)
        row = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM ingestion_logs WHERE {where}", params
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_ingestion_stats() -> Dict:
    """获取入库统计"""
    conn = _get_conn()
    try:
        today_start = time.mktime(time.localtime(time.time())[:3] + (0,0,0,0,0,0))
        total = conn.execute("SELECT COUNT(*) FROM ingestion_logs").fetchone()[0]
        success = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status='success'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status IN ('failed_retryable','failed_permanent')"
        ).fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status IN ('pending','in_progress')"
        ).fetchone()[0]
        today_success = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status='success' AND updated_at >= ?",
            (today_start,)
        ).fetchone()[0]
        today_failed = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status IN ('failed_retryable','failed_permanent') AND updated_at >= ?",
            (today_start,)
        ).fetchone()[0]

        by_channel = {}
        rows = conn.execute(
            "SELECT channel, COUNT(*) AS cnt FROM ingestion_logs GROUP BY channel"
        ).fetchall()
        for r in rows:
            by_channel[r["channel"]] = r["cnt"]

        recent_failures = conn.execute(
            "SELECT * FROM ingestion_logs WHERE status IN ('failed_retryable','failed_permanent') ORDER BY updated_at DESC LIMIT 10"
        ).fetchall()

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "pending": pending,
            "today_success": today_success,
            "today_failed": today_failed,
            "by_channel": by_channel,
            "recent_failures": [dict(r) for r in recent_failures],
        }
    finally:
        conn.close()


def get_dashboard_stats() -> dict:
    """获取看板统计数据"""
    conn = _get_conn()
    try:
        today_start = time.mktime(time.localtime(time.time())[:3] + (0, 0, 0, 0, 0, 0))
        total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        today_ingested = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status='success' AND created_at >= ?",
            (today_start,)
        ).fetchone()[0]
        today_failed = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status='failed_retryable' AND created_at >= ?",
            (today_start,)
        ).fetchone()[0]
        pending_count = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status='pending'"
        ).fetchone()[0]
        subscription_count = conn.execute(
            "SELECT COUNT(*) FROM subscriptions"
        ).fetchone()[0]
        today_active_accounts = conn.execute(
            "SELECT COUNT(DISTINCT fakeid) FROM ingestion_logs WHERE created_at >= ?",
            (today_start,)
        ).fetchone()[0]
        ingestion_rate = 0.0
        t = today_ingested + today_failed
        if t > 0:
            ingestion_rate = round(today_ingested / t, 2)
        recent_failures = conn.execute(
            "SELECT il.*, s.nickname FROM ingestion_logs il "
            "LEFT JOIN subscriptions s ON il.fakeid = s.fakeid "
            "WHERE il.status='failed_retryable' "
            "ORDER BY il.updated_at DESC LIMIT 5"
        ).fetchall()
        return {
            "total_articles": total_articles,
            "today_ingested": today_ingested,
            "today_failed": today_failed,
            "ingestion_rate": ingestion_rate,
            "subscription_count": subscription_count,
            "today_active_accounts": today_active_accounts,
            "pending_count": pending_count,
            "recent_failures": [dict(r) for r in recent_failures],
        }
    finally:
        conn.close()


def get_failed_articles_for_retry(fakeid: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """获取失败的文章链接列表用于重试"""
    conn = _get_conn()
    try:
        if fakeid:
            rows = conn.execute(
                "SELECT DISTINCT fakeid, article_link, channel FROM ingestion_logs "
                "WHERE status='failed_retryable' AND fakeid=? ORDER BY updated_at DESC LIMIT ?",
                (fakeid, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT fakeid, article_link, channel FROM ingestion_logs "
                "WHERE status='failed_retryable' ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def reset_ingestion_status(fakeid: str, link: str):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE ingestion_logs SET status='pending', error_msg='', updated_at=? WHERE fakeid=? AND article_link=?",
            (time.time(), fakeid, link),
        )
        conn.commit()
    finally:
        conn.close()


def ban_article(fakeid: str, article_link: str):
    """标记文章为永久禁止入库"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE ingestion_logs SET status='failed_permanent', fail_type='manual_banned', updated_at=? "
            "WHERE fakeid=? AND article_link=?",
            (time.time(), fakeid, article_link),
        )
        conn.commit()
    finally:
        conn.close()


def unban_article(fakeid: str, article_link: str):
    """解除禁止，重置为 pending"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE ingestion_logs SET status='pending', fail_type='', attempt=0, next_retry_at=0, updated_at=? "
            "WHERE fakeid=? AND article_link=?",
            (time.time(), fakeid, article_link),
        )
        conn.commit()
    finally:
        conn.close()

def get_next_task() -> Optional[Dict]:
    """Worker 调度查询 — 取一篇待抓取的最早文章"""
    conn = _get_conn()
    try:
        now = time.time()
        row = conn.execute(
            "SELECT * FROM ingestion_logs "
            "WHERE status IN ('pending', 'failed_retryable') "
            "  AND next_retry_at <= ? "
            "ORDER BY "
            "  CASE channel WHEN 'poll' THEN 0 WHEN 'manual' THEN 1 "
            "    WHEN 'deep_fetch' THEN 2 END, "
            "  next_retry_at ASC "
            "LIMIT 1",
            (now,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_in_progress(fakeid: str, article_link: str):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE ingestion_logs SET status='in_progress', updated_at=? "
            "WHERE fakeid=? AND article_link=?",
            (time.time(), fakeid, article_link),
        )
        conn.commit()
    finally:
        conn.close()


def mark_success(fakeid: str, article_link: str, fetcher: str = ""):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE ingestion_logs SET status='success', fail_type='', "
            "fetcher=?, attempt=attempt+1, updated_at=? "
            "WHERE fakeid=? AND article_link=?",
            (fetcher, time.time(), fakeid, article_link),
        )
        conn.commit()
    finally:
        conn.close()


def mark_failure(fakeid: str, article_link: str, fail_type: str,
                 next_retry_at: float, is_permanent: bool = False,
                 fetcher: str = ""):
    conn = _get_conn()
    try:
        status = "failed_permanent" if is_permanent else "failed_retryable"
        conn.execute(
            "UPDATE ingestion_logs SET status=?, fail_type=?, "
            "fetcher=?, attempt=attempt+1, next_retry_at=?, updated_at=? "
            "WHERE fakeid=? AND article_link=?",
            (status, fail_type, fetcher, next_retry_at, time.time(), fakeid, article_link),
        )
        conn.commit()
    finally:
        conn.close()


def reset_for_retry(fakeid: str, article_link: str, fetcher: str = ""):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE ingestion_logs SET status='pending', fail_type='', "
            "attempt=0, next_retry_at=0, fetcher=?, updated_at=? "
            "WHERE fakeid=? AND article_link=?",
            (fetcher, time.time(), fakeid, article_link),
        )
        conn.commit()
    finally:
        conn.close()


def recover_stalled_in_progress(timeout_minutes: int = 15) -> int:
    conn = _get_conn()
    try:
        cutoff = time.time() - timeout_minutes * 60
        rows = conn.execute(
            "SELECT fakeid, article_link FROM ingestion_logs "
            "WHERE status='in_progress' AND updated_at < ?",
            (cutoff,),
        ).fetchall()
        count = 0
        for r in rows:
            conn.execute(
                "UPDATE ingestion_logs SET status='failed_retryable', "
                "fail_type='network_error', updated_at=? "
                "WHERE fakeid=? AND article_link=?",
                (time.time(), r["fakeid"], r["article_link"]),
            )
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def extend_retry(fakeid: str, article_link: str, seconds: int = 30):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE ingestion_logs SET next_retry_at=?, updated_at=? "
            "WHERE fakeid=? AND article_link=?",
            (time.time() + seconds, time.time(), fakeid, article_link),
        )
        conn.commit()
    finally:
        conn.close()


def pending_count() -> int:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM ingestion_logs "
            "WHERE status IN ('pending', 'failed_retryable') AND next_retry_at <= ?",
            (time.time(),),
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def pending_per_fakeid() -> List[Dict]:
    conn = _get_conn()
    try:
        now = time.time()
        rows = conn.execute(
            "SELECT i.fakeid, s.nickname, COUNT(*) AS cnt FROM ingestion_logs i "
            "INNER JOIN subscriptions s ON i.fakeid = s.fakeid "
            "WHERE i.status IN ('pending', 'failed_retryable') "
            "  AND i.next_retry_at <= ? "
            "GROUP BY i.fakeid "
            "ORDER BY cnt DESC",
            (now,),
        ).fetchall()
        return [{"fakeid": r["fakeid"], "nickname": r["nickname"] or r["fakeid"], "count": r["cnt"]} for r in rows]
    finally:
        conn.close()


def cleanup_old_ingestion(retain_days: int = 30):
    cutoff = time.time() - retain_days * 86400
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM ingestion_logs WHERE created_at < ?", (cutoff,))
        deleted = conn.execute("SELECT changes()").fetchone()[0]
        conn.commit()
        return deleted
    finally:
        conn.close()
