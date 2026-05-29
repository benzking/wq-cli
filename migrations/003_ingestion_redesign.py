#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
Migration 003: Ingestion Redesign

Steps:
  1. Backfill ingestion_logs.channel from articles.source (deep_fetch)
  2. Deduplicate ingestion_logs (keep latest per fakeid+article_link)
  3. Add UNIQUE index on ingestion_logs(fakeid, article_link)
  4. Remap status: 'failed' -> 'failed_retryable'
  5. Add new columns: fail_type, next_retry_at, fetcher
  6. Backfill fail_type='no_content' for empty-content failures
  7. Remove source column from articles (rebuild table)
  8. Rebuild idx_articles_fakeid_time index
"""
import sqlite3
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_default_db = Path(__file__).parent.parent / "data" / "rss.db"
DB_PATH = Path(os.getenv("RSS_DB_PATH", str(_default_db)))


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in the given table."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return column in (r[1] for r in rows)


def _index_exists(conn: sqlite3.Connection, name: str) -> bool:
    """Check if an index (or other sqlite_master entry) exists by name."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name=? AND type='index'", (name,)
    ).fetchone()
    return row is not None


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name=? AND type='table'", (table,)
    ).fetchone()
    return row is not None


def migrate():
    conn = _get_conn()

    # ── Step 1: Backfill ingestion_logs.channel from articles.source ──
    logger.info("Step 1: Backfilling ingestion_logs.channel from articles.source...")
    if _table_exists(conn, "ingestion_logs") and _table_exists(conn, "articles"):
        if _column_exists(conn, "articles", "source") and _column_exists(conn, "ingestion_logs", "channel"):
            conn.execute("""
                UPDATE ingestion_logs
                SET channel = 'deep_fetch'
                WHERE channel = 'poll'
                  AND EXISTS (
                      SELECT 1 FROM articles
                      WHERE articles.link = ingestion_logs.article_link
                        AND articles.source = 'deep_fetch'
                  )
            """)
            affected = conn.total_changes
            logger.info("  Backfilled %d ingestion_logs rows to channel='deep_fetch'", affected)
            conn.commit()
        else:
            logger.info("  Skipped: source or channel column does not exist")
    else:
        logger.info("  Skipped: ingestion_logs or articles table does not exist")

    # ── Step 2: Deduplicate ingestion_logs ──
    logger.info("Step 2: Deduplicating ingestion_logs...")
    if _table_exists(conn, "ingestion_logs"):
        conn.execute("""
            DELETE FROM ingestion_logs
            WHERE id NOT IN (
                SELECT MAX(id) FROM ingestion_logs GROUP BY fakeid, article_link
            )
        """)
        deleted = conn.total_changes
        logger.info("  Removed %d duplicate rows", deleted)
        conn.commit()
    else:
        logger.info("  Skipped: ingestion_logs table does not exist")

    # ── Step 3: Add UNIQUE index on (fakeid, article_link) ──
    logger.info("Step 3: Adding UNIQUE index uq_ingestion_link...")
    if _table_exists(conn, "ingestion_logs"):
        if not _index_exists(conn, "uq_ingestion_link"):
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_ingestion_link "
                "ON ingestion_logs(fakeid, article_link)"
            )
            conn.commit()
            logger.info("  Created UNIQUE index uq_ingestion_link")
        else:
            logger.info("  Index uq_ingestion_link already exists")
    else:
        logger.info("  Skipped: ingestion_logs table does not exist")

    # ── Step 4: Status remap (failed -> failed_retryable) ──
    logger.info("Step 4: Remapping status 'failed' -> 'failed_retryable'...")
    if _table_exists(conn, "ingestion_logs"):
        conn.execute(
            "UPDATE ingestion_logs SET status='failed_retryable' WHERE status='failed'"
        )
        remapped = conn.total_changes
        logger.info("  Remapped %d rows to 'failed_retryable'", remapped)
        conn.commit()
    else:
        logger.info("  Skipped: ingestion_logs table does not exist")

    # ── Step 5: Add new columns ──
    logger.info("Step 5: Adding new columns to ingestion_logs...")
    if _table_exists(conn, "ingestion_logs"):
        if not _column_exists(conn, "ingestion_logs", "fail_type"):
            conn.execute("ALTER TABLE ingestion_logs ADD COLUMN fail_type TEXT NOT NULL DEFAULT ''")
            conn.commit()
            logger.info("  Added column: fail_type")
        else:
            logger.info("  Column fail_type already exists")

        if not _column_exists(conn, "ingestion_logs", "next_retry_at"):
            conn.execute("ALTER TABLE ingestion_logs ADD COLUMN next_retry_at REAL NOT NULL DEFAULT 0.0")
            conn.commit()
            logger.info("  Added column: next_retry_at")
        else:
            logger.info("  Column next_retry_at already exists")

        if not _column_exists(conn, "ingestion_logs", "fetcher"):
            conn.execute("ALTER TABLE ingestion_logs ADD COLUMN fetcher TEXT NOT NULL DEFAULT ''")
            conn.commit()
            logger.info("  Added column: fetcher")
        else:
            logger.info("  Column fetcher already exists")
    else:
        logger.info("  Skipped: ingestion_logs table does not exist")

    # ── Step 6: Backfill fail_type for empty-content failures ──
    logger.info("Step 6: Backfilling fail_type='no_content' for empty-content failures...")
    if _table_exists(conn, "ingestion_logs") and _column_exists(conn, "ingestion_logs", "fail_type"):
        conn.execute("""
            UPDATE ingestion_logs
            SET fail_type = 'no_content'
            WHERE status = 'failed_retryable'
              AND (fail_type = '' OR fail_type IS NULL)
              AND (error_msg LIKE '%empty content%' OR error_msg = '')
        """)
        updated = conn.total_changes
        logger.info("  Backfilled %d rows with fail_type='no_content'", updated)
        conn.commit()
    else:
        logger.info("  Skipped: ingestion_logs table or fail_type column does not exist")

    # ── Step 7: Remove source column from articles (rebuild table) ──
    logger.info("Step 7: Removing source column from articles...")
    if _table_exists(conn, "articles") and _column_exists(conn, "articles", "source"):
        # Get all columns except 'source'
        cols = conn.execute("PRAGMA table_info(articles)").fetchall()
        col_names = [c[1] for c in cols if c[1] != "source"]
        col_list = ", ".join(col_names)
        placeholders = ", ".join("?" * len(col_names))

        # Build new table without source column, including constraints
        # Original schema: id, fakeid, aid, title, link, digest, cover, author,
        # content, plain_content, publish_time, fetched_at, source, starred, images_localized
        # Plus UNIQUE(fakeid, link), FOREIGN KEY (fakeid) REFERENCES subscriptions(fakeid)
        conn.execute("""
            CREATE TABLE articles_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                fakeid          TEXT NOT NULL,
                aid             TEXT NOT NULL DEFAULT '',
                title           TEXT NOT NULL DEFAULT '',
                link            TEXT NOT NULL DEFAULT '',
                digest          TEXT NOT NULL DEFAULT '',
                cover           TEXT NOT NULL DEFAULT '',
                author          TEXT NOT NULL DEFAULT '',
                content         TEXT NOT NULL DEFAULT '',
                plain_content   TEXT NOT NULL DEFAULT '',
                publish_time    INTEGER NOT NULL DEFAULT 0,
                fetched_at      INTEGER NOT NULL,
                starred         INTEGER NOT NULL DEFAULT 0,
                images_localized INTEGER NOT NULL DEFAULT 0,
                UNIQUE(fakeid, link),
                FOREIGN KEY (fakeid) REFERENCES subscriptions(fakeid) ON DELETE CASCADE
            )
        """)

        # Copy data
        conn.execute(
            f"INSERT INTO articles_new ({col_list}) SELECT {col_list} FROM articles"
        )
        logger.info("  Copied %d rows to articles_new", conn.total_changes)

        # Swap tables
        conn.execute("DROP TABLE articles")
        conn.execute("ALTER TABLE articles_new RENAME TO articles")
        conn.commit()
        logger.info("  Replaced articles table (source column removed)")
    else:
        logger.info("  Skipped: articles table or source column does not exist")

    # ── Step 8: Rebuild indexes ──
    logger.info("Step 8: Rebuilding indexes...")
    if _table_exists(conn, "articles"):
        # idx_articles_fakeid_time
        if not _index_exists(conn, "idx_articles_fakeid_time"):
            conn.execute(
                "CREATE INDEX idx_articles_fakeid_time ON articles(fakeid, publish_time DESC)"
            )
            logger.info("  Created index: idx_articles_fakeid_time")
        else:
            logger.info("  Index idx_articles_fakeid_time already exists")

        # Remove old source index if it exists
        if _index_exists(conn, "idx_articles_source"):
            conn.execute("DROP INDEX IF EXISTS idx_articles_source")
            logger.info("  Dropped obsolete index: idx_articles_source")

        conn.commit()
    else:
        logger.info("  Skipped: articles table does not exist")

    conn.close()
    logger.info("Migration 003 completed successfully.")


if __name__ == "__main__":
    migrate()
