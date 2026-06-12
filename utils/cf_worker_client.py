#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CF Worker 节点池客户端
通过 Cloudflare Worker 代理获取微信公众号文章。
节点轮转、单节点冷却、全层熔断、后台健康探测。
"""

import asyncio
import logging
import time
import threading
from typing import Optional, List, Dict
from urllib.parse import quote

import httpx

from utils.fetcher_config import get_cf_worker_urls

logger = logging.getLogger(__name__)

FAIL_COOLDOWN = 120          # 单节点连续失败冷却时间
CONSECUTIVE_FAIL_THRESHOLD = 3  # 连续失败次数阈值
CIRCUIT_BREAKER_RATIO = 0.8  # 80% 节点冷却 → 熔断
CIRCUIT_BREAKER_DURATION = 60  # 熔断持续时间
HEALTH_CHECK_INTERVAL = 300  # 后台健康探测间隔
L1_TIMEOUT = 15.0            # CF Worker 请求超时


class CFWorkerClient:
    """CF Worker 节点池"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._lock = threading.Lock()
        self._index = 0
        self._fail_counts: Dict[str, int] = {}
        self._fail_until: Dict[str, float] = {}
        self._circuit_breaker_until: float = 0.0
        self._health_task: Optional[asyncio.Task] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._initialized = True

    @property
    def enabled(self) -> bool:
        return len(get_cf_worker_urls()) > 0

    async def start(self):
        """启动后台健康探测"""
        self._http_client = httpx.AsyncClient(
            timeout=L1_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        self._health_task = asyncio.create_task(self._health_check_loop())
        logger.info("CF Worker client started")

    async def stop(self):
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        if self._http_client:
            await self._http_client.aclose()

    def _get_nodes(self) -> List[str]:
        return get_cf_worker_urls()

    def _is_circuit_open(self) -> bool:
        return time.time() < self._circuit_breaker_until

    def _open_circuit(self):
        self._circuit_breaker_until = time.time() + CIRCUIT_BREAKER_DURATION
        logger.warning("CF Worker circuit breaker OPEN for %ds", CIRCUIT_BREAKER_DURATION)

    def _check_circuit(self):
        """检查是否需要开熔断：80% 节点冷却 → 开熔断"""
        nodes = self._get_nodes()
        if not nodes:
            return
        now = time.time()
        cooled = sum(1 for n in nodes if self._fail_until.get(n, 0) > now)
        if cooled / len(nodes) >= CIRCUIT_BREAKER_RATIO:
            self._open_circuit()

    def next_node(self) -> Optional[str]:
        if not self._get_nodes():
            return None
        if self._is_circuit_open():
            return None
        now = time.time()
        with self._lock:
            nodes = self._get_nodes()
            for _ in range(len(nodes)):
                self._index = (self._index + 1) % len(nodes)
                node = nodes[self._index]
                if self._fail_until.get(node, 0) <= now:
                    return node
        return None

    def mark_failed(self, node: str):
        with self._lock:
            self._fail_counts[node] = self._fail_counts.get(node, 0) + 1
            if self._fail_counts[node] >= CONSECUTIVE_FAIL_THRESHOLD:
                self._fail_until[node] = time.time() + FAIL_COOLDOWN
                logger.warning("CF Worker %s cooled for %ds (fail count=%d)",
                             node, FAIL_COOLDOWN, self._fail_counts[node])
        self._check_circuit()

    def mark_ok(self, node: str):
        with self._lock:
            self._fail_counts[node] = 0
            self._fail_until.pop(node, None)

    def get_status(self) -> dict:
        nodes = self._get_nodes()
        now = time.time()
        healthy = []
        cooldown = []
        for n in nodes:
            if self._fail_until.get(n, 0) > now:
                cooldown.append(n)
            else:
                healthy.append(n)
        return {
            "healthy": len(healthy),
            "cooldown": len(cooldown),
            "total": len(nodes),
            "circuit_open": self._is_circuit_open(),
        }

    async def fetch(self, article_url: str,
                    node_url: Optional[str] = None) -> Optional[str]:
        """
        通过 CF Worker 代理获取文章内容。

        参数:
            node_url: 指定具体节点 URL（FetcherRouter 渠道隔离用）。
                      为 None 时使用内部节点池轮转（兼容旧路径: ArticleFallbackFetcher）。
        """
        if node_url is not None:
            # 指定节点模式 — 直达目标，不经过内部池管理（由 FetcherRouter 负责熔断）
            return await self._do_fetch_url(article_url, node_url)

        # 池模式 — 内部轮转 + 冷却管理
        node = self.next_node()
        if not node:
            logger.warning("[L1] No available CF Worker node")
            return None

        try:
            html = await self._do_fetch_url(article_url, node)
            self.mark_ok(node)
            return html
        except Exception as e:
            logger.warning("[L1] CF Worker pool fetch failed: %s", str(e)[:80])
            self.mark_failed(node)
            return None

    async def _do_fetch_url(self, article_url: str,
                            node_url: str) -> str:
        """对单个 CF Worker 节点发请求，成功返回 HTML，失败抛异常"""
        node_url = node_url.rstrip("/")
        encoded_url = quote(article_url, safe="")
        proxy_url = f"{node_url}/?url={encoded_url}&preset=mp"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "Chrome/120.0.0.0 Safari/537.36",
        }

        if self._http_client is None:
            async with httpx.AsyncClient(timeout=L1_TIMEOUT) as client:
                resp = await client.get(proxy_url, headers=headers)
        else:
            resp = await self._http_client.get(proxy_url, headers=headers)

        if resp.status_code == 200 and len(resp.text) > 500:
            return resp.text

        reason = f"status={resp.status_code} len={len(resp.text)}"
        try:
            err_data = resp.json()
            if isinstance(err_data, dict) and "error" in err_data:
                retry_flag = err_data.get("retry", False)
                reason = f"worker_error={err_data['error']} retry={retry_flag} status={resp.status_code}"
        except Exception:
            if resp.text:
                reason = f"status={resp.status_code} len={len(resp.text)} body={resp.text[:200]}"

        raise Exception(f"CF Worker returned {reason}")

    async def _health_check_loop(self):
        """后台每 300s 探测所有节点"""
        while True:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                await self._probe_all()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("Health check error: %s", e)

    async def _probe_all(self):
        """对所有节点发健康探测请求，优先 /health，fallback 到旧方式"""
        nodes = self._get_nodes()
        if not nodes:
            return
        logger.info("[L1 Health] Probing %d CF Worker nodes", len(nodes))
        for node in nodes:
            try:
                node_url = node.rstrip("/")
                client = self._http_client or httpx.AsyncClient(timeout=10.0)

                # 优先用 /health 轻量端点
                try:
                    resp = await client.get(f"{node_url}/health")
                    if resp.status_code == 200:
                        self.mark_ok(node)
                        continue
                except Exception:
                    pass

                # 降级：旧节点不支持 /health，用原方式探测
                probe_url = f"{node_url}/?url={quote('https://mp.weixin.qq.com', safe='')}&preset=mp"
                resp = await client.get(probe_url)
                if resp.status_code == 200:
                    self.mark_ok(node)
                else:
                    self.mark_failed(node)
            except Exception:
                self.mark_failed(node)

    async def test_nodes(self) -> List[dict]:
        """异步测试所有节点的速度和可用性，返回逐节点结果"""
        import time as time_mod
        nodes = self._get_nodes()
        if not nodes:
            return []

        async def test_one(node: str) -> dict:
            node_url = node.rstrip("/")
            test_url = f"{node_url}/?url={quote('https://mp.weixin.qq.com', safe='')}&preset=mp"
            start = time_mod.monotonic()
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(test_url)
                latency = (time_mod.monotonic() - start) * 1000
                if resp.status_code == 200:
                    return {"level": "L1", "node": node, "status": "ok", "latency_ms": round(latency, 1)}
                return {"level": "L1", "node": node, "status": "fail",
                        "latency_ms": round(latency, 1), "error": f"HTTP {resp.status_code}"}
            except Exception as e:
                latency = (time_mod.monotonic() - start) * 1000
                return {"level": "L1", "node": node, "status": "fail",
                        "latency_ms": round(latency, 1), "error": str(e)[:100]}

        tasks = [test_one(node) for node in nodes]
        return list(await asyncio.gather(*tasks))


cf_worker_client = CFWorkerClient()
