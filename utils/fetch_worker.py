#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
入库抓取 Worker — 串行单线程，从 ingestion_logs 取任务并执行

每轮循环：读配置 → 崩溃恢复 → 暂停检查 → 取任务 → 选渠道 → 抓取 →
判定结果 → 写 articles/ingestion/fetch_logs → 间隔等待 → 令牌桶检查
"""

import asyncio
import logging
import time
import os
import secrets
from typing import Dict, Optional

logger = logging.getLogger(__name__)

CFG_KEYS = {
    "fetch_interval": ("worker_fetch_interval", 5),
    "rate_per_minute": ("worker_rate_per_minute", 10),
    "idle_sleep": ("worker_idle_sleep", 60),
    "fetch_timeout": ("worker_fetch_timeout", 90),
    "channel_cooldown": ("worker_channel_cooldown", 30),
    "channel_death_threshold": ("worker_channel_death_threshold", 5),
    "in_progress_timeout": ("worker_in_progress_timeout", 15),
}


def _load_config() -> dict:
    from utils import rss_store
    cfg = {}
    for name, (key, default) in CFG_KEYS.items():
        val = rss_store.get_config(key)
        cfg[name] = type(default)(val) if val else default
    return cfg


def _classify_html(html: str) -> str:
    """判定 HTML 失败类型，正常返回 ''"""
    from utils.helpers import is_article_unavailable, has_article_content
    html_lower = html.lower()
    if ("verifycode" in html_lower
            or "请输入图片中的字符" in html
            or "环境异常" in html):
        return "verification"
    if is_article_unavailable(html):
        return "unavailable"
    if not has_article_content(html):
        return "no_content"
    return ""


class FetchWorker:
    """串行单线程抓取 Worker"""

    def __init__(self):
        self._running = False
        self._paused = False
        self._wake_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._tokens = 0.0
        self._last_token_time = 0.0
        self._current_task: Optional[Dict] = None
        self._current_task_start: Optional[float] = None

    @property
    def status(self) -> dict:
        from utils.ingestion_store import pending_count, pending_per_fakeid
        from utils.fetch_router import fetcher_router
        return {
            "running": self._running,
            "paused": self._paused,
            "current_task": {
                "fakeid": self._current_task["fakeid"],
                "link": self._current_task["link"],
                "title": self._current_task.get("title", ""),
                "nickname": self._current_task.get("nickname", ""),
                "fetcher": self._current_task.get("fetcher", ""),
            } if self._current_task else None,
            "pending_count": pending_count(),
            "per_fakeid_pending": pending_per_fakeid(),
            "fetchers": fetcher_router.all_status(),
        }

    async def start(self):
        if self._running:
            return
        self._running = True
        self._last_token_time = time.monotonic()
        self._tokens = _load_config()["rate_per_minute"]
        self._task = asyncio.create_task(self._loop())
        logger.info("FetchWorker started")

    async def stop(self):
        self._running = False
        self._current_task = None
        self._current_task_start = None
        self._wake_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("FetchWorker stopped")

    def wake(self):
        self._wake_event.set()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    async def toggle_pause(self) -> bool:
        self._paused = not self._paused
        if not self._paused:
            self._wake_event.set()
        return self._paused

    async def _loop(self):
        while self._running:
            try:
                await self._do_cycle()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Worker cycle crashed: %s", e, exc_info=True)
                self._current_task = None
                self._current_task_start = None
                await asyncio.sleep(10)

    async def _do_cycle(self):
        while self._running:
            cfg = _load_config()

            # 渠道配置刷新
            from utils.fetch_router import fetcher_router
            fetcher_router.refresh_from_config(
                cooldown_seconds=cfg["channel_cooldown"],
                death_threshold=cfg["channel_death_threshold"],
            )

            # 崩溃恢复
            from utils.ingestion_store import recover_stalled_in_progress
            recovered = recover_stalled_in_progress(cfg["in_progress_timeout"])
            if recovered:
                logger.warning("Recovered %d stalled in_progress records", recovered)

            # 暂停检查
            if self._paused:
                try:
                    await asyncio.wait_for(self._wake_event.wait(), timeout=30)
                    self._wake_event.clear()
                except asyncio.TimeoutError:
                    pass
                continue

            # 取任务
            from utils.ingestion_store import get_next_task
            task = get_next_task()
            if not task:
                try:
                    await asyncio.wait_for(self._wake_event.wait(),
                                           timeout=cfg["idle_sleep"])
                    self._wake_event.clear()
                except asyncio.TimeoutError:
                    pass
                continue

            article_link = task["article_link"]
            fakeid = task["fakeid"]
            tid = secrets.token_hex(4)
            logger.info("[Worker %s] processing %s", tid, article_link[:60])

            # 标记 in_progress
            from utils.ingestion_store import set_in_progress
            set_in_progress(fakeid, article_link)

            # 选取渠道
            fetcher_name = fetcher_router.select_fetcher(
                article_link,
                specified=task.get("fetcher") or None,
            )
            if not fetcher_name:
                from utils.ingestion_store import extend_retry
                extend_retry(fakeid, article_link, 30)
                logger.info("[Worker %s] no available fetcher, deferred 30s", tid)
                await asyncio.sleep(cfg["fetch_interval"])
                continue

            self._current_task = {
                "fakeid": fakeid,
                "link": article_link,
                "title": task.get("title", ""),
                "nickname": task.get("nickname", ""),
                "fetcher": fetcher_name,
                "tid": tid,
            }
            self._current_task_start = time.monotonic()

            # 构建 URL 和 headers
            full_url = article_link
            token = os.getenv("WECHAT_TOKEN", "")
            if token:
                sep = '&' if '?' in article_link else '?'
                full_url = f"{article_link}{sep}token={token}"
            extra_headers = {"Referer": "https://mp.weixin.qq.com/"}
            cookie = os.getenv("WECHAT_COOKIE", "")
            if cookie:
                extra_headers["Cookie"] = cookie

            # 执行抓取
            t_start = time.monotonic()
            html = None
            try:
                html = await asyncio.wait_for(
                    fetcher_router.execute(
                        fetcher_name, full_url,
                        extra_headers=extra_headers,
                        timeout=cfg["fetch_timeout"],
                    ),
                    timeout=cfg["fetch_timeout"],
                )
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error("[Worker %s] fetch error: %s", tid, str(e)[:80])
            latency_ms = int((time.monotonic() - t_start) * 1000)

            # 判定和处理结果
            if html:
                fail_type = _classify_html(html)
                if fail_type:
                    self._handle_failure(task, fetcher_name, fail_type, latency_ms, tid)
                else:
                    self._handle_success(task, html, fetcher_name, latency_ms, tid)
            else:
                self._handle_failure(task, fetcher_name, "network_error", latency_ms, tid)

            self._current_task = None
            self._current_task_start = None

            # 间隔等待
            await asyncio.sleep(cfg["fetch_interval"])
            # 令牌桶
            await self._token_wait(cfg["rate_per_minute"])

    def _handle_success(self, task: dict, html: str, fetcher_name: str,
                        latency_ms: int, tid: str):
        from utils.content_processor import process_article_content
        from utils.ingestion_store import mark_success
        from utils.fetch_logs import insert_fetch_log
        from utils.fetch_router import fetcher_router
        from utils import rss_store
        import os

        article_link = task["article_link"]
        fakeid = task["fakeid"]

        try:
            site_url = os.getenv("SITE_URL", "http://localhost:5000").rstrip("/")
            result = process_article_content(html, proxy_base_url=site_url)
            content = result.get("content", "")
            plain_content = result.get("plain_content", "")

            if not content.strip():
                self._handle_failure(task, fetcher_name, "no_content", latency_ms, tid)
                return

            conn = rss_store._get_conn()
            try:
                conn.execute(
                    "UPDATE articles SET content=?, plain_content=? "
                    "WHERE fakeid=? AND link=?",
                    (content, plain_content, fakeid, article_link),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error("[Worker %s] parse error: %s", tid, str(e)[:80])
            self._handle_failure(task, fetcher_name, "parse_error", latency_ms, tid)
            return

        mark_success(fakeid, article_link, fetcher=fetcher_router.get_label(fetcher_name))
        insert_fetch_log(fakeid, article_link, fetcher_name, 1,
                         "", "", latency_ms, "queue_worker")
        fetcher_router.record_result(fetcher_name, True)
        logger.info("[Worker %s] SUCCESS: %s via %s (%dms)",
                    tid, article_link[:60], fetcher_name, latency_ms)

    def _handle_failure(self, task: dict, fetcher_name: str, fail_type: str,
                        latency_ms: int, tid: str):
        from utils.ingestion_store import mark_failure
        from utils.fetch_logs import insert_fetch_log, get_tried_fetchers_for_article
        from utils.fetch_router import fetcher_router
        from utils.fetch_backoff import get_backoff

        article_link = task["article_link"]
        fakeid = task["fakeid"]

        insert_fetch_log(fakeid, article_link, fetcher_name, 0,
                         fail_type, "", latency_ms, "queue_worker")
        fetcher_router.record_result(fetcher_name, False, fail_type)

        interval, max_retries = get_backoff(fail_type)
        attempt = task.get("attempt", 0)
        is_permanent = False

        if fail_type == "unavailable":
            is_permanent = True
            interval = 0
        elif fail_type == "network_error":
            tried = get_tried_fetchers_for_article(article_link)
            all_names = [cb.name for cb in fetcher_router.breakers.values()]
            if len(tried) >= len(all_names):
                is_permanent = True
        elif max_retries is not None and attempt + 1 >= max_retries:
            is_permanent = True

        if interval is None:
            interval = 60

        next_retry = time.time() + interval
        mark_failure(fakeid, article_link, fail_type, next_retry, is_permanent,
                     fetcher=fetcher_router.get_label(fetcher_name))
        status = "failed_permanent" if is_permanent else "failed_retryable"
        logger.info("[Worker %s] FAILED (%s/%s): %s via %s",
                    tid, fail_type, status, article_link[:60], fetcher_name)

    async def _token_wait(self, rate_per_minute: int):
        now = time.monotonic()
        elapsed = now - self._last_token_time
        self._tokens += elapsed * (rate_per_minute / 60.0)
        if self._tokens > rate_per_minute:
            self._tokens = rate_per_minute
        self._last_token_time = now
        if self._tokens < 1.0:
            wait = (1.0 - self._tokens) * (60.0 / rate_per_minute)
            await asyncio.sleep(wait)
            self._tokens = 0.0
            self._last_token_time = time.monotonic()
        else:
            self._tokens -= 1.0


fetch_worker = FetchWorker()
