# 设计文档：多级回落文章抓取 + 配置管理

> **基于**: [PDR](../pdr-multi-level-fallback-2026-05-21.md)
> **日期**: 2026-05-21
> **状态**: 已批准

---

## 一、架构决策：统一回落调度器

`/api/article` 和 RSS 轮询器共用一个回落入口，避免两套代码各自维护。

```
/article API ─┐
              ├──→ article_fetcher.fetch() → L1→L2→L3 → 返回 HTML
RSS 轮询器  ──┘
```

L1 (CF Worker) 用 httpx（Worker 已解决 IP 问题，不需要 TLS 指纹伪装）；L2/L3 保持 curl_cffi。

---

## 二、回落流程

```
1. 生成 trace_id (8位 hex)
2. L1 启用? → cf_worker_client.fetch_via_cf_worker() → 成功返回 HTML
3. L1 失败  → http_client.fetch_page(url, proxy=..., allow_direct_fallback=False) → 成功返回 HTML
4. L2 失败  → http_client.fetch_page(url, proxy=None) → 成功返回 HTML
5. 全失败  → raise AllLevelsFailedException
```

**面向调用方的接口不变** — `fetch_article_content(url)` 签名与原来一致，返回 HTML 或 None。

---

## 三、CF Worker 调用方式

```
GET {node_url}/?url={encoded_article_url}&preset=mp
```

- `url`: 微信公众号文章 URL（完整地址）
- `preset=mp`: 自动添加 Referer: https://mp.weixin.qq.com
- 成功返回原始 HTML，失败返回纯文本错误 + 400 状态码

CF Worker 不需要额外反爬措施 — Cloudflare edge IP 本身干净，header 伪装对其帮助有限。

### 节点池管理

- 轮转选取
- 单节点连续 3 次失败 → 冷却 120s
- 80% 节点冷却 → 熔断 60s，自动跳过 L1
- 后台每 300s 健康探测

---

## 四、配置管理

### 存储

SQLite 新增 `config` 表 (key/value/updated_at)，get_config/set_config 操作接口。

### 读取优先级

```
SQLite config 表（Web 页面写入）    ← 优先
.env 环境变量（传统配置）           ← 兜底
空值                                ← 对应等级自动跳过
```

启动时自动迁移：SQLite 无配置且 .env 有值 → 写入 SQLite。

### 配置模块接口

```python
# fetcher_config.py
get_cf_worker_urls() -> list[str]
get_proxy_urls() -> list[str]
get_active_levels() -> list[str]       # ["L1","L2","L3"] 或子集
set_cf_worker_urls(urls: list[str])
set_proxy_urls(urls: list[str])
reset_to_env()
```

proxy_pool.py 改为从 fetcher_config 读取代理列表（而非仅读环境变量），支持 Web 页面热增删。

---

## 五、API 端点

### 新增（挂 routes/admin.py）

| 端点 | 方法 | 说明 |
|:------|:------|:-----|
| `/api/admin/fetch-config` | GET | 返回 CF Worker 列表、代理列表、生效链路 |
| `/api/admin/fetch-config` | PUT | 保存新配置，写入 SQLite + hot-reload |
| `/api/admin/fetch-config/reset` | POST | 清空 SQLite 配置，恢复 .env |
| `/api/admin/fetch-config/test` | GET | 逐节点测试速度和可用性 |

### 增强

| 端点 | 新增字段 |
|:------|:-----|
| `/api/health` | `fallback.active_levels`, `fallback.cf_worker` |
| `/api/admin/status` | `effective_route` |

---

## 六、前端页面

`static/proxy-config.html` — 纯 HTML，无框架，与现有 admin.html 风格一致。

功能：两个多行文本框（CF Worker URL / SOCKS5 代理），保存校验，节点测试按钮，生效链路显示，一键恢复 .env。

`static/admin.html` 导航栏添加入口链接。

---

## 七、改动清单

| 文件 | 动作 |
|:------|:-----|
| `utils/fetcher_config.py` | **新增** — 配置读取/写入 |
| `utils/cf_worker_client.py` | **新增** — CF Worker 客户端 + 节点池 |
| `static/proxy-config.html` | **新增** — Web 配置页面 |
| `utils/article_fetcher.py` | **重写** — 回落调度器 L1→L2→L3 + 批量接口 |
| `utils/http_client.py` | **修改** — 加 `allow_direct_fallback` 参数 |
| `utils/rss_store.py` | **修改** — 新增 config 表 + get/set_config |
| `utils/proxy_pool.py` | **修改** — 读 fetcher_config |
| `routes/article.py` | **修改** — 接回落调度器 |
| `routes/admin.py` | **修改** — 4 个 fetch-config 端点 + status 加 effective_route |
| `routes/health.py` | **修改** — 加 fallback 健康状态 |
| `app.py` | **修改** — proxy-config 路由 |
| `utils/webhook.py` | **修改** — 新增 fallback_degraded 事件 |
| `utils/rss_poller.py` | **修改** — 日志带 trace_id |
| `static/admin.html` | **修改** — 导航加入口 |
| `env.example` | **修改** — 新增 CF_WORKER_URLS 注释 |

---

## 八、不纳入此版本

- API 鉴权中间件（后续版本）
- 凭证加密存储（后续版本）
