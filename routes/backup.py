#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
备份管理路由
"""
import logging
import tempfile
import os
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from utils import backup_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class BackupResponse(BaseModel):
    success: bool
    data: dict = {}
    error: Optional[str] = None


@router.get("/admin/backup/list", summary="列出备份文件")
async def list_backups():
    files = backup_manager.list_backup_files()
    return BackupResponse(success=True, data={"backups": files})


@router.post("/admin/backup/export", summary="导出备份")
async def export_backup():
    try:
        path = backup_manager.export_backup()
        filename = path.rsplit("/", 1)[-1]
        return FileResponse(
            path,
            media_type="application/zip",
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ImportRequest(BaseModel):
    path: str
    restore_db: bool = True
    restore_env: bool = True


@router.post("/admin/backup/import", summary="导入备份（路径方式）")
async def import_backup_by_path(req: ImportRequest):
    result = backup_manager.import_backup(
        req.path, restore_db=req.restore_db, restore_env=req.restore_env,
    )
    return result


@router.post("/admin/backup/import/upload", summary="导入备份（文件上传）")
async def import_backup_upload(
    file: UploadFile = File(...),
    restore_db: bool = Form(True),
    restore_env: bool = Form(True),
):
    try:
        suffix = ".zip"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        result = backup_manager.import_backup(tmp_path, restore_db=restore_db, restore_env=restore_env)

        try:
            os.unlink(tmp_path)
        except OSError:
            pass

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/admin/backup/validate", summary="验证备份文件")
async def validate_backup(path: str = Query(..., description="备份文件路径")):
    manifest = backup_manager.validate_backup(path)
    if manifest:
        return BackupResponse(success=True, data={"manifest": manifest, "compatible": True})
    return BackupResponse(success=False, data={"compatible": False},
                          error="无效或不兼容的备份文件")


@router.delete("/admin/backup/delete", summary="删除备份文件")
async def delete_backup(path: str = Query(..., description="备份文件路径")):
    if not path.endswith(".zip") or ".." in path or "/" not in path:
        return {"success": False, "message": "无效的备份文件路径"}
    # 只允许删除 data/ 目录下的备份文件
    allowed_dir = os.path.join(os.getcwd(), "data")
    full_path = os.path.abspath(path)
    if not full_path.startswith(allowed_dir):
        return {"success": False, "message": "路径越权"}
    try:
        os.remove(path)
        return {"success": True, "message": "已删除"}
    except FileNotFoundError:
        return {"success": False, "message": "文件不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}
