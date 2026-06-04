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
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Query, Request, HTTPException
from pydantic import BaseModel, Field

from utils import rss_store
from utils.image_proxy import proxy_image_url

logger = logging.getLogger(__name__)

router = APIRouter()


def _make_content_disposition(filename: str) -> str:
    """生成 RFC 5987 兼容的 Content-Disposition header，支持中文文件名"""
    ascii_safe = filename.encode("ascii", "ignore").decode("ascii") or "download"
    encoded = quote(filename, safe="")
    return f'attachment; filename="{ascii_safe}"; filename*=UTF-8\'\'{encoded}'


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


@router.patch("/browse/article/{article_id}/star", summary="切换文章星标")
async def toggle_star(article_id: int):
    new_state = rss_store.toggle_star(article_id)
    if new_state is None:
        return {"success": False, "error": "文章不存在"}
    return {"success": True, "data": {"starred": new_state}}


@router.post("/browse/article/{article_id}/refetch", summary="重新抓取文章")
async def refetch_article(article_id: int):
    article = rss_store.get_article_by_id(article_id)
    if not article:
        return {"success": False, "error": "文章不存在"}
    link = article.get("link")
    if not link:
        return {"success": False, "error": "文章缺少链接"}
    import asyncio as _asyncio
    _asyncio.create_task(_do_refetch(link, article.get("fakeid", "")))
    return {"success": True, "message": "已加入重抓队列"}


async def _do_refetch(link: str, fakeid: str):
    try:
        from utils.article_fetcher import fetch_articles_batch
        from utils.content_processor import process_article_content
        token = os.getenv("WECHAT_TOKEN", "")
        cookie = os.getenv("WECHAT_COOKIE", "")
        results = await fetch_articles_batch([link], max_concurrency=1, timeout=60,
                                              wechat_token=token, wechat_cookie=cookie)
        html = results.get(link)
        if html and not _is_verification(html):
            processed = process_article_content(html,
                proxy_base_url=os.getenv("SITE_URL", "http://localhost:5000").rstrip("/"))
            content = processed.get("content", "")
            if content and content.strip():
                rss_store.save_articles(fakeid, [{
                    "aid": "", "title": "", "link": link,
                    "digest": "", "cover": "", "author": "",
                    "publish_time": int(__import__("time").time()),
                }])
    except Exception:
        logger = logging.getLogger(__name__)
        logger.exception("refetch failed for %s", link)


def _is_verification(html: str) -> bool:
    hl = html.lower()
    return "verifycode" in hl or "请输入图片中的字符" in html or "环境异常" in html


@router.get("/browse/article/{article_id}/export", summary="导出文章 Markdown（有图打包 ZIP）")
async def export_article(article_id: int, request: Request):
    """
    导出文章为 Obsidian 规范 Markdown。
    - 无图片：直接返回 .md 文件
    - 有图片：打包 ZIP（MD + 图片），图片优先本地缓存，未命中时从远端下载
    """
    import zipfile
    import io as _io
    import re as _re
    from pathlib import Path as _Path
    from urllib.parse import unquote, urlparse, parse_qs
    from datetime import datetime
    from fastapi.responses import StreamingResponse, Response

    article = rss_store.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    content = article.get("content", "") or ""
    title = article.get("title", "untitled")
    nickname = article.get("nickname", "") or article.get("fakeid", "unknown")
    publish_time = article.get("publish_time", 0)

    # ── 命名 ──
    def safe_filename(s: str) -> str:
        """替换非法文件名字符，保留中文等非 ASCII 字符"""
        return _re.sub(r'[\\/*?:"<>|]', '_', s).strip() or "untitled"

    def format_date(ts: int) -> str:
        """Unix timestamp → YYYYMMDD"""
        return datetime.fromtimestamp(ts).strftime("%Y%m%d")

    safe_title = safe_filename(title)
    date_str = format_date(publish_time) if publish_time else "00000000"
    base_name = f"{safe_filename(nickname)}-{date_str}-{safe_title}"

    # ── 1. 提取图片 URL 列表（在转 MD 之前，从原始 HTML 提取）──
    img_urls = _re.findall(r'<img[^>]*\s(?:data-)?src="([^"]+)"', content, _re.IGNORECASE)
    # 去重保持顺序
    seen = set()
    unique_urls = []
    for u in img_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
    img_urls = unique_urls

    # ── 2. HTML → Markdown ──
    from utils.content_processor import html_to_markdown
    md_body = html_to_markdown(content)
    if not md_body:
        md_body = f"# {title}\n\n> 来源: {nickname} · {publish_time}\n\n*(文章内容为空)*"

    # ── 3. 图片收集（混合策略）──
    local_dir = _Path(__file__).parent.parent / "data" / "images" / str(article_id)

    def extract_original_url(proxy_or_url: str) -> str:
        """从代理 URL 反解原始图片地址"""
        if "/api/image?url=" in proxy_or_url:
            try:
                parsed = urlparse(proxy_or_url)
                qs = parse_qs(parsed.query)
                encoded = qs.get("url", [proxy_or_url])[0]
                return unquote(encoded)
            except Exception:
                return proxy_or_url
        return proxy_or_url

    async def download_image(url: str, timeout: int = 15) -> bytes | None:
        """HTTP 下载图片（异步，不阻塞 event loop）"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.content
        except Exception:
            pass
        return None

    def guess_ext(url: str, data: bytes | None = None) -> str:
        """推断图片扩展名"""
        # 从 URL 路径推断
        path = urlparse(url).path.lower()
        for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"):
            if path.endswith(ext):
                return ext if ext != ".jpeg" else ".jpg"
        # 从文件头魔数推断
        if data:
            if data[:3] == b"\xff\xd8\xff":
                return ".jpg"
            if data[:8] == b"\x89PNG\r\n\x1a\n":
                return ".png"
            if data[:6] in (b"GIF87a", b"GIF89a"):
                return ".gif"
            if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                return ".webp"
        return ".jpg"

    collected_images: list[dict] = []  # [{name, data}]
    url_to_local: dict[str, str] = {}  # 原始 img_url → 本地文件名

    for i, img_url in enumerate(img_urls):
        local_name = f"img_{i+1:03d}"
        img_data = None
        ext = ".jpg"

        # 策略 1：本地缓存
        if local_dir.exists():
            for candidate_ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                candidate = local_dir / f"img_{i+1:03d}{candidate_ext}"
                if candidate.exists():
                    img_data = candidate.read_bytes()
                    ext = candidate_ext if candidate_ext != ".jpeg" else ".jpg"
                    break

        # 策略 2：远端下载
        if img_data is None:
            original_url = extract_original_url(img_url)
            img_data = await download_image(original_url)
            if img_data:
                ext = guess_ext(original_url, img_data)

        # 策略 3：跳过
        if img_data is None:
            url_to_local[img_url] = img_url  # 保留原始 URL 不替换
            continue

        local_name_with_ext = f"{local_name}{ext}"
        collected_images.append({
            "name": local_name_with_ext,
            "data": img_data,
        })
        url_to_local[img_url] = f"./{local_name_with_ext}"

    # ── 4. 替换 MD 中的图片 URL 为相对路径 ──
    for original_url, local_path in url_to_local.items():
        md_body = md_body.replace(original_url, local_path)

    # ── 5. 无图片 → 直接返回 .md ──
    if not collected_images:
        md_full = f"# {title}\n\n> 来源: {nickname} · {publish_time}\n\n{md_body}"
        return Response(
            content=md_full.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": _make_content_disposition(f"{base_name}.md")
            },
        )

    # ── 6. 有图片 → 打包 ZIP ──
    md_full = f"# {title}\n\n> 来源: {nickname} · {publish_time}\n\n{md_body}"
    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_name}.md", md_full)
        for img in collected_images:
            zf.writestr(img["name"], img["data"])

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": _make_content_disposition(f"{base_name}.zip")
        },
    )
