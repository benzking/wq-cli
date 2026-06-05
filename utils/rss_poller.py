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
import random
import time
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


class TokenExpiredError(Exception):
    """RSS 轮询期间检测到 token 过期（ret=200003），轮询器应立即中断当前轮次。"""
    pass


class RSSPoller:
    """后台轮询单例"""

    _instance = None
    _task: Optional[asyncio.Task] = None
    _running = False
    # [2026-05-15 OS-4] 共享 httpx.AsyncClient 避免每轮每 fakeid 都新建（省 DNS+TLS 握手）
    _http_client: Optional[httpx.AsyncClient] = None
    consecutive_failures = 0
    last_fail_time = None
    last_fail_msg = None
    _first_fail_msg = None
    _current_batch: set = set()

    def is_in_current_batch(self, fakeid: str) -> bool:
        """判断 fakeid 是否在当前轮询批次中（用于'已在队列'判断）"""
        return fakeid in self._current_batch

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
        self._current_batch = set(active_fakeids)
        skipped = len(fakeids) - len(active_fakeids)
        
        if skipped > 0:
            logger.info("RSS poll: %d subscriptions (%d blacklisted, skipped)", 
                       len(fakeids), skipped)
        else:
            logger.info("RSS poll: checking %d subscriptions", len(fakeids))

        any_success = False
        any_attempt = False

        for fakeid in active_fakeids:
            sub = rss_store.get_subscription(fakeid)
            nickname = sub.get("nickname", "") if sub else ""
            try:
                articles = await self._fetch_article_list(fakeid, creds)
                any_attempt = True
                if not articles:
                    logger.info("轮询器 拉取 %s(%s) 返回 0 篇文章", nickname, fakeid[:12])
                    rss_store.update_last_poll(fakeid)
                    continue

                logger.info("轮询器 拉取 %s(%s) 最新 %d 篇，开始对比",
                           nickname, fakeid[:12], len(articles))

                new_count = 0
                skipped_count = 0
                new_links = []
                for a in articles:
                    title = a.get("title", "")[:40]
                    link = a.get("link", "")
                    exists = rss_store.article_exists(fakeid, link)
                    if exists:
                        skipped_count += 1
                        logger.debug("RSS poll[DUPE] fakeid=%s title=%s link=%s",
                                    fakeid[:12], title[:30], link[:60])
                        logger.info("轮询器 对比 %s(%s) 的《%s》，已存在",
                                   nickname, fakeid[:12], title)
                    else:
                        new_count += 1
                        new_links.append(link)
                        logger.debug("RSS poll[NEW] fakeid=%s title=%s link=%s",
                                    fakeid[:12], title[:30], link[:60])
                        logger.info("轮询器 对比 %s(%s) 的《%s》，新文章，加入队列",
                                   nickname, fakeid[:12], title)

                # 批量保存新文章元数据
                new_articles = [a for a in articles if a.get("link") in new_links]
                if new_articles:
                    rss_store.save_articles(fakeid, new_articles)
                    log_ingestion_start(fakeid, new_links, channel="poll")
                    from utils.fetch_worker import fetch_worker
                    fetch_worker.wake()

                logger.info("轮询器 %s(%s) 对比结果：获取 %d 篇，新文章 %d 篇，已存在 %d 篇",
                           nickname, fakeid[:12], len(articles), new_count, skipped_count)
                logger.debug("RSS poll: fakeid=%s fetched=%d new=%d skipped=%d",
                            fakeid[:12], len(articles), new_count, skipped_count)
                rss_store.update_last_poll(fakeid)
                any_success = True
            except WechatInvalidFakeidError as e:
                # [2026-05-18] 同步 SaaS 修复：fakeid 在微信侧已失效，自动加入黑名单
                # 取该 fakeid 的 nickname（如果数据库里有）便于后续运维查看
                sub = rss_store.get_subscription(fakeid)
                nickname = sub.get("nickname", "") if sub else ""
                logger.warning("Fakeid %s (%s) is invalid on WeChat, adding to blacklist", fakeid[:8], nickname)
                any_attempt = True
                if self._first_fail_msg is None:
                    self._first_fail_msg = f"{nickname}({fakeid[:12]}) 已失效，自动加入黑名单"
                try:
                    rss_store.add_to_blacklist(
                        fakeid, nickname=nickname, reason="invalid_fakeid",
                        note="[2026-05-18] 微信侧返回 invalid args，fakeid 已失效（注销/改名/重新注册）",
                    )
                except Exception as bl_err:
                    logger.warning("Failed to blacklist invalid fakeid %s: %s", fakeid[:8], bl_err)
            except TokenExpiredError:
                logger.error("Token expired, aborting poll cycle")
                self.consecutive_failures += 1
                self.last_fail_time = time.time()
                self.last_fail_msg = "Token 已过期，请重新扫码登录"
                break
            except Exception as e:
                logger.error("RSS poll error for %s: %s", fakeid[:8], e)
                any_attempt = True
                if self._first_fail_msg is None:
                    self._first_fail_msg = f"获取 {nickname}({fakeid[:12]}) 文章失败: {str(e)[:100]}"
            await asyncio.sleep(random.randint(3, 8))

        self._current_batch.clear()

        if any_attempt:
            if any_success:
                self.consecutive_failures = 0
                self.last_fail_time = None
                self.last_fail_msg = None
                self._first_fail_msg = None
            else:
                self.consecutive_failures += 1
                self.last_fail_time = time.time()
                self.last_fail_msg = self._first_fail_msg or "所有订阅的轮询均失败"
                self._first_fail_msg = None

    async def _fetch_article_list(self, fakeid: str, creds: Dict) -> List[Dict]:
        """通过 fetch_mp_api 获取文章列表。"""
        from utils.mp_api_client import fetch_mp_api

        use_proxy = os.getenv("MP_API_USE_PROXY", "false").lower() == "true"

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

        result = await fetch_mp_api(
            "https://mp.weixin.qq.com/cgi-bin/appmsgpublish",
            params=params, creds=creds, use_proxy=use_proxy,
        )

        if result.is_ok:
            assert result.data is not None
            data = result.data
            publish_page = data.get("publish_page", {})
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

        if result.error_type == "invalid_fakeid":
            raise WechatInvalidFakeidError(
                f"fakeid {fakeid[:8]} 已失效（注销/改名）"
            )
        if result.error_type == "token_expired":
            raise TokenExpiredError("登录过期，请重新扫码登录")
        logger.warning("Poll skip for %s: error_type=%s", fakeid[:8], result.error_type)
        return []

    async def poll_now(self):
        """手动触发一次轮询"""
        await self._poll_all()

    async def poll_single(self, fakeid: str):
        """立即轮询指定公众号（单号，不等待轮询周期）"""
        creds = auth_manager.get_credentials()
        if not creds or not creds.get("token") or not creds.get("cookie"):
            raise ValueError("未登录，请先登录微信公众号后台")

        sub = rss_store.get_subscription(fakeid)
        nickname = sub.get("nickname", "") if sub else ""

        try:
            articles = await self._fetch_article_list(fakeid, creds)
        except WechatInvalidFakeidError:
            logger.warning("Fakeid %s is invalid on WeChat, adding to blacklist", fakeid[:8])
            rss_store.add_to_blacklist(
                fakeid, nickname=nickname, reason="invalid_fakeid",
                note="手动刷新触发：fakeid 已失效",
            )
            return
        except Exception as e:
            logger.error("poll_single error for %s: %s", fakeid[:8], e)
            return

        if not articles:
            logger.info("poll_single %s(%s) returned 0 articles", nickname, fakeid[:12])
            rss_store.update_last_poll(fakeid)
            return

        new_links = []
        for a in articles:
            link = a.get("link", "")
            if not rss_store.article_exists(fakeid, link):
                new_links.append(link)

        if new_links:
            new_articles = [a for a in articles if a.get("link") in new_links]
            rss_store.save_articles(fakeid, new_articles)
            log_ingestion_start(fakeid, new_links, channel="poll")
            from utils.fetch_worker import fetch_worker
            fetch_worker.wake()

        rss_store.update_last_poll(fakeid)
        logger.info("poll_single %s(%s): %d articles, %d new",
                    nickname, fakeid[:12], len(articles), len(new_links))

rss_poller = RSSPoller()
