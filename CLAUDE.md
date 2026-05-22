# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WeChat Download API — a FastAPI service that fetches WeChat Official Account (微信公众号) articles, supports account search, article listing, and generates RSS 2.0 feeds with full article content. Licensed under AGPL-3.0.

## Commands

```bash
# Run locally
python app.py
# Or directly with uvicorn:
uvicorn app:app --host 0.0.0.0 --port 5000

# Install dependencies
pip install -r requirements.txt

# Docker
docker-compose up -d

# Health check
curl http://localhost:5000/api/health
```

There is no test suite, linter config, or Makefile. Testing is manual via the Swagger UI at `/api/docs` or direct HTTP calls.

## Architecture

**Entry point:** `app.py` — creates FastAPI app with a lifespan context manager. On startup: initializes SQLite DB, starts RSS poller, starts login expiry reminder. On shutdown: stops both background tasks.

**Route registration order matters:** `articles.router` must be registered before `search.router` (both under `/api/public`) to avoid route conflicts.

### Routes (`routes/`)

Each file is a self-contained APIRouter module:
- `article.py` — `POST /api/article` (fetch article content by URL)
- `articles.py` — `GET /api/public/articles` (list articles by fakeid), `GET /api/public/articles/search`
- `search.py` — `GET /api/public/searchbiz` (search accounts by name)
- `account.py` — `GET /api/public/accountinfo`
- `login.py` — QR code login flow, verification handling
- `admin.py` — `GET /api/admin/status`, `POST /api/admin/logout`
- `image.py` — `GET /api/image` (image proxy to bypass CDN restrictions)
- `rss.py` — CRUD for RSS subscriptions + XML feed output + manual poll trigger
- `health.py` / `stats.py` — monitoring endpoints

### Utils (`utils/`)

Core business logic, each module is focused:
- `auth_manager.py` — Singleton managing WeChat credentials. Reads from `.env` or `data/.credentials.json` (Docker). Has a 30s read cache to avoid redundant file IO under high RPS.
- `http_client.py` — HTTP client wrapper. Uses `curl_cffi` (Chrome TLS fingerprint emulation) with automatic fallback to `httpx`. Proxy scenarios use synchronous curl_cffi + ThreadPoolExecutor due to SOCKS5 async issues.
- `proxy_pool.py` — SOCKS5 proxy rotation (comma-separated in `PROXY_URLS` env var). Failure → try next proxy → all fail → direct connection fallback.
- `rate_limiter.py` — Multi-tier rate limiting (global, per-IP, per-article intervals)
- `content_processor.py` — Article HTML processing + image URL rewriting for proxy
- `helpers.py` — HTML parsing, article URL extraction from WeChat responses
- `image_proxy.py` — Rewrites image URLs to go through the `/api/image` proxy
- `rss_store.py` — SQLite database operations (WAL mode) for subscriptions and articles
- `rss_poller.py` — Background scheduler that polls subscribed accounts at configurable interval
- `rss_streaming.py` — Streaming RSS XML generation for large feeds
- `article_fetcher.py` — Batch concurrent article fetching with semaphore control
- `login_reminder.py` — Monitors credential expiry, sends webhook notifications
- `webhook.py` — Sends notifications to enterprise WeChat group robots (企业微信群机器人)

### Frontend (`static/`)

Plain HTML pages (no build step, no framework), each is a standalone SPA:
- `admin.html` — Main dashboard
- `login.html` — QR code login
- `rss.html` — RSS subscription management
- `verify.html`, `blacklist.html`, `categories.html`, `history.html`

### Data (`data/`, gitignored)

- `rss.db` — SQLite with WAL mode
- `.credentials.json` — Docker credential persistence

## Key Design Patterns

- **Anti-detection stack:** curl_cffi Chrome TLS fingerprint + SOCKS5 proxy rotation + browser-like headers. This is critical — direct connections to WeChat APIs risk account bans.
- **Credential lifecycle:** Login via QR scan → credentials auto-saved to `.env` or `data/.credentials.json` → ~4 day validity → webhook notification on expiry.
- **Image proxying:** All article images are rewritten to `/api/image?url=...` to bypass WeChat CDN referrer checks. `SITE_URL` env var must be configured correctly for this to work.
- **Singleton pattern:** `AuthManager` uses `__new__` singleton. Other utils are module-level instances.
- **Graceful degradation:** curl_cffi missing → httpx fallback; all proxies fail → direct connection; no `.env` → warning but service still starts.

## Environment Configuration

Copy `env.example` to `.env`. Key variables:
- `WECHAT_TOKEN/COOKIE/FAKEID` — auto-populated after login, don't edit manually
- `PROXY_URLS` — SOCKS5 proxies (strongly recommended when `RSS_FETCH_FULL_CONTENT=true`)
- `SITE_URL` — required for RSS image proxy URLs to work correctly
- `RSS_POLL_INTERVAL` — default 3600s (1 hour)
- `WEBHOOK_URL` — enterprise WeChat robot webhook for login expiry alerts

<!-- superpowers-zh:begin (do not edit between these markers) -->
# Superpowers-ZH 中文增强版

本项目已安装 superpowers-zh 技能框架（20 个 skills）。

## 核心规则

1. **收到任务时，先检查是否有匹配的 skill** — 哪怕只有 1% 的可能性也要检查
2. **设计先于编码** — 收到功能需求时，先用 brainstorming skill 做需求分析
3. **测试先于实现** — 写代码前先写测试（TDD）
4. **验证先于完成** — 声称完成前必须运行验证命令

## 可用 Skills

Skills 位于 `.claude/skills/` 目录，每个 skill 有独立的 `SKILL.md` 文件。

- **brainstorming**: 在任何创造性工作之前必须使用此技能——创建功能、构建组件、添加功能或修改行为。在实现之前先探索用户意图、需求和设计。
- **chinese-code-review**: 中文 review 沟通参考——话术模板、分级标注（必须修复/建议修改/仅供参考）、国内团队常见反模式应对。仅在用户显式 /chinese-code-review 时调用，不要根据上下文自动触发。
- **chinese-commit-conventions**: 中文 commit 与 changelog 配置参考——Conventional Commits 中文适配、commitlint/husky/commitizen 中文模板、conventional-changelog 中文配置。仅在用户显式 /chinese-commit-conventions 时调用，不要根据上下文自动触发。
- **chinese-documentation**: 中文文档排版参考——中英文空格、全半角标点、术语保留、链接格式、中文文案排版指北约定。仅在用户显式 /chinese-documentation 时调用，不要根据上下文自动触发。
- **chinese-git-workflow**: 国内 Git 平台配置参考——Gitee、Coding.net、极狐 GitLab、CNB 的 SSH/HTTPS/凭据/CI 接入差异与镜像同步配置。仅在用户显式 /chinese-git-workflow 时调用，不要根据上下文自动触发。
- **dispatching-parallel-agents**: 当面对 2 个以上可以独立进行、无共享状态或顺序依赖的任务时使用
- **executing-plans**: 当你有一份书面实现计划需要在单独的会话中执行，并设有审查检查点时使用
- **finishing-a-development-branch**: 当实现完成、所有测试通过、需要决定如何集成工作时使用——通过提供合并、PR 或清理等结构化选项来引导开发工作的收尾
- **mcp-builder**: MCP 服务器构建方法论 — 系统化构建生产级 MCP 工具，让 AI 助手连接外部能力
- **receiving-code-review**: 收到代码审查反馈后、实施建议之前使用，尤其当反馈不明确或技术上有疑问时——需要技术严谨性和验证，而非敷衍附和或盲目执行
- **requesting-code-review**: 完成任务、实现重要功能或合并前使用，用于验证工作成果是否符合要求
- **subagent-driven-development**: 当在当前会话中执行包含独立任务的实现计划时使用
- **systematic-debugging**: 遇到任何 bug、测试失败或异常行为时使用，在提出修复方案之前执行
- **test-driven-development**: 在实现任何功能或修复 bug 时使用，在编写实现代码之前
- **using-git-worktrees**: 当需要开始与当前工作区隔离的功能开发或执行实现计划之前使用——创建具有智能目录选择和安全验证的隔离 git 工作树
- **using-superpowers**: 在开始任何对话时使用——确立如何查找和使用技能，要求在任何响应（包括澄清性问题）之前调用 Skill 工具
- **verification-before-completion**: 在宣称工作完成、已修复或测试通过之前使用，在提交或创建 PR 之前——必须运行验证命令并确认输出后才能声称成功；始终用证据支撑断言
- **workflow-runner**: 在 Claude Code / OpenClaw / Cursor 中直接运行 agency-orchestrator YAML 工作流——无需 API key，使用当前会话的 LLM 作为执行引擎。当用户提供 .yaml 工作流文件或要求多角色协作完成任务时触发。
- **writing-plans**: 当你有规格说明或需求用于多步骤任务时使用，在动手写代码之前
- **writing-skills**: 当创建新技能、编辑现有技能或在部署前验证技能是否有效时使用

## 如何使用

当任务匹配某个 skill 时，使用 `Skill` 工具加载对应 skill 并严格遵循其流程。绝不要用 Read 工具读取 SKILL.md 文件。

如果你认为哪怕只有 1% 的可能性某个 skill 适用于你正在做的事情，你必须调用该 skill 检查。
<!-- superpowers-zh:end -->
