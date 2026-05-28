#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
抓取退避配置模块
根据失败类型返回重试间隔和最大重试次数
"""

import os
from typing import Dict, Tuple, Optional

# 默认配置: fail_type -> (interval_seconds, max_retries)
# max_retries 为 None 表示由渠道数动态决定
_DEFAULTS: Dict[str, Tuple[Optional[int], Optional[int]]] = {
    "network_error": (60, None),
    "verification": (1800, 2),
    "no_content": (0, 3),
    "parse_error": (0, 2),
    "unavailable": (None, 0),
}

_SUFFIX_INTERVAL = "_INTERVAL_"
_SUFFIX_MAX_RETRIES = "_MAX_RETRIES_"


def _env_int(key: str) -> Optional[int]:
    """读取环境变量并转为 int, 未设置或无效时返回 None."""
    val = os.environ.get(key)
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        return None


def get_backoff(fail_type: str) -> Tuple[Optional[int], Optional[int]]:
    """返回 (interval_seconds, max_retries).

    max_retries 为 None 时表示由渠道数动态决定（仅 network_error).
    interval 为 None 时表示不重试（如 unavailable).
    """
    defaults = _DEFAULTS.get(fail_type)
    if defaults is None:
        raise ValueError(f"Unknown fail_type: {fail_type!r}")

    interval, max_retries = defaults

    # 环境变量可覆盖默认值, 前缀格式 FETCH_{fail_type_upper}_{SUFFIX}
    prefix = fail_type.upper()

    env_interval = _env_int(f"FETCH_INTERVAL_{prefix}")
    if env_interval is not None:
        interval = env_interval

    env_max = _env_int(f"FETCH_MAX_RETRIES_{prefix}")
    if env_max is not None:
        max_retries = env_max

    return interval, max_retries
