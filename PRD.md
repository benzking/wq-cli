# PRD：wq-cli 引入 CLI 供 Agent 使用

> **版本**: v1.0
> **日期**: 2026-05-22
> **状态**: 草稿
> **对标项目**: [adennng/wechat-query-skill](https://github.com/adennng/wechat-query-skill) (48⭐)

---

## 目录

1. [背景与动机](#1-背景与动机)
2. [现状分析](#2-现状分析)
3. [目标](#3-目标)
4. [方案设计](#4-方案设计)
5. [CLI 命令定义](#5-cli-命令定义)
6. [技术实现](#6-技术实现)
7. [Agent 集成方案](#7-agent-集成方案)
8. [部署与运维](#8-部署与运维)
9. [实施计划](#9-实施计划)
10. [风险与缓解](#10-风险与缓解)

---

## 1. 背景与动机

### 1.1 为什么要做

当前 Hermes Agent 通过 `~/.hermes/skills/wechat-query/scripts/wechat-query.py`（495 行，stdlib only）与 wq-cli 交互。该脚本虽然在 skill 目录中运行良好，但存在以下问题：

| 问题 | 描述 | 影响 |
|------|------|------|
| **位置不适配** | CLI 脚本在 skill 目录，而非项目仓库内 | 版本管理困难，无法随 wq-cli 同步更新 |
| **无标准入口点** | 只能 `python wechat-query.py`，无 `wq` 命令 | 用户无法直接使用，Agent 依赖完整路径 |
| **权限处理脆弱** | 通过复制 DB 到 `/tmp` 绕开权限问题 | 性能开销，临时文件残留 |
| **登录命令废弃** | 三个 login-* 命令返回 hardcoded 错误提示 | 用户困惑，无实际替代功能 |
| **缺少无人值守模式** | 不支持纯脚本模式（no_agent cron）的标准化输出 | 巡检/推送依赖额外包装脚本 |

### 1.2 对标分析

**wechat-query-skill** 采用 **Agent DSL + CLI 双层架构**：

```
┌──────────────────────────────┐
│       Agent Layer            │
│  SKILL.md (场景编排、预检)    │
│  SCHEDULES.md (cron 模板)    │
├──────────────────────────────┤
│       CLI Layer              │
│  wechat-query.py (stdlib)    │
│  check_service_and_login.sh  │
├──────────────────────────────┤
│       Service Layer          │
│  wechat-download-api         │
│  FastAPI + SQLite + curl_cffi│
└──────────────────────────────┘
```

wq-cli 只有 Service Layer，缺少标准化的 CLI Layer。本次 PRD 的核心目标是在 wq-cli 项目内构建 CLI Layer，并保持与 Agent Layer（SKILL.md）的对接。

---

## 2. 现状分析

### 2.1 wq-cli 项目结构

```
/home/gly/wq-cli/
├── app.py                    # FastAPI 主入口
├── routes/                   # 路由模块 (10个)
│   ├── article.py            # POST /api/article
│   ├── articles.py           # GET /api/public/articles
│   ├── search.py             # GET /api/public/searchbiz
│   ├── account.py            # GET /api/public/accountinfo
│   ├── admin.py              # GET /api/admin/status
│   ├── login.py              # /api/login/*
│   ├── image.py              # GET /api/image
│   ├── rss.py                # /api/rss/*
│   ├── health.py             # GET /api/health
│   └── stats.py              # GET /api/stats
├── utils/                    # 工具模块 (13个)
├── static/                   # 前端页面
├── data/rss.db               # SQLite (WAL模式)
├── start.sh                  # 启动脚本
├── requirements.txt          # 依赖清单
├── CLAUDE.md                 # 架构文档
├── cfwork.js                 # Cloudflare Worker
└── .env                      # 环境配置
```

### 2.2 现有 CLI 能力现状

已有 CLI 脚本位于 `~/.hermes/skills/wechat-query/scripts/wechat-query.py`：

| 命令 | 实现方式 | 状态 |
|------|----------|------|
| `check` | HTTP API → `/api/health` + `/api/admin/status` | ✅ 确认适配新服务 |
| `search` | HTTP API → `/api/public/searchbiz` | ✅ |
| `subscribe` | HTTP API → `POST /api/rss/subscribe` | ✅ |
| `unsubscribe` | HTTP API → `DELETE /api/rss/subscribe/<fakeid>` | ✅ |
| `subscriptions` | HTTP API → `GET /api/rss/subscriptions` | ✅ |
| `poll` | HTTP API → `POST /api/rss/poll` | ✅ |
| `articles` | SQLite 直接查询 | ✅ (有权限自适应) |
| `fetch` | HTTP API → `POST /api/article` | ✅ (端点已适配) |
| `login-start` | 废弃 → 引导手动扫码 | ⚠️ stub |
| `login-qrcode` | 废弃 → 引导手动扫码 | ⚠️ stub |
| `login-status` | 废弃 → 引导手动扫码 | ⚠️ stub |
| `push-report` | SQLite + HTTP API 混合 | ✅ |
| `md-push` | Markdown 格式输出 | ✅ |
| `cron-setup` | 打印注册指引 | ✅ |

### 2.3 关键差异：上游 vs 本地

| 维度 | wechat-query-skill (上游) | wq-cli (本地) |
|------|--------------------------|---------------|
| **登录方式** | 服务端托管二维码（三步 API + 轮询） | 浏览器端扫码（`/login.html`） |
| **文章抓取端点** | `POST /api/article/fetch` | `POST /api/article` |
| **登录状态字段** | `loginState`, `authenticated` | `status`, `authenticated`, `isExpired` |
| **服务部署** | Docker Compose | systemd + start.sh |
| **DB 属主** | 应用进程用户 | `wechat-api:wechat-api` |
| **DB 大小** | ~4.8MB (含历史) | ~57KB (空库) |
| **巡检脚本** | `check_service_and_login.sh` (bash) | Hermes `wechat-inspection.sh` |
| **CLI 位置** | 项目内 `scripts/` | skill 目录 `~/.hermes/skills/...` |

---

## 3. 目标

### 3.1 核心目标

1. **标准化 CLI** — 在 wq-cli 项目内创建标准 CLI，暴露为 `wq` 命令
2. **零外部依赖** — 保持 stdlib only，不引入额外依赖（与上游设计一致）
3. **无缝接入 Agent** — Hermes CLI 模式（`wq <command>`）直接供 Agent 调用
4. **兼容现有 Skill** — 现有 wechat-query Hermes skill 无破坏性变更
5. **无人值守自动化** — 支持 `no_agent` cron 模式的纯脚本输出

### 3.2 非目标

- ❌ 不重写 wq-cli 登录流程（保留浏览器扫码模式）
- ❌ 不引入第三方 CLI 框架（click/typer/rich）
- ❌ 不改变 wq-cli 后端架构（FastAPI 不变）
- ❌ 不做 DB 迁移工具（数据迁移是独立工作项）

---

## 4. 方案设计

### 4.1 整体架构

```
┌─────────────────────────────────────────────┐
│            Agent Layer (Hermes)             │
│  wechat-query  skill  →  wq <command>       │
├─────────────────────────────────────────────┤
│            CLI Layer (新)                    │
│  pyproject.toml → [project.scripts] wq=...  │
│  cli/__init__.py + cli/commands/*.py        │
│  wq check | search | fetch | ...           │
├─────────────────────────────────────────────┤
│         Service Layer (wq-cli 已有)          │
│  FastAPI → routes/*.py → utils/*.py         │
│  SQLite (data/rss.db)                       │
└─────────────────────────────────────────────┘
```

### 4.2 CLI 位置决策

| 方案 | 优势 | 劣势 | 结论 |
|------|------|------|------|
| **A: 放 wq-cli 项目内** | 版本同步、随项目发布 | 需处理 pyproject.toml | ✅ **推荐** |
| B: 保留在 skill 目录 | 零变更 | 版本管理困难 | ❌ |
| C: 独立 repo | 解耦 | 维护成本高 | ❌ |

**结论**：CLI 代码迁入 wq-cli 项目，创建 `cli/` 包。

### 4.3 权限方案 (多级回落)

当前 `/home/gly/wq-cli/` 目录属主为 `wechat-api:wechat-api`，`gly` 用户对 `data/rss.db` 无写权限（读权限可能也有问题）。

**自适应策略**（SQLite 操作时按顺序尝试）：

```
Level 1: 直接读写
  os.access(db_path, R_OK | W_OK) 成功 → 直接打开
  ↓ 失败
Level 2: 只读模式
  os.access(db_path, R_OK) 成功，但 W_OK 失败
  → PRAGMA query_only=ON, temp_store=MEMORY
  ↓ 失败
Level 3: 复制到 /tmp
  shutil.copy2 → 打开副本
  ↓ 失败
Level 4: API 兜底
  通过 HTTP API 替代 SQLite 查询
  (e.g., /api/public/articles 替代直接读 articles 表)
```

**长期方案**：将 `gly` 加入 `wechat-api` 组：

```bash
sudo usermod -aG wechat-api gly
chmod g+rx /home/gly/wq-cli/data/
```

---

## 5. CLI 命令定义

### 5.1 命令全景

| 命令 | 请求方式 | 参数 | 说明 |
|------|----------|------|------|
| **健康与状态** ||||
| `wq check` | HTTP | 无 | 服务健康 + 登录状态检查 |
| `wq status` | HTTP | 无 | login-status 别名（JSON） |
| **公众号操作** ||||
| `wq search <query>` | HTTP | query: str | 搜索公众号 |
| `wq info <fakeid>` | HTTP | fakeid: str | 公众号详情 |
| **订阅管理** ||||
| `wq subscribe <fakeid>` | HTTP | fakeid: str | 添加订阅 |
| `wq unsubscribe <fakeid>` | HTTP | fakeid: str | 取消订阅 |
| `wq subscriptions` | HTTP | 无 | 订阅列表 |
| `wq poll` | HTTP | 无 | 手动触发 RSS 轮询 |
| **文章操作** ||||
| `wq articles [--hours=N] [--keyword=K] [--fakeid=F] [--limit=N]` | SQLite/API | 过滤器 | 查询缓存文章 |
| `wq fetch <url>` | HTTP | url: str | 抓取文章全文 |
| **推送** ||||
| `wq push-report [--hours=N]` | SQLite+HTTP | hours: int | 推送报告 JSON |
| `wq md-push` | SQLite+HTTP | 无 | 推送报告 Markdown |
| **运维** ||||
| `wq cron-setup` | 本地 | 无 | 打印 cron 注册指引 |
| `wq login` | 本地 | 无 | 打开登录页面 URL |
| `wq version` | 本地 | 无 | 显示版本信息 |

> **login-* 系列变更**：废弃上游的 login-start / login-qrcode / login-status（服务端托管模式不兼容），改为：
> - `wq login` → 输出 `http://localhost:5000/login.html` URL
> - 已有 skill 登录引导文案保持兼容

### 5.2 输出规范

所有命令统一 JSON 输出（供 Agent 解析），`md-push` 特例输出 Markdown。

#### 成功输出

```json
{"ok": true, "data": <结果数据>}
```

#### 失败输出

```json
{"ok": false, "error": "错误描述"}
```

#### Exit Code

- `0` — 成功
- `1` — 一般错误（服务不可达、参数错误）
- `2` — 认证失败/登录过期

---

## 6. 技术实现

### 6.1 Python 打包：pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "wq-cli"
version = "0.1.0"
description = "WeChat Article Query CLI — Agent interface for wq-cli service"
requires-python = ">=3.10"

[project.scripts]
wq = "cli:main"
```

### 6.2 包结构

```
wq-cli/
├── cli/
│   ├── __init__.py          # main() 入口 + argparse
│   ├── core.py              # HTTP 请求、DB 连接、输出工具
│   ├── health.py            # check, status
│   ├── subscribe.py         # subscribe, unsubscribe, subscriptions, poll
│   ├── articles.py          # articles, fetch
│   ├── push.py              # push-report, md-push
│   ├── search.py            # search, info
│   └── login.py             # login
├── pyproject.toml           # 打包配置
├── tests/                   # 测试
│   ├── test_health.py
│   ├── test_articles.py
│   └── ...
└── ... (现有 wq-cli 文件不变)
```

### 6.3 核心模块设计

**cli/core.py** — 基础能力层：

```python
# HTTP 请求（urllib.request, stdlib only）
# DB 连接（多级回落权限处理）
# JSON 输出规范化（_ok / _fail）
# 服务预检（_ensure_service）
```

**cli/__init__.py** — 主入口：

| 职责 | 说明 |
|------|------|
| `main()` | `argparse` 分发命令 |
| `WECHAT_API` 环境变量 | 默认 `http://localhost:5000/api` |
| `WECHAT_SERVICE_DIR` 环境变量 | 默认 `/home/gly/wq-cli` |

### 6.4 迁移策略：现有 wechat-query.py → 新 CLI

| 步骤 | 内容 | 影响 |
|------|------|------|
| 1 | 将 wechat-query.py 逻辑拆入 `cli/` 各模块 | 内部重构 |
| 2 | 创建 `pyproject.toml`，定义 `wq` 入口点 | 新增文件 |
| 3 | `pip install -e /home/gly/wq-cli` (开发) | 本地安装 |
| 4 | 更新 skill 中 CLI 调用路径 `wq` | skill 适配 |
| 5 | 单元测试 | 新增 |

**不变的部分**：
- API 端点（全向后兼容）
- JSON 输出格式（`_ok` / `_fail` 保持）
- 环境变量名（`WECHAT_API`, `WECHAT_SERVICE_DIR`）

---

## 7. Agent 集成方案

### 7.1 Hermes Skill 更新

现有 `~/.hermes/skills/wechat-query/skill.md` 中 CLI 调用方式：

```diff
- python ~/.hermes/skills/wechat-query/scripts/wechat-query.py check
+ wq check
```

skill 中的预检、查询、推送等场景无需改变逻辑，只需替换调用路径。

### 7.2 Cron 任务

| 任务 | 时间 | 模式 | 命令 |
|------|------|------|------|
| 服务巡检 | 每日 09:00 | no_agent | `wq check` → 失败时告警 |
| 文章推送 | 每日 18:00 | no_agent | `wq md-push` → Markdown 投递 |

### 7.3 环境变量

提供 Hermes `config.yaml` 级别的配置持久化：

```yaml
# 可选：自定义 API 地址和服务目录
env:
  WECHAT_API: "http://localhost:5000/api"
  WECHAT_SERVICE_DIR: "/home/gly/wq-cli"
```

---

## 8. 部署与运维

### 8.1 安装方式

| 场景 | 命令 | 说明 |
|------|------|------|
| 开发 | `cd /home/gly/wq-cli && pip install -e .` | 符号链接，修改即生效 |
| 部署 | `pip install /home/gly/wq-cli` | 固定版本 |
| 更新 | `git pull && pip install -e .` | 重新安装 |

### 8.2 开发工作流

```bash
# 1. 修改 CLI 代码
vim /home/gly/wq-cli/cli/*.py

# 2. 验证（pip install -e 后直接生效，无需 reinstall）
wq check
wq articles --hours=24

# 3. 提交
cd /home/gly/wq-cli
git commit -m "feat(cli): add articles --keyword filter"
```

### 8.3 测试计划

| 测试类型 | 范围 | 工具 |
|----------|------|------|
| 单元测试 | cli/core.py 工具函数 | pytest |
| 集成测试 | 各命令完整流程 | bash script |
| 权限测试 | DB 读/写/复制回落 | pytest |
| 兼容测试 | 现有 skill 调用不变 | Hermes `wq` 命令 |

---

## 9. 实施计划

### Phase 1：CLI 迁移（1-2 天）

- [ ] 创建 `cli/` 包，拆分 wechat-query.py 逻辑
- [ ] 创建 `pyproject.toml`
- [ ] `pip install -e .` 验证 `wq` 命令可用
- [ ] 保持与现有 json 输出格式 100% 兼容

### Phase 2：Skill 适配（0.5 天）

- [ ] 更新 `~/.hermes/skills/wechat-query/skill.md`
  - CLI 调用路径 `python .../wechat-query.py` → `wq`
- [ ] 清理旧脚本引用（确认无其他 skill 依赖）
- [ ] 验证所有 skill 场景正常

### Phase 3：Cron 重构（0.5 天）

- [ ] 将 `~/.hermes/scripts/wechat-inspection.sh` 改为 `wq check`
- [ ] 将 `~/.hermes/scripts/wechat-daily-push.sh` 改为 `wq md-push`
- [ ] 清理旧包装脚本

### Phase 4：增强（2-3 天，可选）

- [ ] `wq login` 命令：检测过期后自动打开浏览器
- [ ] `wq version` 命令
- [ ] `wq export` 导出文章为 Markdown/PDF
- [ ] `wq stats` 公众号统计概览

---

## 10. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **DB 权限问题复发** | 中 | 高 | 多级回落策略（Level 1-4），每级独立 fallback |
| **login-* 命令用户依赖** | 低 | 中 | 废弃命令返回清晰引导文案，skill 文档更新说明 |
| **pip install -e 冲突** | 低 | 中 | 仅影响当前 venv，无全局影响 |
| **旧 wechat-query.py 残留** | 中 | 低 | 迁移后保留旧脚本作为 fallback，标注 deprecated |
| **多用户环境权限** | 低 | 中 | 推荐 `usermod -aG wechat-api` 方案，非破坏性 |
| **上游 wq-cli 升级** | 低 | 低 | CLI 通过 HTTP API 交互，API 无破坏性变更风险低 |

---

## 附录

### A. 现有 wechat-query.py 函数映射

| 旧函数 | 新模块 | 备注 |
|--------|--------|------|
| `cmd_check` | `health.py` | 保持不变 |
| `cmd_search` | `search.py` | 保持不变 |
| `cmd_subscribe` | `subscribe.py` | 保持不变 |
| `cmd_unsubscribe` | `subscribe.py` | 保持不变 |
| `cmd_subscriptions` | `subscribe.py` | 保持不变 |
| `cmd_poll` | `subscribe.py` | 保持不变 |
| `cmd_articles` | `articles.py` | 保持不变 |
| `cmd_fetch` | `articles.py` | 保持不变 |
| `cmd_login_*` | `login.py` | stub → 引导 URL |
| `cmd_push_report` | `push.py` | 保持不变 |
| `cmd_md_push` | `push.py` | 保持不变 |
| `cmd_cron_setup` | `__init__.py` | 保持不变 |
| `_req` | `core.py` | 提取为公共函数 |
| `_db_conn` | `core.py` | 提取为公共函数 |
| `_ok` / `_fail` | `core.py` | 提取为公共函数 |

### B. 目录属主变更（可选）

```bash
# 将 gly 加入 wechat-api 组（非破坏性，不影响已有服务）
sudo usermod -aG wechat-api gly

# 确保组有读权限
chmod g+rX /home/gly/wq-cli
chmod g+rX /home/gly/wq-cli/data/
# 注意：start.sh 每次启动会 chown 回 wechat-api:wechat-api（第 388 行）
# 因此 chmod 是临时方案，start.sh 启动后组权限会被重置
```

---

> **下一阶段建议**：确认本 PRD 后 → 实施 Phase 1-3 → 编写单元测试 → 删除旧 `wechat-query.py` 脚本
