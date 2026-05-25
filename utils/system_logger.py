#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
全平台日志系统 — SQLite 存储 + LogHandler
"""
import logging
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
    return conn


def init_system_logs_table():
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL NOT NULL,
                level       TEXT NOT NULL DEFAULT 'INFO',
                module      TEXT NOT NULL DEFAULT '',
                message     TEXT NOT NULL DEFAULT '',
                created_at  REAL NOT NULL DEFAULT (unixepoch())
            );
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);
        """)
        conn.commit()
    finally:
        conn.close()


def write_log(level: str, module: str, message: str, timestamp: float = None):
    if timestamp is None:
        timestamp = time.time()
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO system_logs (timestamp, level, module, message) VALUES (?, ?, ?, ?)",
            (timestamp, level, module, message),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


class SQLiteLogHandler(logging.Handler):
    """将 Python logging 写入 SQLite"""

    def emit(self, record: logging.LogRecord):
        try:
            write_log(
                level=record.levelname,
                module=record.name,
                message=self.format(record),
                timestamp=record.created,
            )
        except Exception:
            self.handleError(record)


def query_logs(level: Optional[str] = None, module: Optional[str] = None,
               keyword: Optional[str] = None, page: int = 1, per_page: int = 50,
               since: Optional[float] = None, until: Optional[float] = None,
               ) -> List[Dict]:
    conn = _get_conn()
    try:
        conditions = ["1=1"]
        params = []

        if level:
            conditions.append("level = ?")
            params.append(level.upper())

        if module:
            conditions.append("module LIKE ?")
            params.append(f"%{module}%")

        if keyword:
            conditions.append("message LIKE ?")
            params.append(f"%{keyword}%")

        if since:
            conditions.append("timestamp >= ?")
            params.append(since)

        if until:
            conditions.append("timestamp <= ?")
            params.append(until)

        where = " AND ".join(conditions)
        offset = (page - 1) * per_page
        params.extend([per_page, offset])

        rows = conn.execute(
            f"SELECT * FROM system_logs WHERE {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_logs(level: Optional[str] = None, module: Optional[str] = None,
               keyword: Optional[str] = None, since: Optional[float] = None,
               until: Optional[float] = None) -> int:
    conn = _get_conn()
    try:
        conditions = ["1=1"]
        params = []

        if level:
            conditions.append("level = ?")
            params.append(level.upper())

        if module:
            conditions.append("module LIKE ?")
            params.append(f"%{module}%")

        if keyword:
            conditions.append("message LIKE ?")
            params.append(f"%{keyword}%")

        if since:
            conditions.append("timestamp >= ?")
            params.append(since)

        if until:
            conditions.append("timestamp <= ?")
            params.append(until)

        where = " AND ".join(conditions)
        row = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM system_logs WHERE {where}", params
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def delete_old_logs(retain_days: int = 7):
    """删除 N 天前的日志"""
    cutoff = time.time() - retain_days * 86400
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM system_logs WHERE timestamp < ?", (cutoff,))
        deleted = conn.execute("SELECT changes()").fetchone()[0]
        conn.commit()
        return deleted
    finally:
        conn.close()


def get_distinct_modules() -> List[str]:
    """获取所有出现过的模块名"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT module FROM system_logs WHERE module != '' ORDER BY module"
        ).fetchall()
        return [r["module"] for r in rows]
    finally:
        conn.close()
