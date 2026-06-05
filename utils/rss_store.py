#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
RSS 数据存储 — SQLite
管理订阅列表和文章缓存
"""

import sqlite3
import time
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Database path: configurable via env var, defaults to ./data/rss.db
_default_db = Path(__file__).parent.parent / "data" / "rss.db"
DB_PATH = Path(os.getenv("RSS_DB_PATH", str(_default_db)))


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """建表（幂等）"""
    conn = _get_conn()
    
    # 先创建不依赖其他表的基础表
    conn.executescript("""
        -- 分类表（先创建，因为 subscriptions 依赖它）
        CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            color       TEXT NOT NULL DEFAULT 'blue',
            sort_order  INTEGER NOT NULL DEFAULT 0,
            created_at  INTEGER NOT NULL
        );
        
        -- 黑名单表
        CREATE TABLE IF NOT EXISTS fakeid_blacklist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fakeid      TEXT NOT NULL UNIQUE,
            nickname    TEXT NOT NULL DEFAULT '',
            reason      TEXT NOT NULL DEFAULT 'manual',
            verification_count INTEGER NOT NULL DEFAULT 0,
            is_active   INTEGER NOT NULL DEFAULT 1,
            blacklisted_at INTEGER NOT NULL,
            unblacklisted_at INTEGER DEFAULT NULL,
            note        TEXT NOT NULL DEFAULT ''
        );
        
        CREATE INDEX IF NOT EXISTS idx_blacklist_active ON fakeid_blacklist(is_active);
    """)
    conn.commit()
    
    # 检查 subscriptions 表是否存在
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='subscriptions'"
    )
    table_exists = cursor.fetchone() is not None
    
    if table_exists:
        # 表已存在，检查是否有 category_id 列
        cursor = conn.execute("PRAGMA table_info(subscriptions)")
        columns = [row[1] for row in cursor.fetchall()]
        if "category_id" not in columns:
            # 添加 category_id 列
            conn.execute("ALTER TABLE subscriptions ADD COLUMN category_id INTEGER DEFAULT NULL")
            conn.commit()
            logger.info("Added category_id column to subscriptions table")
    else:
        # 表不存在，创建新表
        conn.executescript("""
            CREATE TABLE subscriptions (
                fakeid      TEXT PRIMARY KEY,
                nickname    TEXT NOT NULL DEFAULT '',
                alias       TEXT NOT NULL DEFAULT '',
                head_img    TEXT NOT NULL DEFAULT '',
                category_id INTEGER DEFAULT NULL,
                created_at  INTEGER NOT NULL,
                last_poll   INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            );
        """)
        conn.commit()
    
    # 创建 articles 表
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fakeid      TEXT NOT NULL,
            aid         TEXT NOT NULL DEFAULT '',
            title       TEXT NOT NULL DEFAULT '',
            link        TEXT NOT NULL DEFAULT '',
            digest      TEXT NOT NULL DEFAULT '',
            cover       TEXT NOT NULL DEFAULT '',
            author      TEXT NOT NULL DEFAULT '',
            content     TEXT NOT NULL DEFAULT '',
            plain_content TEXT NOT NULL DEFAULT '',
            publish_time INTEGER NOT NULL DEFAULT 0,
            fetched_at  INTEGER NOT NULL,
            UNIQUE(fakeid, link),
            FOREIGN KEY (fakeid) REFERENCES subscriptions(fakeid) -- 不设 CASCADE，取消订阅保留缓存
        );

        CREATE INDEX IF NOT EXISTS idx_articles_fakeid_time
            ON articles(fakeid, publish_time DESC);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_category ON subscriptions(category_id);
    """)
    conn.commit()

    # 检查并添加后续新增的列
    cursor = conn.execute("PRAGMA table_info(articles)")
    columns = [row[1] for row in cursor.fetchall()]
    if "starred" not in columns:
        logger.info("Adding starred column to articles table")
        conn.execute("ALTER TABLE articles ADD COLUMN starred INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    if "images_localized" not in columns:
        logger.info("Adding images_localized column to articles table")
        conn.execute("ALTER TABLE articles ADD COLUMN images_localized INTEGER NOT NULL DEFAULT 0")
        conn.commit()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL DEFAULT '',
            updated_at INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            fakeid       TEXT PRIMARY KEY,
            nickname     TEXT NOT NULL DEFAULT '',
            head_img     TEXT NOT NULL DEFAULT '',
            alias        TEXT NOT NULL DEFAULT '',
            token        TEXT NOT NULL DEFAULT '',
            cookie       TEXT NOT NULL DEFAULT '',
            expire_time  INTEGER NOT NULL DEFAULT 0,
            login_time   REAL NOT NULL DEFAULT 0,
            is_active    INTEGER NOT NULL DEFAULT 0,
            created_at   REAL NOT NULL DEFAULT (unixepoch()),
            updated_at   REAL NOT NULL DEFAULT (unixepoch())
        );

        CREATE INDEX IF NOT EXISTS idx_accounts_active ON accounts(is_active);
    """)
    conn.commit()

    conn.close()
    logger.info("RSS database initialized: %s", DB_PATH)


# ── 配置管理 ─────────────────────────────────────────────


def get_config(key: str) -> Optional[str]:
    """读取配置值，不存在返回 None"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM config WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_config(key: str, value: str) -> bool:
    """写入配置（upsert），返回是否成功"""
    import time
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO config (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, int(time.time())),
        )
        conn.commit()
        return True
    finally:
        conn.close()


# ── 订阅管理 ─────────────────────────────────────────────

def add_subscription(fakeid: str, nickname: str = "",
                     alias: str = "", head_img: str = "") -> bool:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO subscriptions "
            "(fakeid, nickname, alias, head_img, created_at) VALUES (?,?,?,?,?)",
            (fakeid, nickname, alias, head_img, int(time.time())),
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def remove_subscription(fakeid: str) -> bool:
    """取消订阅——仅删除 subscriptions 记录，保留 articles 缓存"""
    conn = _get_conn()
    try:
        # 临时关闭外键约束，避免已有数据库 ON DELETE CASCADE 误删数据
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DELETE FROM subscriptions WHERE fakeid=?", (fakeid,))
        conn.execute("PRAGMA foreign_keys=ON")
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def list_subscriptions() -> List[Dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT s.*, c.name AS category_name, "
            "(SELECT COUNT(*) FROM articles a WHERE a.fakeid=s.fakeid) AS article_count "
            "FROM subscriptions s "
            "LEFT JOIN categories c ON s.category_id = c.id "
            "ORDER BY s.created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_subscription(fakeid: str) -> Optional[Dict]:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE fakeid=?", (fakeid,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def article_exists(fakeid: str, link: str) -> bool:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM articles WHERE fakeid=? AND link=?", (fakeid, link)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def update_last_poll(fakeid: str):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE subscriptions SET last_poll=? WHERE fakeid=?",
            (int(time.time()), fakeid),
        )
        conn.commit()
    finally:
        conn.close()


# ── 文章缓存 ─────────────────────────────────────────────

def save_articles(fakeid: str, articles: List[Dict]) -> int:
    """
    批量保存文章，返回新增数量。
    If an article already exists but has empty content, update it with new content.
    """
    conn = _get_conn()
    inserted = 0
    try:
        for a in articles:
            content = a.get("content", "")
            plain_content = a.get("plain_content", "")
            try:
                cursor = conn.execute(
                    "INSERT INTO articles "
                    "(fakeid, aid, title, link, digest, cover, author, "
                    "content, plain_content, publish_time, fetched_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(fakeid, link) DO UPDATE SET "
                    "content = CASE WHEN excluded.content != '' AND articles.content = '' "
                    "  THEN excluded.content ELSE articles.content END, "
                    "plain_content = CASE WHEN excluded.plain_content != '' AND articles.plain_content = '' "
                    "  THEN excluded.plain_content ELSE articles.plain_content END, "
                    "author = CASE WHEN excluded.author != '' AND articles.author = '' "
                    "  THEN excluded.author ELSE articles.author END",
                    (
                        fakeid,
                        a.get("aid", ""),
                        a.get("title", ""),
                        a.get("link", ""),
                        a.get("digest", ""),
                        a.get("cover", ""),
                        a.get("author", ""),
                        content,
                        plain_content,
                        a.get("publish_time", 0),
                        int(time.time()),
                    ),
                )
                if cursor.rowcount > 0:
                    inserted += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        return inserted
    finally:
        conn.close()


def get_articles(fakeid: str, limit: int = 20) -> List[Dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM articles WHERE fakeid=? "
            "ORDER BY publish_time DESC LIMIT ?",
            (fakeid, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_regular_articles(fakeid: str, limit: int = 50) -> List[Dict]:
    """
    获取常规文章（轮询器拉取的文章）
    通过 JOIN ingestion_logs 获取 channel='poll' 的文章
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT a.* FROM articles a "
            "INNER JOIN ingestion_logs il ON a.fakeid = il.fakeid AND a.link = il.article_link "
            "WHERE a.fakeid=? AND il.channel='poll' "
            "ORDER BY a.publish_time DESC LIMIT ?",
            (fakeid, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_historical_articles(fakeid: str, limit: int = 500, offset: int = 0) -> List[Dict]:
    """
    获取历史文章（通过"获取历史文章"功能拉取的文章）
    通过 JOIN ingestion_logs 获取 channel='deep_fetch' 的文章，支持分页
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT a.* FROM articles a "
            "INNER JOIN ingestion_logs il ON a.fakeid = il.fakeid AND a.link = il.article_link "
            "WHERE a.fakeid=? AND il.channel='deep_fetch' "
            "ORDER BY a.publish_time DESC LIMIT ? OFFSET ?",
            (fakeid, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_historical_articles(fakeid: str) -> int:
    """统计历史文章数量（channel='deep_fetch'的文章）"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(DISTINCT a.id) as cnt FROM articles a "
            "INNER JOIN ingestion_logs il ON a.fakeid = il.fakeid AND a.link = il.article_link "
            "WHERE a.fakeid=? AND il.channel='deep_fetch'",
            (fakeid,),
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def count_pending_articles(fakeid: str) -> int:
    """统计待入库文章数 — ingestion_logs 中 status='pending' 的数量"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM ingestion_logs "
            "WHERE fakeid=? AND status='pending'",
            (fakeid,),
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_all_fakeids() -> List[str]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT fakeid FROM subscriptions").fetchall()
        return [r["fakeid"] for r in rows]
    finally:
        conn.close()


def get_all_articles(limit: int = 50) -> List[Dict]:
    """
    获取所有订阅的常规文章（聚合RSS）
    只返回轮询器拉取的文章（source='poll'），不包含历史文章
    
    [2026-05-06 优化] 使用窗口函数实现"每号限额 + 总数限制"策略：
    - 根据订阅数量动态调整每个号的文章数限制
    - 保证每个订阅号都有文章显示（避免活跃号占满）
    - 单订阅场景与单个 RSS 保持一致
    """
    conn = _get_conn()
    try:
        # 获取所有订阅的fakeid
        subs = conn.execute("SELECT fakeid FROM subscriptions").fetchall()
        if not subs:
            return []
        
        fakeid_list = [s["fakeid"] for s in subs]
        subscription_count = len(fakeid_list)
        
        # 根据订阅数量计算动态限制
        per_sub_limit, total_limit = _calculate_aggregated_limits(subscription_count)
        
        # 使用实际的 limit 参数作为总数上限（用户可自定义）
        total_limit = min(limit, total_limit)
        
        placeholders = ",".join("?" * len(fakeid_list))
        
        # 使用窗口函数：每个订阅号最多 N 篇，总共最多 M 篇
        rows = conn.execute(
            f"""
            WITH ranked_articles AS (
                SELECT
                    a.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY a.fakeid
                        ORDER BY a.publish_time DESC
                    ) AS rn
                FROM articles a
                INNER JOIN ingestion_logs il ON a.fakeid = il.fakeid AND a.link = il.article_link
                WHERE a.fakeid IN ({placeholders}) AND il.channel='poll'
            )
            SELECT * FROM ranked_articles
            WHERE rn <= ?
            ORDER BY publish_time DESC
            LIMIT ?
            """,
            (*fakeid_list, per_sub_limit, total_limit),
        ).fetchall()

        return [dict(r) for r in rows]
    finally:
        conn.close()


def _calculate_aggregated_limits(subscription_count: int) -> tuple:
    """
    根据订阅数量动态计算聚合 RSS 的限制策略
    
    Args:
        subscription_count: 订阅数量
    
    Returns:
        (per_sub_limit, total_limit): 每个订阅号的限额、总数上限
    
    策略设计：
    - 每个订阅号统一 30 篇
    - total_limit = subscription_count * 30（精确计算）
    - 最高支持 4500 篇（150 订阅 * 30）
    """
    if subscription_count == 0:
        return (0, 0)
    
    per_sub_limit = 30
    total_limit = subscription_count * 30
    
    # 上限：4500 篇（对应 150 个订阅）
    if total_limit > 4500:
        total_limit = 4500
    
    return (per_sub_limit, total_limit)


# ── 黑名单管理 ─────────────────────────────────────────────

def add_to_blacklist(fakeid: str, nickname: str = "", reason: str = "manual",
                     verification_count: int = 0, note: str = "") -> bool:
    """添加公众号到黑名单"""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO fakeid_blacklist "
            "(fakeid, nickname, reason, verification_count, is_active, blacklisted_at, note) "
            "VALUES (?,?,?,?,1,?,?)",
            (fakeid, nickname, reason, verification_count, int(time.time()), note),
        )
        conn.commit()
        logger.info("Added %s to blacklist: %s", fakeid[:8], reason)
        return True
    finally:
        conn.close()


def remove_from_blacklist(fakeid: str) -> bool:
    """从黑名单移除（标记为非活跃）"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE fakeid_blacklist SET is_active=0, unblacklisted_at=? WHERE fakeid=?",
            (int(time.time()), fakeid),
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def delete_blacklist_record(blacklist_id: int) -> bool:
    """永久删除黑名单记录"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM fakeid_blacklist WHERE id=? AND is_active=0", (blacklist_id,))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def is_blacklisted(fakeid: str) -> bool:
    """检查公众号是否在黑名单中"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM fakeid_blacklist WHERE fakeid=? AND is_active=1",
            (fakeid,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def get_blacklist() -> List[Dict]:
    """获取黑名单列表"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM fakeid_blacklist ORDER BY blacklisted_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_active_blacklist_fakeids() -> List[str]:
    """获取活跃黑名单的 fakeid 列表"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT fakeid FROM fakeid_blacklist WHERE is_active=1"
        ).fetchall()
        return [r["fakeid"] for r in rows]
    finally:
        conn.close()


def increment_verification_count(fakeid: str, nickname: str = "") -> int:
    """
    增加验证码触发次数，达到阈值时自动加入黑名单

    [2026-05-18 优化]
    1. 阈值 5 → 8（避免误判，配合精确化 verification 检测后误报率本就低）
    2. 修复隐藏 bug：之前 UPDATE 强制 is_active=1 → admin 手动取消后，下次触发又被自动激活
       现在：仅在「跨阈值的瞬间」激活；已激活/已被 admin 取消的状态保持不变

    注意：本计数为永久累计（无 24h 窗口）。误判的 fakeid 可通过 remove_from_blacklist
    或 delete_blacklist_record 手动清理（开源版简化设计，不引入 PG/Redis）

    返回：当前触发次数
    """
    threshold = 8
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM fakeid_blacklist WHERE fakeid=?", (fakeid,)
        ).fetchone()

        if row:
            new_count = row["verification_count"] + 1
            crossing_threshold = (
                row["verification_count"] < threshold <= new_count
                and not row["is_active"]
            )
            if crossing_threshold:
                # 首次跨过阈值：激活拉黑
                conn.execute(
                    "UPDATE fakeid_blacklist SET verification_count=?, is_active=1, "
                    "blacklisted_at=?, note=? WHERE fakeid=?",
                    (new_count, int(time.time()),
                     f"自动记录: 触发验证码 {new_count} 次（达到阈值 {threshold}）",
                     fakeid),
                )
            else:
                # 仅累计计数，不动 is_active（保留 admin 手动取消的状态）
                conn.execute(
                    "UPDATE fakeid_blacklist SET verification_count=? WHERE fakeid=?",
                    (new_count, fakeid),
                )
        else:
            new_count = 1
            conn.execute(
                "INSERT INTO fakeid_blacklist "
                "(fakeid, nickname, reason, verification_count, is_active, blacklisted_at, note) "
                "VALUES (?,?,?,?,?,?,?)",
                (fakeid, nickname, "high_verification", new_count,
                 1 if new_count >= threshold else 0,
                 int(time.time()),
                 f"自动记录: 触发验证码 {new_count} 次"),
            )

        conn.commit()

        if new_count >= threshold:
            logger.warning("Fakeid %s reached %d verification triggers (threshold=%d)",
                          fakeid[:8], new_count, threshold)

        return new_count
    finally:
        conn.close()


# ── 分类管理 ─────────────────────────────────────────────

def create_category(name: str, description: str = "", color: str = "blue") -> Optional[int]:
    """创建分类，返回新分类 ID"""
    conn = _get_conn()
    try:
        # 获取最大 sort_order
        row = conn.execute("SELECT MAX(sort_order) as max_order FROM categories").fetchone()
        max_order = row["max_order"] or 0
        
        cursor = conn.execute(
            "INSERT INTO categories (name, description, color, sort_order, created_at) "
            "VALUES (?,?,?,?,?)",
            (name, description, color, max_order + 1, int(time.time())),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def update_category(category_id: int, name: str = None, 
                    description: str = None, color: str = None) -> bool:
    """更新分类"""
    conn = _get_conn()
    try:
        updates = []
        params = []
        if name is not None:
            updates.append("name=?")
            params.append(name)
        if description is not None:
            updates.append("description=?")
            params.append(description)
        if color is not None:
            updates.append("color=?")
            params.append(color)
        
        if not updates:
            return False
        
        params.append(category_id)
        conn.execute(
            f"UPDATE categories SET {', '.join(updates)} WHERE id=?",
            params,
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def delete_category(category_id: int) -> bool:
    """删除分类（订阅会自动解除关联）"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM categories WHERE id=?", (category_id,))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def list_categories() -> List[Dict]:
    """获取所有分类及其订阅数"""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT c.*, 
                   (SELECT COUNT(*) FROM subscriptions s WHERE s.category_id=c.id) AS subscription_count
            FROM categories c 
            ORDER BY c.sort_order, c.created_at
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_category(category_id: int) -> Optional[Dict]:
    """获取单个分类"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM categories WHERE id=?", (category_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_subscription_category(fakeid: str, category_id: Optional[int]) -> bool:
    """设置订阅的分类"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE subscriptions SET category_id=? WHERE fakeid=?",
            (category_id, fakeid),
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def get_subscriptions_by_category(category_id: int) -> List[Dict]:
    """获取分类下的所有订阅"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT s.*, "
            "(SELECT COUNT(*) FROM articles a WHERE a.fakeid=s.fakeid) AS article_count "
            "FROM subscriptions s WHERE s.category_id=? ORDER BY s.created_at DESC",
            (category_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_articles_by_category(category_id: int, limit: int = 50) -> List[Dict]:
    """
    获取分类下所有订阅的常规文章
    只返回轮询器拉取的文章（source='poll'），不包含历史文章
    
    [2026-05-06 优化] 使用窗口函数实现"每号限额 + 总数限制"策略
    """
    conn = _get_conn()
    try:
        # 获取该分类下的所有fakeid
        subs = conn.execute(
            "SELECT fakeid FROM subscriptions WHERE category_id=?",
            (category_id,)
        ).fetchall()
        if not subs:
            return []
        
        fakeid_list = [s["fakeid"] for s in subs]
        subscription_count = len(fakeid_list)
        
        # [2026-05-06 优化] 使用窗口函数实现"每号限额 + 总数限制"策略
        # 根据订阅数量计算动态限制
        per_sub_limit, total_limit = _calculate_aggregated_limits(subscription_count)
        # 使用实际的 limit 参数作为总数上限（用户可自定义）
        total_limit = min(limit, total_limit)
        
        placeholders = ",".join("?" * len(fakeid_list))
        
        # 使用窗口函数：每个订阅号最多 N 篇，总共最多 M 篇
        rows = conn.execute(
            f"""
            WITH ranked_articles AS (
                SELECT
                    a.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY a.fakeid
                        ORDER BY a.publish_time DESC
                    ) AS rn
                FROM articles a
                INNER JOIN ingestion_logs il ON a.fakeid = il.fakeid AND a.link = il.article_link
                WHERE a.fakeid IN ({placeholders}) AND il.channel='poll'
            )
            SELECT * FROM ranked_articles
            WHERE rn <= ?
            ORDER BY publish_time DESC
            LIMIT ?
            """,
            (*fakeid_list, per_sub_limit, total_limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def browse_articles(fakeid: Optional[str] = None, page: int = 1, per_page: int = 20,
                    keyword: Optional[str] = None) -> List[Dict]:
    """浏览已存储的文章（分页、筛选、搜索）"""
    conn = _get_conn()
    try:
        conditions = ["1=1"]
        params = []

        if fakeid:
            conditions.append("fakeid = ?")
            params.append(fakeid)

        if keyword:
            conditions.append("(title LIKE ? OR digest LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw])

        where = " AND ".join(conditions)

        offset = (page - 1) * per_page
        params.extend([per_page, offset])

        rows = conn.execute(
            f"SELECT id, fakeid, title, link, digest, cover, author, publish_time, fetched_at "
            f"FROM articles WHERE {where} ORDER BY publish_time DESC, id DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_articles(fakeid: Optional[str] = None, keyword: Optional[str] = None) -> int:
    """统计文章总数（用于分页）"""
    conn = _get_conn()
    try:
        conditions = ["1=1"]
        params = []

        if fakeid:
            conditions.append("fakeid = ?")
            params.append(fakeid)

        if keyword:
            conditions.append("(title LIKE ? OR digest LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw])

        where = " AND ".join(conditions)
        row = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM articles WHERE {where}", params
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_article_by_id(article_id: int) -> Optional[Dict]:
    """获取文章完整内容"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_subscriptions_with_articles() -> List[Dict]:
    """获取有文章缓存的订阅列表（带文章计数）"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT s.fakeid, s.nickname, s.alias, s.head_img, "
            "COUNT(a.id) AS article_count "
            "FROM subscriptions s "
            "INNER JOIN articles a ON a.fakeid = s.fakeid "
            "GROUP BY s.fakeid "
            "ORDER BY article_count DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def toggle_star(article_id: int):
    """切换文章星标，返回新的 starred 状态"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT starred FROM articles WHERE id=?", (article_id,)
        ).fetchone()
        if not row:
            return None
        new_val = 1 if not row[0] else 0
        conn.execute(
            "UPDATE articles SET starred=? WHERE id=?", (new_val, article_id)
        )
        conn.commit()
        return bool(new_val)
    finally:
        conn.close()


def init_image_queue_table():
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS image_download_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                local_path TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                attempt INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_iq_status ON image_download_queue(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_iq_article ON image_download_queue(article_id)")
        conn.commit()
    finally:
        conn.close()


def queue_images(article_id: int, image_urls: list):
    conn = _get_conn()
    try:
        _now = time.time()
        for url in image_urls:
            conn.execute(
                "INSERT INTO image_download_queue (article_id, image_url, status, created_at, updated_at) "
                "VALUES (?, ?, 'pending', ?, ?)",
                (article_id, url, _now, _now)
            )
        conn.commit()
    finally:
        conn.close()


def get_pending_images(limit: int = 5) -> list:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM image_download_queue WHERE status='pending' "
            "ORDER BY created_at ASC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_image_done(queue_id: int, local_path: str):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE image_download_queue SET status='done', local_path=?, updated_at=? WHERE id=?",
            (local_path, time.time(), queue_id)
        )
        conn.commit()
    finally:
        conn.close()


def mark_image_failed(queue_id: int):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE image_download_queue SET status='failed', attempt=attempt+1, updated_at=? WHERE id=?",
            (time.time(), queue_id)
        )
        conn.commit()
    finally:
        conn.close()


def replace_article_images(article_id: int, mapping: dict) -> bool:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT content FROM articles WHERE id=?", (article_id,)).fetchone()
        if not row:
            return False
        content = row[0] or ""
        # 按 URL 长度降序替换，防止短 URL 是长 URL 的子串导致内容损坏
        for url, local in sorted(mapping.items(), key=lambda x: -len(x[0])):
            content = content.replace(url, f"/static/images/{article_id}/{local}")
        conn.execute("UPDATE articles SET content=?, images_localized=1 WHERE id=?", (content, article_id))
        conn.commit()
        return True
    finally:
        conn.close()


def get_image_queue_stats() -> dict:
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM image_download_queue").fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM image_download_queue WHERE status='pending'"
        ).fetchone()[0]
        done = conn.execute(
            "SELECT COUNT(*) FROM image_download_queue WHERE status='done'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM image_download_queue WHERE status='failed'"
        ).fetchone()[0]
        return {"total": total, "pending": pending, "done": done, "failed": failed}
    finally:
        conn.close()


# ── 账号管理 ─────────────────────────────────────────────

def upsert_account(fakeid: str, nickname: str = "", head_img: str = "",
                   alias: str = "", token: str = "", cookie: str = "",
                   expire_time: int = 0) -> bool:
    """插入或更新账号记录，设置 is_active=1，同时将其他账号 is_active 置 0"""
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE accounts SET is_active=0, updated_at=unixepoch() WHERE is_active=1")
        conn.execute(
            "INSERT INTO accounts (fakeid, nickname, head_img, alias, token, cookie, expire_time, login_time, is_active) "
            "VALUES (?,?,?,?,?,?,?,unixepoch(),1) "
            "ON CONFLICT(fakeid) DO UPDATE SET "
            "nickname=excluded.nickname, head_img=excluded.head_img, alias=excluded.alias, "
            "token=excluded.token, cookie=excluded.cookie, expire_time=excluded.expire_time, "
            "login_time=unixepoch(), is_active=1, updated_at=unixepoch()",
            (fakeid, nickname, head_img, alias, token, cookie, expire_time),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error("upsert_account failed: %s", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def get_active_account() -> Optional[Dict]:
    """获取当前活跃账号（is_active=1），无则返回 None"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM accounts WHERE is_active=1 LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_accounts() -> List[Dict]:
    """列出所有账号，按登录时间倒序。此方法已过滤 token/cookie，安全可公开"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT fakeid, nickname, head_img, alias, expire_time, "
            "login_time, is_active, created_at, updated_at "
            "FROM accounts ORDER BY login_time DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_account(fakeid: str) -> Optional[Dict]:
    """获取单个账号完整信息（含 token/cookie）"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM accounts WHERE fakeid=?", (fakeid,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def activate_account(fakeid: str) -> bool:
    """切换活跃账号：将指定 fakeid 设为 is_active=1，其余置 0"""
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE accounts SET is_active=0 WHERE is_active=1")
        conn.execute(
            "UPDATE accounts SET is_active=1, updated_at=unixepoch() WHERE fakeid=?",
            (fakeid,)
        )
        conn.commit()
        return conn.total_changes > 0
    except Exception as e:
        logger.error("activate_account failed: %s", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_account(fakeid: str) -> bool:
    """删除账号记录"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM accounts WHERE fakeid=?", (fakeid,))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def deactivate_all_accounts() -> bool:
    """将所有账号的 is_active 置 0"""
    conn = _get_conn()
    try:
        conn.execute("UPDATE accounts SET is_active=0, updated_at=unixepoch()")
        conn.commit()
        return True
    finally:
        conn.close()


def get_accounts_count() -> int:
    """返回账号总数"""
    conn = _get_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    finally:
        conn.close()
