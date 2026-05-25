#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 tmwgsicp
# Licensed under the GNU Affero General Public License v3.0
# See LICENSE file in the project root for full license text.
# SPDX-License-Identifier: AGPL-3.0-only
"""
备份导出导入 — 数据库 + 配置 + 版本兼容
"""
import json
import os
import shutil
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv

backup_version = 1

BACKUP_VERSION_KEY = "wq_cli_backup_version"
DB_FILE = "rss.db"
ENV_FILE = ".env"
MANIFEST_FILE = "manifest.json"


def export_backup() -> str:
    """创建备份 zip 文件，返回文件路径"""
    load_dotenv()
    base = Path(__file__).parent.parent
    data_dir = base / "data"
    tmp = tempfile.mkdtemp(prefix="wq_backup_")
    manifest_path = Path(tmp) / MANIFEST_FILE

    try:
        # manifest — 记录版本和时间
        manifest = {
            BACKUP_VERSION_KEY: backup_version,
            "created_at": time.time(),
            "created_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "db_file": DB_FILE,
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        # 复制数据库
        db_src = data_dir / DB_FILE
        if db_src.exists():
            shutil.copy2(db_src, Path(tmp) / DB_FILE)

        # 导出 .env 中的关键配置（脱敏处理：仅保留非 token/cookie 的值）
        env_section = {}
        important_keys = [
            "SITE_URL", "PROXY_URLS", "RSS_POLL_INTERVAL",
            "ARTICLES_PER_POLL", "RSS_FETCH_FULL_CONTENT", "WEBHOOK_URL",
            "RSS_DB_PATH", "CF_WORKER_URLS", "RSS_SINGLE_DEFAULT",
            "RSS_SINGLE_MAX", "RSS_AGGREGATED_DEFAULT", "RSS_AGGREGATED_MAX",
            "RSS_CATEGORY_DEFAULT", "RSS_CATEGORY_MAX", "RSS_HISTORICAL_DEFAULT",
            "RSS_HISTORICAL_MAX",
        ]
        for k in important_keys:
            v = os.getenv(k, "")
            if v:
                env_section[k] = v

        # 凭证类：导出为空占位，导入时若缺失不影响已有配置
        credential_keys = ["WECHAT_TOKEN", "WECHAT_COOKIE", "WECHAT_FAKEID"]
        for k in credential_keys:
            env_section[k] = ""

        with open(Path(tmp) / "env_export.json", "w", encoding="utf-8") as f:
            json.dump(env_section, f, ensure_ascii=False, indent=2)

        # zip 打包
        zip_dir = base / "data"
        zip_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        zip_path = zip_dir / f"wq_backup_{time.strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 1000:03d}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(manifest_path, MANIFEST_FILE)
            if (Path(tmp) / DB_FILE).exists():
                zf.write(Path(tmp) / DB_FILE, DB_FILE)
            env_json = Path(tmp) / "env_export.json"
            if env_json.exists():
                zf.write(env_json, "env_export.json")

        return str(zip_path)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def validate_backup(zip_path: str) -> Optional[Dict]:
    """验证备份文件的版本兼容性，返回 manifest 或 None"""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if MANIFEST_FILE not in zf.namelist():
                return None
            manifest = json.loads(zf.read(MANIFEST_FILE))
            backup_ver = manifest.get(BACKUP_VERSION_KEY, 0)

            # 向前兼容：新版本可以导入旧版本的备份
            if backup_ver > backup_version:
                return None  # 不能导入更新版本的备份

            return manifest
    except Exception:
        return None


def import_backup(zip_path: str, restore_db: bool = True,
                  restore_env: bool = True) -> Dict:
    """导入备份文件，返回结果详情"""
    result = {
        "success": True,
        "db_restored": False,
        "env_restored": False,
        "env_keys_imported": 0,
        "env_keys_skipped": 0,
        "errors": [],
    }

    manifest = validate_backup(zip_path)
    if not manifest:
        return {"success": False, "error": "无效或不兼容的备份文件"}

    base = Path(__file__).parent.parent

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()

            if restore_db and DB_FILE in names:
                data_dir = base / "data"
                data_dir.mkdir(parents=True, exist_ok=True)
                # 备份现有数据库
                existing = data_dir / DB_FILE
                if existing.exists():
                    bak = data_dir / f"rss.db.bak_{int(time.time())}"
                    shutil.copy2(existing, bak)

                # 提取到临时位置再替换
                tmp_db = Path(tempfile.mktemp(suffix=".db"))
                with zf.open(DB_FILE) as zdb, open(tmp_db, "wb") as f:
                    f.write(zdb.read())

                # 验证 SQLite 完整性
                try:
                    vconn = sqlite3.connect(str(tmp_db))
                    vconn.execute("PRAGMA integrity_check").fetchone()
                    vconn.close()
                except Exception as e:
                    result["errors"].append(f"数据库验证失败: {e}")
                    tmp_db.unlink(missing_ok=True)
                    result["success"] = False
                    return result

                shutil.move(str(tmp_db), str(existing))
                result["db_restored"] = True

            if restore_env and "env_export.json" in names:
                env_data = json.loads(zf.read("env_export.json"))
                env_path = base / ENV_FILE

                # 读取现有 .env
                existing_env: Dict[str, str] = {}
                if env_path.exists():
                    for line in env_path.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            existing_env[k.strip()] = v.strip()

                # 合并导入的配置（保护已有凭据、保留备份中不存在的自定义 key）
                for k, v in env_data.items():
                    if not v:
                        # 空值跳过（凭证或未设置项）
                        result["env_keys_skipped"] += 1
                        continue
                    # 保护已有凭据
                    if k in ("WECHAT_TOKEN", "WECHAT_COOKIE", "WECHAT_FAKEID"):
                        if k in existing_env and existing_env[k]:
                            result["env_keys_skipped"] += 1
                            continue
                    existing_env[k] = v
                    result["env_keys_imported"] += 1

                # 写回 .env
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write("# WeChat Download API Environment\n")
                    f.write(f"# Restored from backup {manifest.get('created_iso', '')}\n")
                    for k, v in existing_env.items():
                        f.write(f"{k}={v}\n")

                result["env_restored"] = True

    except Exception as e:
        result["success"] = False
        result["errors"].append(str(e))

    return result


def list_backup_files() -> list:
    base = Path(__file__).parent.parent / "data"
    if not base.exists():
        return []
    files = []
    for f in sorted(base.glob("wq_backup_*.zip"), reverse=True):
        stat = f.stat()
        files.append({
            "name": f.name,
            "path": str(f),
            "size": stat.st_size,
            "size_mb": round(stat.st_size / 1048576, 2),
            "created_at": stat.st_mtime,
            "created_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime)),
        })
    return files
