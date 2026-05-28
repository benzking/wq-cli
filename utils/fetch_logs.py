#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
抓取操作日志 — 记录每次抓取尝试的明细
"""
import sqlite3
import time
import os
from pathlib import Path

_default_db = Path(__file__).parent.parent / "data" / "rss.db"
DB_PATH = Path(os.getenv("RSS_DB_PATH", str(_default_db)))


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_fetch_logs_table():
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fetch_logs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                fakeid        TEXT NOT NULL DEFAULT '',
                article_link  TEXT NOT NULL DEFAULT '',
                fetcher       TEXT NOT NULL DEFAULT '',
                success       INTEGER NOT NULL DEFAULT 0,
                fail_type     TEXT NOT NULL DEFAULT '',
                error_detail  TEXT NOT NULL DEFAULT '',
                latency_ms    INTEGER NOT NULL DEFAULT 0,
                triggered_by  TEXT NOT NULL DEFAULT 'queue_worker',
                created_at    REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_fetch_logs_article_link ON fetch_logs(article_link);
            CREATE INDEX IF NOT EXISTS idx_fetch_logs_created_at ON fetch_logs(created_at);
        """)
        conn.commit()
    finally:
        conn.close()


def insert_fetch_log(
    fakeid: str,
    article_link: str,
    fetcher: str,
    success: int,
    fail_type: str = "",
    error_detail: str = "",
    latency_ms: int = 0,
    triggered_by: str = "queue_worker",
):
    conn = _get_conn()
    try:
        now = time.time()
        conn.execute(
            "INSERT INTO fetch_logs (fakeid, article_link, fetcher, success, fail_type, error_detail, latency_ms, triggered_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fakeid, article_link, fetcher, success, fail_type, error_detail, latency_ms, triggered_by, now),
        )
        conn.commit()
    finally:
        conn.close()


def get_tried_fetchers_for_article(article_link: str) -> list:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT fetcher FROM fetch_logs "
            "WHERE article_link=? AND fail_type='network_error'",
            (article_link,),
        ).fetchall()
        return [r["fetcher"] for r in rows]
    finally:
        conn.close()