#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
文章在线浏览路由
"""
import os
import logging
from typing import Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from utils import rss_store
from utils.image_proxy import proxy_image_url

logger = logging.getLogger(__name__)

router = APIRouter()


def get_base_url(request: Request) -> str:
    site_url = os.getenv("SITE_URL", "").strip()
    if site_url:
        return site_url.rstrip("/")
    proto = request.headers.get("X-Forwarded-Proto", "http")
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host", "localhost:5000")
    return f"{proto}://{host}"


class BrowseArticlesResponse(BaseModel):
    success: bool
    data: dict = {}
    error: Optional[str] = None


def _proxy_article_images(article: dict, base_url: str) -> dict:
    """对文章中的图片 URL 进行代理转换"""
    if article.get("cover"):
        article["cover"] = proxy_image_url(article["cover"], base_url)
    if article.get("content"):
        from utils.image_proxy import proxy_content_images
        article["content"] = proxy_content_images(article["content"], base_url)
    return article


@router.get("/browse/articles", response_model=BrowseArticlesResponse,
            summary="浏览已订阅文章")
async def browse_articles(
    request: Request,
    fakeid: Optional[str] = Query(None, description="按公众号 fakeid 筛选"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=5, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="标题/摘要搜索"),
):
    """
    浏览数据库中的已抓取文章（支持分页、筛选、搜索）。
    返回文章的标题、摘要、封面图、发布时间、公众号等。
    """
    subs = rss_store.list_subscriptions()
    nickname_map = {s["fakeid"]: s.get("nickname") or s["fakeid"] for s in subs}

    articles = rss_store.browse_articles(
        fakeid=fakeid,
        page=page,
        per_page=per_page,
        keyword=keyword,
    )
    total = rss_store.count_articles(fakeid=fakeid, keyword=keyword)

    base_url = get_base_url(request)
    for a in articles:
        a["nickname"] = nickname_map.get(a["fakeid"], a["fakeid"])
        if a.get("cover"):
            a["cover"] = proxy_image_url(a["cover"], base_url)

    return BrowseArticlesResponse(
        success=True,
        data={
            "articles": articles,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    )


@router.get("/browse/article/{article_id}", response_model=BrowseArticlesResponse,
            summary="获取文章详情")
async def browse_article_detail(article_id: int, request: Request):
    """
    获取单篇文章完整内容（含 HTML）。
    """
    article = rss_store.get_article_by_id(article_id)
    if not article:
        return BrowseArticlesResponse(
            success=False,
            error="文章不存在",
        )

    base_url = get_base_url(request)
    _proxy_article_images(article, base_url)

    subs = rss_store.list_subscriptions()
    nickname_map = {s["fakeid"]: s.get("nickname") or s["fakeid"] for s in subs}
    article["nickname"] = nickname_map.get(article["fakeid"], article["fakeid"])

    return BrowseArticlesResponse(
        success=True,
        data={"article": article},
    )


@router.get("/browse/subscriptions", response_model=BrowseArticlesResponse,
            summary="获取有文章的订阅列表")
async def browse_subscriptions():
    """获取所有有文章缓存的订阅列表（用于浏览页筛选）。"""
    subs = rss_store.get_subscriptions_with_articles()
    return BrowseArticlesResponse(
        success=True,
        data={"subscriptions": subs},
    )
