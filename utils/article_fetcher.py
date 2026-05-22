#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章回落获取器 — L1(CF Worker) → L2(SOCKS5代理) → L3(直连) 三级回落
"""

import asyncio
import logging
import secrets
from typing import Optional

logger = logging.getLogger(__name__)

FALLBACK_TOTAL_TIMEOUT = 90  # 全链路总超时


class AllLevelsFailedError(Exception):
    """所有等级均失败"""
    pass


class ArticleFallbackFetcher:
    """统一回落调度器 — 单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _trace_id(self) -> str:
        return secrets.token_hex(4)

    async def fetch(self, article_url: str, timeout: int = 60,
                    wechat_token: Optional[str] = None,
                    wechat_cookie: Optional[str] = None) -> Optional[str]:
        """
        按 L1→L2→L3 逐级尝试获取文章。
        签名与旧 fetch_article_content() 兼容。
        """
        tid = self._trace_id()
        from utils.fetcher_config import get_active_levels

        active = get_active_levels()
        logger.info("[Fetch %s] url=%s levels=%s", tid, article_url[:60], "→".join(active))

        try:
            return await asyncio.wait_for(
                self._do_fetch(article_url, tid, wechat_token, wechat_cookie),
                timeout=FALLBACK_TOTAL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("[Fetch %s] total timeout %ds exceeded", tid, FALLBACK_TOTAL_TIMEOUT)
            return None

    async def _do_fetch(self, article_url: str, tid: str,
                        wechat_token: Optional[str],
                        wechat_cookie: Optional[str]) -> Optional[str]:
        from utils.fetcher_config import get_active_levels
        from utils.http_client import fetch_page

        active = get_active_levels()

        full_url = article_url
        if wechat_token:
            separator = '&' if '?' in article_url else '?'
            full_url = f"{article_url}{separator}token={wechat_token}"

        extra_headers = {"Referer": "https://mp.weixin.qq.com/"}
        if wechat_cookie:
            extra_headers["Cookie"] = wechat_cookie

        # L1: CF Worker
        if "L1" in active:
            logger.info("[Fetch %s] L1 trying CF Worker", tid)
            from utils.cf_worker_client import cf_worker_client
            html = await cf_worker_client.fetch(full_url)
            if html and self._is_valid(html):
                logger.info("[Fetch %s] L1 SUCCESS len=%d", tid, len(html))
                return html
            logger.warning("[Fetch %s] L1 FAILED", tid)
            self._notify_degraded("L1")

        # L2: SOCKS5 代理（禁止直连兜底，直连留给 L3）
        if "L2" in active:
            logger.info("[Fetch %s] L2 trying SOCKS5 proxy", tid)
            try:
                html = await fetch_page(full_url, extra_headers=extra_headers,
                                        timeout=30, allow_direct_fallback=False)
                if html and self._is_valid(html):
                    logger.info("[Fetch %s] L2 SUCCESS len=%d", tid, len(html))
                    return html
            except Exception as e:
                logger.warning("[Fetch %s] L2 error: %s", tid, str(e)[:80])
            logger.warning("[Fetch %s] L2 FAILED", tid)
            self._notify_degraded("L2")

        # L3: curl_cffi 直连（始终可用）
        if "L3" in active:
            logger.info("[Fetch %s] L3 trying direct connection", tid)
            try:
                html = await fetch_page(full_url, extra_headers=extra_headers,
                                        timeout=30, allow_direct_fallback=True)
                if html and self._is_valid(html):
                    logger.info("[Fetch %s] L3 SUCCESS len=%d", tid, len(html))
                    return html
            except Exception as e:
                logger.error("[Fetch %s] L3 error: %s", tid, str(e)[:80])

        logger.error("[Fetch %s] ALL LEVELS FAILED", tid)
        return None

    def _is_valid(self, html: str) -> bool:
        from utils.helpers import has_article_content, is_article_unavailable
        if is_article_unavailable(html):
            return False
        return has_article_content(html)

    def _notify_degraded(self, level: str):
        """异步通知 webhook（不阻塞主流程）"""
        async def _notify():
            try:
                from utils.webhook import webhook
                await webhook.notify("fallback_degraded", {
                    "level": level,
                    "message": f"回落等级 {level} 所有节点不可用，已降级",
                })
            except Exception:
                pass
        asyncio.ensure_future(_notify())


fallback_fetcher = ArticleFallbackFetcher()


# ── 兼容旧接口 ─────────────────────────────────────────────


async def fetch_article_content(
    article_url: str,
    timeout: int = 60,
    wechat_token: Optional[str] = None,
    wechat_cookie: Optional[str] = None
) -> Optional[str]:
    """兼容旧的 fetch_article_content() 接口"""
    return await fallback_fetcher.fetch(article_url, timeout, wechat_token, wechat_cookie)


async def fetch_articles_batch(
    article_urls: list,
    max_concurrency: int = 5,
    timeout: int = 60,
    wechat_token: Optional[str] = None,
    wechat_cookie: Optional[str] = None
) -> dict:
    """批量获取文章内容（并发版），兼容旧接口"""
    semaphore = asyncio.Semaphore(max_concurrency)
    results = {}

    async def fetch_one(url):
        async with semaphore:
            html = await fallback_fetcher.fetch(url, timeout, wechat_token, wechat_cookie)
            results[url] = html
            await asyncio.sleep(1)

    logger.info("[Batch] 开始批量获取 %d 篇文章", len(article_urls))
    await asyncio.gather(*[fetch_one(url) for url in article_urls], return_exceptions=True)

    success_count = sum(1 for html in results.values() if html)
    logger.info("[Batch] 完成: 成功=%d, 失败=%d", success_count, len(results) - success_count)
    return results
