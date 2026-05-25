#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
系统日志路由
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from utils import system_logger

logger = logging.getLogger(__name__)
router = APIRouter()


class LogsResponse(BaseModel):
    success: bool
    data: dict = {}
    error: Optional[str] = None


@router.get("/admin/logs", response_model=LogsResponse, summary="查询系统日志")
async def query_logs(
    level: Optional[str] = Query(None, description="日志级别: INFO/WARNING/ERROR"),
    module: Optional[str] = Query(None, description="模块名模糊匹配"),
    keyword: Optional[str] = Query(None, description="日志内容搜索"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(50, ge=10, le=200, description="每页数量"),
    since: Optional[float] = Query(None, description="开始时间戳"),
    until: Optional[float] = Query(None, description="结束时间戳"),
):
    logs = system_logger.query_logs(
        level=level, module=module, keyword=keyword,
        page=page, per_page=per_page, since=since, until=until,
    )
    total = system_logger.count_logs(
        level=level, module=module, keyword=keyword, since=since, until=until,
    )

    return LogsResponse(
        success=True,
        data={
            "logs": logs,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    )


@router.post("/admin/logs/cleanup", summary="清理旧日志")
async def cleanup_logs(retain_days: int = Query(7, ge=1, le=365, description="保留天数")):
    deleted = system_logger.delete_old_logs(retain_days=retain_days)
    logger.info("Cleaned up %d old log entries (older than %d days)", deleted, retain_days)
    return {"success": True, "data": {"deleted": deleted, "retain_days": retain_days}}


@router.get("/admin/logs/modules", summary="获取日志模块列表")
async def get_log_modules():
    modules = system_logger.get_distinct_modules()
    return {"success": True, "data": {"modules": modules}}
