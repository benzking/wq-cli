#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
RSS 后台轮询器
定时通过公众号后台 API 拉取订阅号的最新文章列表并缓存到 SQLite。
仅获取标题、摘要、封面等元数据，不访问文章页面，零风控风险。
"""

import asyncio
import json
import logging
import os
from typing import List, Dict, Optional

import httpx

from utils.auth_manager import auth_manager
from utils import rss_store
from utils.ingestion_store import log_ingestion_start

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("RSS_POLL_INTERVAL", "3600"))
ARTICLES_PER_POLL = int(os.getenv("ARTICLES_PER_POLL", "10"))
FETCH_FULL_CONTENT = os.getenv("RSS_FETCH_FULL_CONTENT", "true").lower() == "true"


class WechatInvalidFakeidError(Exception):
    """
    [2026-05-18] 公众号在微信侧已失效（已注销/改名/重新注册）

    触发条件：appmsgpublish 接口返回 ret=200002 且 err_msg="invalid args"
    实测：任何 token+cookie 都无法访问，需要标记为永久失效
    """
    pass


class RSSPoller:
    """后台轮询单例"""

    _instance = None
    _task: Optional[asyncio.Task] = None
    _running = False
    # [2026-05-15 OS-4] 共享 httpx.AsyncClient 避免每轮每 fakeid 都新建（省 DNS+TLS 握手）
    _http_client: Optional[httpx.AsyncClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def start(self):
        if self._running:
            return
        self._running = True
        # 创建长连接 client，连接池 + keep-alive 自动复用
        self._http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        self._task = asyncio.create_task(self._loop())
        logger.info("RSS poller started (interval=%ds)", POLL_INTERVAL)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # 关闭共享 client
        if self._http_client is not None:
            try:
                await self._http_client.aclose()
            except Exception:
                pass
            self._http_client = None
        logger.info("RSS poller stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    async def _loop(self):
        while self._running:
            try:
                await self._poll_all()
            except Exception as e:
                logger.error("RSS poll cycle error: %s", e, exc_info=True)
            await asyncio.sleep(POLL_INTERVAL)

    async def _poll_all(self):
        fakeids = rss_store.get_all_fakeids()
        if not fakeids:
            return

        creds = auth_manager.get_credentials()
        if not creds or not creds.get("token") or not creds.get("cookie"):
            logger.warning("RSS poll skipped: not logged in")
            return

        # 获取活跃黑名单
        blacklisted = set(rss_store.get_active_blacklist_fakeids())
        
        # 过滤掉黑名单中的公众号
        active_fakeids = [f for f in fakeids if f not in blacklisted]
        skipped = len(fakeids) - len(active_fakeids)
        
        if skipped > 0:
            logger.info("RSS poll: %d subscriptions (%d blacklisted, skipped)", 
                       len(fakeids), skipped)
        else:
            logger.info("RSS poll: checking %d subscriptions", len(fakeids))

        for fakeid in active_fakeids:
            try:
                articles = await self._fetch_article_list(fakeid, creds)
                if articles:
                    new_count = rss_store.save_articles(fakeid, articles)
                    logger.info("RSS poll %s: fetched=%d, new=%d, skipped=%d",
                               fakeid[:12], len(articles), new_count,
                               len(articles) - new_count)
                    # 为新文章写入 ingestion_logs，Worker 异步抓取内容
                    links = [a.get("link", "") for a in articles if a.get("link")]
                    if links:
                        log_ingestion_start(fakeid, links, channel="poll")
                    # 唤醒 Worker
                    from utils.fetch_worker import fetch_worker
                    fetch_worker.wake()
                else:
                    logger.info("RSS poll %s: no articles returned", fakeid[:12])
                rss_store.update_last_poll(fakeid)
            except WechatInvalidFakeidError as e:
                # [2026-05-18] 同步 SaaS 修复：fakeid 在微信侧已失效，自动加入黑名单
                # 取该 fakeid 的 nickname（如果数据库里有）便于后续运维查看
                sub = rss_store.get_subscription(fakeid)
                nickname = sub.get("nickname", "") if sub else ""
                logger.warning("Fakeid %s (%s) is invalid on WeChat, adding to blacklist", fakeid[:8], nickname)
                try:
                    rss_store.add_to_blacklist(
                        fakeid, nickname=nickname, reason="invalid_fakeid",
                        note="[2026-05-18] 微信侧返回 invalid args，fakeid 已失效（注销/改名/重新注册）",
                    )
                except Exception as bl_err:
                    logger.warning("Failed to blacklist invalid fakeid %s: %s", fakeid[:8], bl_err)
            except Exception as e:
                logger.error("RSS poll error for %s: %s", fakeid[:8], e)
            await asyncio.sleep(3)

    async def _fetch_article_list(self, fakeid: str, creds: Dict) -> List[Dict]:
        params = {
            "sub": "list",
            "search_field": "null",
            "begin": 0,
            "count": ARTICLES_PER_POLL,
            "query": "",
            "fakeid": fakeid,
            "type": "101_1",
            "free_publish_type": 1,
            "sub_action": "list_ex",
            "token": creds["token"],
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://mp.weixin.qq.com/",
            "Cookie": creds["cookie"],
        }

        # [2026-05-15 OS-4] 使用共享 client，省 DNS+TLS 握手
        # 兜底：若 client 未初始化（理论不会发生），退回到每次新建
        if self._http_client is not None:
            resp = await self._http_client.get(
                "https://mp.weixin.qq.com/cgi-bin/appmsgpublish",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            result = resp.json()
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    "https://mp.weixin.qq.com/cgi-bin/appmsgpublish",
                    params=params,
                    headers=headers,
                )
                resp.raise_for_status()
                result = resp.json()

        base_resp = result.get("base_resp", {})
        if base_resp.get("ret") != 0:
            ret_code = base_resp.get("ret")
            err_msg = base_resp.get("err_msg", "")
            logger.warning("WeChat API error for %s: ret=%s err_msg=%r",
                           fakeid[:8], ret_code, err_msg)
            # [2026-05-18] 同步 SaaS 修复：ret=200002 + "invalid args" → fakeid 已失效
            # 老代码统一返回空 → 静默失败，用户感受不到该号已注销
            # 现在：抛 WechatInvalidFakeidError 让调用方加入黑名单
            if ret_code == 200002 and "invalid arg" in err_msg.lower():
                raise WechatInvalidFakeidError(
                    f"fakeid {fakeid[:8]} 已失效（注销/改名）: {err_msg}"
                )
            return []

        publish_page = result.get("publish_page", {})
        if isinstance(publish_page, str):
            try:
                publish_page = json.loads(publish_page)
            except (json.JSONDecodeError, ValueError):
                return []

        if not isinstance(publish_page, dict):
            return []

        articles = []
        for item in publish_page.get("publish_list", []):
            publish_info = item.get("publish_info", {})
            if isinstance(publish_info, str):
                try:
                    publish_info = json.loads(publish_info)
                except (json.JSONDecodeError, ValueError):
                    continue
            if not isinstance(publish_info, dict):
                continue
            for a in publish_info.get("appmsgex", []):
                articles.append({
                    "aid": a.get("aid", ""),
                    "title": a.get("title", ""),
                    "link": a.get("link", ""),
                    "digest": a.get("digest", ""),
                    "cover": a.get("cover", ""),
                    "author": a.get("author", ""),
                    "publish_time": a.get("update_time", 0),
                })
        return articles

    async def poll_now(self):
        """手动触发一次轮询"""
        await self._poll_all()
    
rss_poller = RSSPoller()
