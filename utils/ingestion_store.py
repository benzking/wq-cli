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
                attempt     INTEGER NOT NULL DEFAULT 0,
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL,
                FOREIGN KEY (fakeid) REFERENCES subscriptions(fakeid) ON DELETE CASCADE
            );
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
            status = "success" if success else "failed"
            conn.execute(
                "UPDATE ingestion_logs SET status=?, error_msg=?, attempt=?, updated_at=? WHERE id=?",
                (status, error_msg, new_attempt, now, existing["id"]),
            )
        else:
            status = "success" if success else "failed"
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
            f"SELECT i.*, s.nickname FROM ingestion_logs i "
            f"LEFT JOIN subscriptions s ON i.fakeid = s.fakeid "
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
        total = conn.execute("SELECT COUNT(*) FROM ingestion_logs").fetchone()[0]
        success = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status='success'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status='failed'"
        ).fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM ingestion_logs WHERE status='pending'"
        ).fetchone()[0]

        by_channel = {}
        rows = conn.execute(
            "SELECT channel, COUNT(*) AS cnt FROM ingestion_logs GROUP BY channel"
        ).fetchall()
        for r in rows:
            by_channel[r["channel"]] = r["cnt"]

        recent_failures = conn.execute(
            "SELECT * FROM ingestion_logs WHERE status='failed' ORDER BY updated_at DESC LIMIT 10"
        ).fetchall()

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "pending": pending,
            "by_channel": by_channel,
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
                "WHERE status='failed' AND fakeid=? ORDER BY updated_at DESC LIMIT ?",
                (fakeid, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT fakeid, article_link, channel FROM ingestion_logs "
                "WHERE status='failed' ORDER BY updated_at DESC LIMIT ?",
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
