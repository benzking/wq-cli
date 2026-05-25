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


@router.post("/admin/ingestion/retry", summary="重试失败的入库")
async def retry_ingestion(req: RetryRequest):
    if req.article_links:
        links = req.article_links
        # 标记为 pending 并重置
        for link in links:
            fid = req.fakeid or ""
            ingestion_store.reset_ingestion_status(fid, link)
    else:
        failed = ingestion_store.get_failed_articles_for_retry(fakeid=req.fakeid, limit=req.limit)
        links = [f["article_link"] for f in failed if f.get("article_link")]
        for f in failed:
            ingestion_store.reset_ingestion_status(f["fakeid"], f["article_link"])

    # 异步抓取这些链接
    try:
        retry_count = 0
        if links:
            from utils.article_fetcher import fetch_articles_batch
            import os
            token = os.getenv("WECHAT_TOKEN", "")
            cookie = os.getenv("WECHAT_COOKIE", "")
            results = await fetch_articles_batch(links, max_concurrency=3, timeout=60, wechat_token=token, wechat_cookie=cookie)
            from utils.content_processor import process_article_content
            site_url = os.getenv("SITE_URL", "http://localhost:5000").rstrip("/")

            for link, html in results.items():
                if html and not _is_verification(html):
                    processed = process_article_content(html, proxy_base_url=site_url)
                    content = processed.get("content", "")
                    # 尝试保存
                    fid = req.fakeid or ""
                    success = bool(content and content.strip())
                    ingestion_store.log_ingestion_result(
                        fid, link, success,
                        error_msg="" if success else "empty content",
                    )
                    if success:
                        retry_count += 1

        return IngestionResponse(
            success=True,
            data={"retried": retry_count, "links": len(links)},
        )
    except Exception as e:
        return IngestionResponse(success=False, error=str(e))


def _is_verification(html: str) -> bool:
    hl = html.lower()
    return "verifycode" in hl or "请输入图片中的字符" in html or "环境异常" in html


@router.post("/admin/ingestion/cleanup", summary="清理旧入库记录")
async def cleanup_ingestion(retain_days: int = Query(30, ge=1, le=365)):
    deleted = ingestion_store.cleanup_old_ingestion(retain_days=retain_days)
    return {"success": True, "data": {"deleted": deleted, "retain_days": retain_days}}
