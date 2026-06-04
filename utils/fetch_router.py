#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
渠道路由和熔断器模块

FetcherCircuitBreaker: active/cooling/dead 三态熔断器
FetcherRouter: 管理所有渠道的注册、选取和分派
"""

import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FetcherCircuitBreaker:
    """active/cooling/dead 三态熔断器。

    状态机：
      active --失败--> cooling --冷却到期--> active
      cooling --连续失败>=阈值 且 从未成功--> dead
      dead --revive()--> active
      任意成功 --> active（计数清零）
    """

    def __init__(self, name: str, cooldown_seconds: int = 30,
                 death_threshold: int = 5):
        self.name = name
        self.cooldown_seconds = cooldown_seconds
        self.death_threshold = death_threshold
        self._state = "active"
        self._cooldown_until: Optional[float] = None
        self.consecutive_failures = 0
        self.success_count = 0

    @property
    def state(self) -> str:
        if (self._state == "cooling"
                and self._cooldown_until is not None
                and time.time() > self._cooldown_until):
            self._state = "active"
            self._cooldown_until = None
        return self._state

    def is_available(self) -> bool:
        return self.state == "active"

    def record_success(self):
        self._state = "active"
        self._cooldown_until = None
        self.consecutive_failures = 0
        self.success_count += 1

    def record_failure(self) -> bool:
        """记录一次失败。

        进入 cooling 状态，连续失败计数 +1。
        若连续失败 >= 阈值且从未成功过，转为 dead 并返回 True。
        否则返回 False。
        """
        self._state = "cooling"
        self._cooldown_until = time.time() + self.cooldown_seconds
        self.consecutive_failures += 1

        if (self.consecutive_failures >= self.death_threshold
                and self.success_count == 0):
            self._state = "dead"
            self._cooldown_until = None
            return True
        return False

    def revive(self):
        """手动复活 dead -> active，计数全部归零"""
        self._state = "active"
        self._cooldown_until = None
        self.consecutive_failures = 0
        self.success_count = 0

    def status_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "consecutive_failures": self.consecutive_failures,
            "success_count": self.success_count,
            "cooldown_until": self._cooldown_until,
        }


DEAD_KEY_PREFIX = "fetcher_dead_"


def _load_dead_names() -> List[str]:
    """从 config 表读取已持久化的 dead 渠道名"""
    from utils.rss_store import _get_conn
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT key FROM config WHERE key LIKE 'fetcher_dead_%'"
        ).fetchall()
        return [r["key"][len(DEAD_KEY_PREFIX):] for r in rows]
    finally:
        conn.close()


def _persist_dead(name: str):
    """持久化 dead 状态到 config 表"""
    from utils.rss_store import set_config
    set_config(f"{DEAD_KEY_PREFIX}{name}", "1")


def _clear_dead(name: str):
    """从 config 表删除 dead 持久化"""
    from utils.rss_store import _get_conn
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM config WHERE key=?", (f"{DEAD_KEY_PREFIX}{name}",))
        conn.commit()
    finally:
        conn.close()


class FetcherRouter:
    """管理所有渠道的注册、选取和分派"""

    def __init__(self):
        self.breakers: Dict[str, FetcherCircuitBreaker] = {}
        self._order: List[str] = []
        self._labels: Dict[str, str] = {}

    def get_label(self, name: str) -> str:
        """获取渠道的显示名，如 cf节点1-wq1.8419609.xyz、socks5-127.0.0.1:1080、直连"""
        return self._labels.get(name, name)

    def refresh_from_config(self, cooldown_seconds: int = 30,
                            death_threshold: int = 5):
        """从 fetcher_config 读取渠道列表，生成 breaker，恢复 dead 状态"""
        from utils.fetcher_config import get_cf_worker_urls, get_proxy_urls

        proxy_urls = get_proxy_urls()
        cf_urls = get_cf_worker_urls()

        self._labels = {}
        names: List[str] = []
        for i, url in enumerate(proxy_urls):
            name = f"proxy_{i}"
            names.append(name)
            self._labels[name] = f"socks5-{self._extract_display(url)}"
        for i, url in enumerate(cf_urls):
            name = f"cf_node_{i}"
            names.append(name)
            self._labels[name] = f"cf节点{i+1}-{self._extract_display(url)}"
        names.append("direct")
        self._labels["direct"] = "直连"

        dead_names = _load_dead_names()

        new_breakers: Dict[str, FetcherCircuitBreaker] = {}
        for name in names:
            if name in self.breakers:
                breaker = self.breakers[name]
                breaker.cooldown_seconds = cooldown_seconds
                breaker.death_threshold = death_threshold
                # 根据持久化的 dead 列表同步状态
                if name in dead_names:
                    breaker._state = "dead"
                elif breaker._state == "dead":
                    breaker._state = "active"
            else:
                breaker = FetcherCircuitBreaker(
                    name, cooldown_seconds, death_threshold
                )
                if name in dead_names:
                    breaker._state = "dead"
            new_breakers[name] = breaker

        self.breakers = new_breakers
        self._order = names
        logger.info("FetcherRouter refreshed: %d channels", len(names))

    @staticmethod
    def _extract_display(url: str) -> str:
        """从 URL 中提取展示用的简短标识，如 wq1.8419609.xyz、127.0.0.1:1080"""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            host = parsed.hostname or url
            port = parsed.port
            return f"{host}:{port}" if port else host
        except Exception:
            return url

    def select_fetcher(self, article_link: str,
                       specified: Optional[str] = None) -> Optional[str]:
        """按优先级选取可用渠道。

        跳过 dead、跳过 cooling、跳过该文章已试过且失败的渠道。
        若 specified 合法且可用，优先使用。
        """
        from utils.fetch_logs import get_tried_fetchers_for_article

        tried = get_tried_fetchers_for_article(article_link)

        # 若指定了渠道且符合条件，直接返回
        if specified is not None and specified in self.breakers:
            breaker = self.breakers[specified]
            if breaker.is_available() and specified not in tried:
                return specified

        # 按优先级顺序遍历
        for name in self._order:
            breaker = self.breakers[name]
            if not breaker.is_available():
                continue
            if name in tried:
                continue
            return name

        return None

    async def execute(self, fetcher_name: str, url: str,
                      extra_headers: Optional[Dict] = None,
                      timeout: int = 30) -> Optional[str]:
        """根据渠道名分派到对应的抓取实现"""
        if fetcher_name.startswith("cf_node_"):
            from utils.cf_worker_client import cf_worker_client
            return await cf_worker_client.fetch(url)
        elif fetcher_name.startswith("proxy_"):
            from utils.http_client import fetch_page
            return await fetch_page(
                url, extra_headers=extra_headers, timeout=timeout,
                allow_direct_fallback=False,
            )
        elif fetcher_name == "direct":
            from utils.http_client import fetch_page
            return await fetch_page(
                url, extra_headers=extra_headers, timeout=timeout,
                allow_direct_fallback=True,
            )
        else:
            raise ValueError(f"Unknown fetcher: {fetcher_name}")

    def record_result(self, name: str, success: bool,
                      fail_type: str = ""):
        """记录抓取结果，更新熔断器状态并持久化 dead"""
        breaker = self.breakers.get(name)
        if breaker is None:
            logger.warning("record_result: unknown fetcher %s", name)
            return

        if success:
            breaker.record_success()
            _clear_dead(name)
        elif fail_type == "network_error":
            became_dead = breaker.record_failure()
            if became_dead:
                _persist_dead(name)

    def revive_fetcher(self, name: str):
        """手动复活一个渠道"""
        breaker = self.breakers.get(name)
        if breaker is None:
            logger.warning("revive_fetcher: unknown fetcher %s", name)
            return
        breaker.revive()
        _clear_dead(name)

    def all_status(self) -> List[dict]:
        """返回所有渠道的熔断器状态"""
        return [self.breakers[name].status_dict() for name in self._order]


# 模块级单例
fetcher_router = FetcherRouter()
