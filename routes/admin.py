#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
管理路由 - FastAPI版本
"""

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from utils.auth_manager import auth_manager
from utils import rss_store

router = APIRouter()


# ── 状态管理 ─────────────────────────────────────────────

class StatusResponse(BaseModel):
    """状态响应模型"""
    authenticated: bool
    loggedIn: bool
    account: str
    nickname: Optional[str] = ""
    fakeid: Optional[str] = ""
    expireTime: Optional[int] = 0
    isExpired: Optional[bool] = False
    status: str
    effective_route: Optional[str] = ""


@router.get("/status", response_model=StatusResponse, summary="获取登录状态")
async def get_status():
    """获取当前登录状态"""
    from utils.fetcher_config import get_active_levels
    result = auth_manager.get_status()
    result["effective_route"] = " → ".join(get_active_levels())
    return result


@router.post("/logout", summary="退出登录")
async def logout():
    """退出登录，清除凭证"""
    success = auth_manager.clear_credentials()
    if success:
        return {"success": True, "message": "已退出登录"}
    else:
        return {"success": False, "message": "退出登录失败"}


# ── 黑名单管理 ─────────────────────────────────────────────

class BlacklistItem(BaseModel):
    id: int
    fakeid: str
    nickname: str
    reason: str
    verification_count: int
    is_active: bool
    blacklisted_at: int
    unblacklisted_at: Optional[int]
    note: str


class AddBlacklistRequest(BaseModel):
    fakeid: str = Field(..., description="公众号ID")
    nickname: str = Field("", description="公众号名称")
    reason: str = Field("manual", description="加入原因")
    note: str = Field("", description="备注")


@router.get("/blacklist", summary="获取黑名单列表")
async def get_blacklist():
    """获取公众号黑名单列表"""
    blacklist = rss_store.get_blacklist()
    return {
        "blacklist": [
            BlacklistItem(
                id=bl["id"],
                fakeid=bl["fakeid"],
                nickname=bl["nickname"],
                reason=bl["reason"],
                verification_count=bl["verification_count"],
                is_active=bool(bl["is_active"]),
                blacklisted_at=bl["blacklisted_at"],
                unblacklisted_at=bl["unblacklisted_at"],
                note=bl["note"],
            )
            for bl in blacklist
        ]
    }


@router.post("/blacklist", summary="添加到黑名单")
async def add_to_blacklist(req: AddBlacklistRequest):
    """手动添加公众号到黑名单"""
    success = rss_store.add_to_blacklist(
        fakeid=req.fakeid,
        nickname=req.nickname,
        reason=req.reason,
        note=req.note or "手动添加"
    )
    if success:
        return {"success": True, "message": f"已将 {req.nickname or req.fakeid} 加入黑名单"}
    return {"success": False, "message": "添加失败"}


@router.delete("/blacklist/{fakeid}", summary="从黑名单移除")
async def remove_from_blacklist(fakeid: str):
    """从黑名单移除公众号（标记为非活跃）"""
    success = rss_store.remove_from_blacklist(fakeid)
    if success:
        return {"success": True, "message": "已从黑名单移除"}
    return {"success": False, "message": "移除失败，记录不存在"}


@router.delete("/blacklist/record/{blacklist_id}", summary="永久删除黑名单记录")
async def delete_blacklist_record(blacklist_id: int):
    """永久删除黑名单记录（仅可删除非活跃记录）"""
    success = rss_store.delete_blacklist_record(blacklist_id)
    if success:
        return {"success": True, "message": "记录已删除"}
    return {"success": False, "message": "删除失败，记录不存在或仍在生效中"}


# ── 分类管理 ─────────────────────────────────────────────

class CategoryItem(BaseModel):
    id: int
    name: str
    description: str
    color: str
    sort_order: int
    subscription_count: int
    created_at: int


class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="分类名称")
    description: str = Field("", max_length=200, description="分类描述")
    color: str = Field("blue", description="颜色: blue, green, red, purple, orange, gray")


class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    color: Optional[str] = None


class SetCategoryRequest(BaseModel):
    category_id: Optional[int] = Field(None, description="分类ID，null表示取消分类")


@router.get("/categories", summary="获取分类列表")
async def get_categories():
    """获取所有分类"""
    categories = rss_store.list_categories()
    return {
        "categories": [
            CategoryItem(
                id=c["id"],
                name=c["name"],
                description=c["description"],
                color=c["color"],
                sort_order=c["sort_order"],
                subscription_count=c["subscription_count"],
                created_at=c["created_at"],
            )
            for c in categories
        ]
    }


@router.post("/categories", summary="创建分类")
async def create_category(req: CreateCategoryRequest):
    """创建新分类"""
    category_id = rss_store.create_category(
        name=req.name,
        description=req.description,
        color=req.color
    )
    if category_id:
        return {"success": True, "id": category_id, "message": f"分类 '{req.name}' 创建成功"}
    raise HTTPException(status_code=400, detail="分类名称已存在")


@router.patch("/categories/{category_id}", summary="更新分类")
async def update_category(category_id: int, req: UpdateCategoryRequest):
    """更新分类信息"""
    success = rss_store.update_category(
        category_id=category_id,
        name=req.name,
        description=req.description,
        color=req.color
    )
    if success:
        return {"success": True, "message": "分类已更新"}
    raise HTTPException(status_code=404, detail="分类不存在")


@router.delete("/categories/{category_id}", summary="删除分类")
async def delete_category(category_id: int):
    """删除分类（订阅会自动解除关联）"""
    success = rss_store.delete_category(category_id)
    if success:
        return {"success": True, "message": "分类已删除"}
    raise HTTPException(status_code=404, detail="分类不存在")


@router.get("/categories/{category_id}/subscriptions", summary="获取分类下的订阅")
async def get_category_subscriptions(category_id: int):
    """获取分类下的所有订阅"""
    category = rss_store.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    
    subscriptions = rss_store.get_subscriptions_by_category(category_id)
    return {
        "category": CategoryItem(
            id=category["id"],
            name=category["name"],
            description=category["description"],
            color=category["color"],
            sort_order=category["sort_order"],
            subscription_count=len(subscriptions),
            created_at=category["created_at"],
        ),
        "subscriptions": subscriptions
    }


@router.put("/subscriptions/{fakeid}/category", summary="设置订阅分类")
async def set_subscription_category(fakeid: str, req: SetCategoryRequest):
    """设置订阅的分类"""
    # 如果指定了分类，验证分类存在
    if req.category_id is not None:
        category = rss_store.get_category(req.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
    
    success = rss_store.set_subscription_category(fakeid, req.category_id)
    if success:
        return {"success": True, "message": "分类已设置"}
    raise HTTPException(status_code=404, detail="订阅不存在")


# ── 历史文章获取 ─────────────────────────────────────────────

class FetchHistoryRequest(BaseModel):
    fakeid: str = Field(..., description="公众号ID")
    count: int = Field(1, ge=1, le=100, description="获取数量，1-100篇")


class FetchHistoryResponse(BaseModel):
    success: bool
    message: str
    fetched_count: int = 0
    new_count: int = 0


@router.post("/history/fetch", response_model=FetchHistoryResponse, summary="获取历史文章")
async def fetch_history_articles(req: FetchHistoryRequest):
    """
    获取公众号的历史文章并存入数据库。
    简化版：直接调用微信 API 获取历史文章列表，不涉及用户权限和付费逻辑。
    """
    from utils.auth_manager import auth_manager
    
    # 检查登录状态
    status = auth_manager.get_status()
    if not status.get("authenticated"):
        return FetchHistoryResponse(
            success=False,
            message="未登录，请先扫码登录",
            fetched_count=0,
            new_count=0
        )
    
    # 检查订阅是否存在
    subscriptions = rss_store.list_subscriptions()
    sub = next((s for s in subscriptions if s["fakeid"] == req.fakeid), None)
    if not sub:
        return FetchHistoryResponse(
            success=False,
            message="订阅不存在，请先添加订阅",
            fetched_count=0,
            new_count=0
        )
    
    try:
        # 调用 poller 的内部方法获取文章列表
        fetched_count, new_count = await _fetch_history_internal(
            fakeid=req.fakeid,
            target_count=req.count
        )
        
        return FetchHistoryResponse(
            success=True,
            message=f"获取完成，共获取 {fetched_count} 篇，新增 {new_count} 篇",
            fetched_count=fetched_count,
            new_count=new_count
        )
    except Exception as e:
        return FetchHistoryResponse(
            success=False,
            message=f"获取失败: {str(e)}",
            fetched_count=0,
            new_count=0
        )


async def _fetch_history_internal(fakeid: str, target_count: int) -> tuple:
    """
    内部历史文章获取逻辑。
    
    历史文章定义：通过深度获取功能拉取的文章（标记为 source='deep_fetch'）
    
    流程：
    1. 获取数据库中已有的历史文章数量（source='deep_fetch'）
    2. 从已有历史文章的位置开始翻页，避免重复获取
    3. 保存所有抓取的文章，标记为 source='deep_fetch'
    4. 数据库通过 UNIQUE(fakeid, link) 自动去重：
       - 轮询器已拉取的文章保持 source='poll'（不更新）
       - 只有新文章被标记为 source='deep_fetch'
    5. 达到目标数量或无更多文章时停止
    
    返回 (fetched_count, new_count)。
    """
    import httpx
    import json
    import asyncio
    import random
    
    creds = auth_manager.get_credentials()
    if not creds or not creds.get("token"):
        raise ValueError("登录凭证无效")
    
    # 验证订阅是否存在
    sub = rss_store.get_subscription(fakeid)
    if not sub:
        raise ValueError("订阅不存在")
    
    # 获取数据库中已有的历史文章数量（source='deep_fetch'），从这个位置开始翻页
    existing_historical = rss_store.count_historical_articles(fakeid)
    
    historical_articles = []
    batch_size = 10
    # 从已有历史文章位置开始（跳过已获取的）
    start_batch = existing_historical // batch_size
    batch_num = start_batch
    max_batches = start_batch + 50  # 最多再翻 50 页
    
    while batch_num < max_batches and len(historical_articles) < target_count:
        begin = batch_num * batch_size
        
        params = {
            "begin": begin,
            "count": batch_size,
            "fakeid": fakeid,
            "type": "101_1",
            "free_publish_type": 1,
            "sub_action": "list_ex",
            "token": creds["token"],
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://mp.weixin.qq.com/",
            "Cookie": creds["cookie"],
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://mp.weixin.qq.com/cgi-bin/appmsgpublish",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            result = resp.json()
        
        base_resp = result.get("base_resp", {})
        ret_code = base_resp.get("ret", -1)
        
        if ret_code == 200003:
            raise ValueError("触发验证码，请稍后重试")
        if ret_code != 0:
            raise ValueError(f"微信API错误: ret={ret_code}")
        
        publish_page = result.get("publish_page", {})
        if isinstance(publish_page, str):
            try:
                publish_page = json.loads(publish_page)
            except (json.JSONDecodeError, ValueError):
                batch_num += 1
                continue
        
        if not isinstance(publish_page, dict):
            batch_num += 1
            continue
        
        batch_articles = []
        
        for item in publish_page.get("publish_list", []):
            publish_info = item.get("publish_info", {})
            if isinstance(publish_info, str):
                try:
                    publish_info = json.loads(publish_info)
                except (json.JSONDecodeError, ValueError):
                    continue
            if not isinstance(publish_info, dict):
                continue
            for a in publish_info.get("appmsgex", []):
                # [2026-05-06 简化] 不需要时间判断
                # 数据库有唯一约束 UNIQUE(fakeid, link)
                # 轮询器已拉取的文章（source='poll'）会保持原样
                # 只有新文章才会被标记为 source='deep_fetch'
                batch_articles.append({
                    "aid": a.get("aid", ""),
                    "title": a.get("title", ""),
                    "link": a.get("link", ""),
                    "digest": a.get("digest", ""),
                    "cover": a.get("cover", ""),
                    "author": a.get("author", ""),
                    "publish_time": a.get("update_time", 0),
                })
        
        if batch_articles:
            historical_articles.extend(batch_articles)
        
        # 检查停止条件
        articles_in_page = len(publish_page.get("publish_list", []))
        if articles_in_page < batch_size:
            # 没有更多文章了
            break
        
        batch_num += 1
        
        # 延迟避免频繁请求
        if len(historical_articles) < target_count:
            await asyncio.sleep(random.uniform(2, 4))
    
    # 截取到目标数量
    historical_articles = historical_articles[:target_count]
    
    # 保存到数据库（去重）
    new_count = rss_store.save_articles(fakeid, historical_articles)
    
    return len(historical_articles), new_count


# ── 回落配置管理 ─────────────────────────────────────────────


class FetchConfigResponse(BaseModel):
    cf_worker_urls: List[str] = Field(default_factory=list)
    proxy_urls: List[str] = Field(default_factory=list)
    active_levels: List[str] = Field(default_factory=list)
    effective_route: str = ""


class UpdateConfigRequest(BaseModel):
    cf_worker_urls: Optional[List[str]] = None
    proxy_urls: Optional[List[str]] = None


@router.get("/fetch-config", summary="获取回落配置")
async def get_fetch_config():
    from utils.fetcher_config import (get_cf_worker_urls, get_proxy_urls,
                                       get_active_levels)
    active = get_active_levels()
    return FetchConfigResponse(
        cf_worker_urls=get_cf_worker_urls(),
        proxy_urls=get_proxy_urls(),
        active_levels=active,
        effective_route=" → ".join(active),
    )


@router.put("/fetch-config", summary="更新回落配置")
async def update_fetch_config(req: UpdateConfigRequest):
    from utils.fetcher_config import (set_cf_worker_urls, set_proxy_urls,
                                       get_active_levels)
    from utils.proxy_pool import proxy_pool

    if req.cf_worker_urls is not None:
        cleaned = list(dict.fromkeys(
            u.strip() for u in req.cf_worker_urls
            if isinstance(u, str) and u.strip() and u.strip().startswith("http")
        ))
        set_cf_worker_urls(cleaned)

    if req.proxy_urls is not None:
        cleaned = list(dict.fromkeys(
            p.strip() for p in req.proxy_urls
            if isinstance(p, str) and p.strip()
        ))
        set_proxy_urls(cleaned)

    proxy_pool.reload()

    active = get_active_levels()
    return {
        "success": True,
        "message": "配置已更新",
        "active_levels": active,
        "effective_route": " → ".join(active),
    }


@router.post("/fetch-config/reset", summary="重置回落配置")
async def reset_fetch_config():
    from utils.fetcher_config import reset_to_env, get_active_levels
    from utils.proxy_pool import proxy_pool

    reset_to_env()
    proxy_pool.reload()

    active = get_active_levels()
    return {
        "success": True,
        "message": "已恢复为 .env 配置",
        "active_levels": active,
        "effective_route": " → ".join(active),
    }


@router.get("/fetch-config/test", summary="测试回落节点")
async def test_fetch_config():
    from utils.cf_worker_client import cf_worker_client
    import time

    results = await cf_worker_client.test_nodes()

    from utils.proxy_pool import proxy_pool
    from utils.http_client import fetch_page
    for proxy in proxy_pool.get_all():
        start = time.monotonic()
        try:
            html = await fetch_page(
                "https://mp.weixin.qq.com/",
                extra_headers={"Referer": "https://mp.weixin.qq.com/"},
                timeout=15,
            )
            latency = (time.monotonic() - start) * 1000
            results.append({
                "level": "L2", "node": proxy, "status": "ok",
                "latency_ms": round(latency, 1),
            })
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            results.append({
                "level": "L2", "node": proxy, "status": "fail",
                "latency_ms": round(latency, 1), "error": str(e)[:100],
            })

    return {"results": results}


# ── 账号管理 ─────────────────────────────────────────────

class AccountItem(BaseModel):
    fakeid: str
    nickname: str
    head_img: str
    alias: str
    login_time: float
    expire_time: int
    is_expired: bool
    is_active: bool


class AccountListResponse(BaseModel):
    success: bool
    data: list = []


@router.get("/accounts", response_model=AccountListResponse,
            summary="获取账号历史列表")
async def list_accounts_endpoint():
    """获取所有登录过的公众号列表（不含 token/cookie）"""
    try:
        from utils.rss_store import list_accounts
        accounts = list_accounts()
        now = int(time.time() * 1000)
        result = []
        for a in accounts:
            et = a.get("expire_time", 0)
            result.append({
                "fakeid": a["fakeid"],
                "nickname": a.get("nickname", ""),
                "head_img": a.get("head_img", ""),
                "alias": a.get("alias", ""),
                "login_time": a.get("login_time", 0),
                "expire_time": et,
                "is_expired": et > 0 and now > et,
                "is_active": bool(a.get("is_active", 0)),
            })
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "data": [], "error": str(e)}


@router.post("/accounts/{fakeid}/activate", summary="切换活跃账号")
async def activate_account_endpoint(fakeid: str):
    """将指定账号设为活跃，其他账号停用"""
    try:
        from utils.rss_store import activate_account, get_account
        account = get_account(fakeid)
        if not account:
            return {"success": False, "error": "账号不存在"}
        activate_account(fakeid)
        auth_manager._load_credentials(force=True)
        return {"success": True, "message": f"已切换到 {account.get('nickname', fakeid)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/accounts/{fakeid}", summary="删除账号记录")
async def delete_account_endpoint(fakeid: str):
    """删除指定账号记录"""
    try:
        from utils.rss_store import delete_account, get_account
        account = get_account(fakeid)
        if not account:
            return {"success": False, "error": "账号不存在"}

        was_active = account.get("is_active", 0)
        delete_account(fakeid)

        if was_active:
            auth_manager._load_credentials(force=True)

        return {"success": True, "message": f"已删除 {account.get('nickname', fakeid)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


class AlertStatusResponse(BaseModel):
    success: bool
    data: dict = {}


@router.get("/alert-status", response_model=AlertStatusResponse,
            summary="告警状态聚合")
async def alert_status():
    """返回凭据和轮询的告警状态"""
    try:
        from utils.rss_store import get_active_account
        from utils.rss_poller import rss_poller

        credential_expired = False
        credential_expiring_soon = False
        credential_nickname = ""
        credential_hours_left = None

        account = get_active_account()
        if account:
            et = account.get("expire_time", 0)
            now = int(time.time() * 1000)
            time_left_sec = (et - now) / 1000

            credential_nickname = account.get("nickname", "")
            if et > 0:
                if time_left_sec <= 0:
                    credential_expired = True
                elif time_left_sec <= 24 * 3600:
                    credential_expiring_soon = True
                    credential_hours_left = round(time_left_sec / 3600, 1)

        poll_failures = getattr(rss_poller, 'consecutive_failures', 0)
        poll_last_fail_time = getattr(rss_poller, 'last_fail_time', None)
        poll_last_fail_msg = getattr(rss_poller, 'last_fail_msg', None)

        return {
            "success": True,
            "data": {
                "credential_expired": credential_expired,
                "credential_expiring_soon": credential_expiring_soon,
                "credential_nickname": credential_nickname,
                "credential_hours_left": credential_hours_left,
                "poll_consecutive_failures": poll_failures,
                "poll_last_fail_time": poll_last_fail_time,
                "poll_last_fail_msg": poll_last_fail_msg,
            }
        }
    except Exception as e:
        return {"success": False, "data": {}, "error": str(e)}
