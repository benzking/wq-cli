#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信管理后台 API 客户端
封装 appmsgpublish 等 JSON API 的请求：
curl_cffi TLS 伪装 + 可配置代理 + 随机 UA + 统一错误分类。
"""
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

from utils.user_agent import random_ua

try:
    from curl_cffi.requests import Session as CurlSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)
_local = threading.local()


@dataclass
class MpApiResult:
    """fetch_mp_api 的统一返回类型"""
    data: Optional[dict] = None
    error_type: str = ""  # "" | "frequency_control" | "token_expired" | "invalid_fakeid" | "network_error" | "unknown"

    @property
    def is_ok(self) -> bool:
        return self.data is not None and self.error_type == ""


def _get_session():
    """每线程一个持久 CurlSession，复用 TCP/TLS 连接"""
    if not HAS_CURL_CFFI:
        raise RuntimeError("curl_cffi not available")
    if not hasattr(_local, 'session'):
        _local.session = CurlSession(impersonate="chrome120")
    return _local.session


def _classify_error(ret_code: int, err_msg: str) -> str:
    """将微信 ret code 映射为结构化错误类型"""
    if ret_code == 200013:
        return "frequency_control"
    if ret_code == 200003:
        return "token_expired"
    if ret_code == 200002 and "invalid arg" in (err_msg or "").lower():
        return "invalid_fakeid"
    return "unknown"


async def fetch_mp_api(
    url: str,
    params: dict,
    creds: dict,
    use_proxy: bool = False,
    timeout: int = 30,
) -> MpApiResult:
    """
    请求微信管理后台 JSON API。

    Args:
        url: API URL
        params: 查询参数
        creds: {"token": "...", "cookie": "..."}
        use_proxy: 是否通过代理池转发
        timeout: 超时秒数

    Returns:
        MpApiResult: .is_ok 为 True 时 .data 是完整 JSON dict
    """
    from utils.http_client import build_headers

    headers = build_headers()
    headers["Referer"] = "https://mp.weixin.qq.com/"
    headers["Cookie"] = creds.get("cookie", "")

    proxy = None
    if use_proxy:
        from utils.proxy_pool import proxy_pool
        proxy = proxy_pool.next()

    loop = asyncio.get_event_loop()

    if HAS_CURL_CFFI:
        try:
            data = await loop.run_in_executor(
                _executor,
                _fetch_sync_curl, url, params, headers, proxy, timeout,
            )
        except Exception as e:
            logger.warning("curl_cffi request failed: %s", e)
            if use_proxy and proxy:
                from utils.proxy_pool import proxy_pool
                proxy_pool.mark_failed(proxy)
            return MpApiResult(error_type="network_error")
    else:
        try:
            data = await _fetch_httpx_fallback(url, params, headers, timeout)
        except Exception as e:
            logger.warning("httpx fallback failed: %s", e)
            return MpApiResult(error_type="network_error")

    if data is None:
        return MpApiResult(error_type="network_error")

    base_resp = data.get("base_resp", {})
    ret_code = base_resp.get("ret", -1)

    if ret_code == 0:
        if use_proxy and proxy:
            from utils.proxy_pool import proxy_pool
            proxy_pool.mark_ok(proxy)
        return MpApiResult(data=data)

    error_type = _classify_error(ret_code, base_resp.get("err_msg", ""))
    logger.warning("WeChat API error: ret=%d type=%s", ret_code, error_type)
    if use_proxy and proxy and error_type in ("frequency_control", "network_error"):
        from utils.proxy_pool import proxy_pool
        proxy_pool.mark_failed(proxy)
    return MpApiResult(error_type=error_type)


def _fetch_sync_curl(
    url: str, params: dict, headers: dict,
    proxy: Optional[str], timeout: int,
) -> Optional[dict]:
    """同步 curl_cffi 请求，在线程池中执行"""
    kwargs = {"timeout": timeout, "allow_redirects": True}
    if proxy:
        kwargs["proxy"] = proxy
    with _get_session() as session:
        resp = session.get(url, params=params, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()


async def _fetch_httpx_fallback(
    url: str, params: dict, headers: dict, timeout: int,
) -> Optional[dict]:
    """httpx 降级请求"""
    async with httpx.AsyncClient(timeout=float(timeout), follow_redirects=True) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()
