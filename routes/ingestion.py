#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
入库管理路由
"""
import asyncio
import logging
from typing import Optional, List

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from utils import ingestion_store, rss_store

logger = logging.getLogger(__name__)
router = APIRouter()


class IngestionResponse(BaseModel):
    success: bool
    data: dict = {}
    error: Optional[str] = None


@router.get("/admin/dashboard", summary="看板数据聚合")
async def dashboard_stats():
    try:
        from utils.auth_manager import auth_manager
        status = auth_manager.get_status()
        stats = ingestion_store.get_dashboard_stats()
        stats["online"] = status.get("authenticated", False)
        stats["nickname"] = status.get("nickname", "")
        return {"success": True, "data": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/admin/ingestion", summary="查询入库记录")
async def query_ingestion(
    fakeid: Optional[str] = Query(None, description="按公众号筛选"),
    status: Optional[str] = Query(None, description="按状态筛选: success/failed/pending"),
    channel: Optional[str] = Query(None, description="按渠道筛选: poll/deep_fetch"),
    keyword: Optional[str] = Query(None, description="搜索链接/标题/错误"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(30, ge=10, le=200, description="每页数量"),
):
    logs = ingestion_store.query_ingestion(
        fakeid=fakeid, status=status, channel=channel,
        keyword=keyword, page=page, per_page=per_page,
    )
    total = ingestion_store.count_ingestion(
        fakeid=fakeid, status=status, channel=channel, keyword=keyword,
    )
    return IngestionResponse(
        success=True,
        data={
            "logs": logs,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    )


@router.get("/admin/ingestion/stats", summary="入库统计")
async def ingestion_stats():
    stats = ingestion_store.get_ingestion_stats()
    return IngestionResponse(success=True, data=stats)


class RetryRequest(BaseModel):
    fakeid: Optional[str] = None
    article_links: Optional[List[str]] = None
    limit: int = Field(10, ge=1, le=50, description="一次最多重试数量")
    fetcher: Optional[str] = None


@router.post("/admin/ingestion/retry", summary="重试失败的入库")
async def retry_ingestion(req: RetryRequest):
    if req.article_links:
        links = req.article_links
        for link in links:
            fid = req.fakeid or ""
            ingestion_store.reset_for_retry(fid, link, fetcher=req.fetcher or "")
    else:
        failed = ingestion_store.get_failed_articles_for_retry(
            fakeid=req.fakeid, limit=req.limit,
        )
        for f in failed:
            ingestion_store.reset_for_retry(
                f["fakeid"], f["article_link"], fetcher=req.fetcher or "",
            )
        links = [f["article_link"] for f in failed if f.get("article_link")]

    from utils.fetch_worker import fetch_worker
    fetch_worker.wake()
    return IngestionResponse(
        success=True,
        data={"retried": len(links) if req.article_links else len(links)},
    )


@router.get("/admin/ingestion/worker-status", summary="Worker 运行状态")
async def worker_status():
    from utils.fetch_worker import fetch_worker
    return {"success": True, "data": fetch_worker.status}


@router.post("/admin/ingestion/worker/trigger", summary="手动唤醒 Worker")
async def worker_trigger():
    from utils.fetch_worker import fetch_worker
    fetch_worker.wake()
    return {"success": True, "message": "Worker awoken"}


@router.post("/admin/ingestion/worker/pause", summary="切换 Worker 暂停状态")
async def worker_pause():
    from utils.fetch_worker import fetch_worker
    paused = await fetch_worker.toggle_pause()
    return {
        "success": True,
        "data": {"paused": paused},
        "message": "Worker paused" if paused else "Worker resumed",
    }


class ReviveFetcherRequest(BaseModel):
    fetcher_name: str


@router.post("/admin/ingestion/worker/revive-fetcher",
             summary="手动启用已 dead 渠道")
async def revive_fetcher(req: ReviveFetcherRequest):
    from utils.fetch_router import fetcher_router
    fetcher_router.revive_fetcher(req.fetcher_name)
    return {"success": True, "message": f"Fetcher {req.fetcher_name} revived"}


@router.post("/admin/ingestion/cleanup", summary="清理旧入库记录")
async def cleanup_ingestion(retain_days: int = Query(30, ge=1, le=365)):
    deleted = ingestion_store.cleanup_old_ingestion(retain_days=retain_days)
    return {"success": True, "data": {"deleted": deleted, "retain_days": retain_days}}


class ToggleArticleRequest(BaseModel):
    fakeid: str
    article_link: str


@router.post("/admin/ingestion/ban", summary="禁止入库")
async def ban_ingestion(req: ToggleArticleRequest):
    ingestion_store.ban_article(req.fakeid, req.article_link)
    return {"success": True, "message": "已禁止入库"}


@router.post("/admin/ingestion/unban", summary="解除禁止入库")
async def unban_ingestion(req: ToggleArticleRequest):
    ingestion_store.unban_article(req.fakeid, req.article_link)
    from utils.fetch_worker import fetch_worker
    fetch_worker.wake()
    return {"success": True, "message": "已解除禁止，重新加入队列"}
