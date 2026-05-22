#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取配置读取器
配置优先级: SQLite config 表 → .env 环境变量 → 空值（对应等级跳过）
启动时自动迁移 .env 到 SQLite（一次性）
"""

import json
import logging
import os
import sqlite3
from typing import List

logger = logging.getLogger(__name__)

CF_WORKER_URLS_KEY = "cf_worker_urls"
PROXY_URLS_KEY = "proxy_urls"


def _get_env_list(key: str) -> List[str]:
    raw = os.getenv(key, "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _get_config_list(key: str) -> List[str]:
    try:
        from utils.rss_store import get_config
        raw = get_config(key)
    except (sqlite3.OperationalError, ImportError):
        return []
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [item.strip() for item in data if isinstance(item, str) and item.strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _set_config_list(key: str, items: List[str]):
    try:
        from utils.rss_store import set_config
        set_config(key, json.dumps(items, ensure_ascii=False))
    except (sqlite3.OperationalError, ImportError):
        pass


def _migrate_if_needed():
    """启动时：如果 SQLite 中无配置但 .env 中有值，自动写入 SQLite"""
    try:
        from utils.rss_store import get_config
        cf_sqlite = get_config(CF_WORKER_URLS_KEY)
        proxy_sqlite = get_config(PROXY_URLS_KEY)
    except (sqlite3.OperationalError, ImportError):
        return

    if cf_sqlite is None:
        env_cf = _get_env_list("CF_WORKER_URLS")
        if env_cf:
            _set_config_list(CF_WORKER_URLS_KEY, env_cf)
            logger.info("Migrated CF_WORKER_URLS from .env to SQLite: %d nodes", len(env_cf))

    if proxy_sqlite is None:
        env_proxy = _get_env_list("PROXY_URLS")
        if env_proxy:
            _set_config_list(PROXY_URLS_KEY, env_proxy)
            logger.info("Migrated PROXY_URLS from .env to SQLite: %d proxies", len(env_proxy))


def get_cf_worker_urls() -> List[str]:
    urls = _get_config_list(CF_WORKER_URLS_KEY)
    if not urls:
        urls = _get_env_list("CF_WORKER_URLS")
    return urls


def get_proxy_urls() -> List[str]:
    urls = _get_config_list(PROXY_URLS_KEY)
    if not urls:
        urls = _get_env_list("PROXY_URLS")
    return urls


def get_active_levels() -> List[str]:
    levels = []
    if get_cf_worker_urls():
        levels.append("L1")
    if get_proxy_urls():
        levels.append("L2")
    levels.append("L3")
    return levels


def set_cf_worker_urls(urls: List[str]):
    _set_config_list(CF_WORKER_URLS_KEY, urls)


def set_proxy_urls(urls: List[str]):
    _set_config_list(PROXY_URLS_KEY, urls)


def reset_to_env():
    """清空 SQLite 配置，恢复 .env 默认"""
    try:
        from utils.rss_store import set_config
        set_config(CF_WORKER_URLS_KEY, "")
        set_config(PROXY_URLS_KEY, "")
        logger.info("Config reset: cleared SQLite config, falling back to .env")
    except (sqlite3.OperationalError, ImportError):
        pass


# 模块加载时执行一次性迁移
_migrate_if_needed()
