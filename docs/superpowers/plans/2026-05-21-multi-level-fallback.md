# 多级回落文章抓取 + 配置管理 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 建立 L1(CF Worker) → L2(SOCKS5代理) → L3(直连) 三级回落体系，新增 Web 配置页面管理节点。

**架构：** 统一回落调度器模式 — `/api/article` 和 RSS 轮询器共用一个 `article_fetcher.py`，内部按配置驱动 L1→L2→L3 逐级尝试，任一级成功即返回。

**技术栈：** Python/FastAPI，httpx (CF Worker)，curl_cffi (L2/L3)，SQLite (配置存储)，原生 HTML/CSS/JS (配置页面)。

---

### 任务 1：config 表 + 读写接口

**文件：**
- 修改：`utils/rss_store.py`（在 `init_db()` 末尾追加，文件末尾追加两个函数）

- [ ] **步骤 1：init_db() 中新增 config 表**

在 `init_db()` 函数末尾（`conn.close()` 之前），INSERT 建表语句：

```python
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL DEFAULT '',
            updated_at INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()
```

- [ ] **步骤 2：文件末尾追加 get_config() 和 set_config()**

```python
def get_config(key: str) -> Optional[str]:
    """读取配置值，不存在返回 None"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM config WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_config(key: str, value: str) -> bool:
    """写入配置（upsert），返回是否成功"""
    import time
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO config (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, int(time.time())),
        )
        conn.commit()
        return True
    finally:
        conn.close()
```

- [ ] **步骤 3：验证**

重启服务，检查 SQLite 数据库中新表存在：

```bash
sqlite3 data/rss.db ".schema config"
```

预期输出：包含 `CREATE TABLE config (...)`。

- [ ] **步骤 4：Commit**

```bash
git add utils/rss_store.py
git commit -m "feat: add config table with get/set_config to rss_store"
```

---

### 任务 2：fetcher_config.py 配置读取器

**文件：**
- 创建：`utils/fetcher_config.py`

- [ ] **步骤 1：创建配置模块**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取配置读取器
配置优先级: SQLite config 表 → .env 环境变量 → 空值（对应等级跳过）
启动时自动迁移 .env 到 SQLite（一次性）
"""

import json
import logging
import os
from typing import List

logger = logging.getLogger(__name__)

CF_WORKER_URLS_KEY = "cf_worker_urls"
PROXY_URLS_KEY = "proxy_urls"


def _get_env_list(key: str) -> List[str]:
    raw = os.getenv(key, "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _get_config_list(key: str) -> List[str]:
    from utils.rss_store import get_config
    raw = get_config(key)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [item.strip() for item in data if isinstance(item, str) and item.strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _set_config_list(key: str, items: List[str]):
    from utils.rss_store import set_config
    set_config(key, json.dumps(items, ensure_ascii=False))


def _migrate_if_needed():
    """启动时：如果 SQLite 中无配置但 .env 中有值，自动写入 SQLite"""
    from utils.rss_store import get_config
    cf_sqlite = get_config(CF_WORKER_URLS_KEY)
    proxy_sqlite = get_config(PROXY_URLS_KEY)

    if cf_sqlite is None:
        env_cf = _get_env_list("CF_WORKER_URLS")
        if env_cf:
            _set_config_list(CF_WORKER_URLS_KEY, env_cf)
            logger.info("Migrated CF_WORKER_URLS from .env to SQLite: %d nodes", len(env_cf))

    if proxy_sqlite is None:
        env_proxy = _get_env_list("PROXY_URLS")
        if env_proxy:
            _set_config_list(PROXY_URLS_KEY, env_proxy)
            logger.info("Migrated PROXY_URLS from .env to SQLite: %d proxies", len(env_proxy))


def get_cf_worker_urls() -> List[str]:
    urls = _get_config_list(CF_WORKER_URLS_KEY)
    if not urls:
        urls = _get_env_list("CF_WORKER_URLS")
    return urls


def get_proxy_urls() -> List[str]:
    urls = _get_config_list(PROXY_URLS_KEY)
    if not urls:
        urls = _get_env_list("PROXY_URLS")
    return urls


def get_active_levels() -> List[str]:
    levels = []
    if get_cf_worker_urls():
        levels.append("L1")
    if get_proxy_urls():
        levels.append("L2")
    levels.append("L3")
    return levels


def set_cf_worker_urls(urls: List[str]):
    _set_config_list(CF_WORKER_URLS_KEY, urls)


def set_proxy_urls(urls: List[str]):
    _set_config_list(PROXY_URLS_KEY, urls)


def reset_to_env():
    """清空 SQLite 配置，恢复 .env 默认"""
    from utils.rss_store import set_config
    set_config(CF_WORKER_URLS_KEY, "")
    set_config(PROXY_URLS_KEY, "")
    logger.info("Config reset: cleared SQLite config, falling back to .env")


# 模块加载时执行一次性迁移
_migrate_if_needed()
```

- [ ] **步骤 2：验证**

```bash
python -c "from utils.fetcher_config import get_active_levels; print(get_active_levels())"
```

预期：`.env` 中没有 `CF_WORKER_URLS` 也没有 `PROXY_URLS` 时输出 `['L3']`。

- [ ] **步骤 3：Commit**

```bash
git add utils/fetcher_config.py
git commit -m "feat: add fetcher_config with SQLite-first, .env fallback"
```

---

### 任务 3：proxy_pool.py 改为读 fetcher_config

**文件：**
- 修改：`utils/proxy_pool.py:50-57`（`_load_proxies` 方法）

- [ ] **步骤 1：修改 _load_proxies()**

将第 50-57 行：
```python
    def _load_proxies(self):
        raw = os.getenv("PROXY_URLS", "").strip()
        if not raw:
            logger.info("Proxy pool: no proxies configured (direct connection)")
            return

        self._proxies = [p.strip() for p in raw.split(",") if p.strip()]
        logger.info("Proxy pool: loaded %d proxies", len(self._proxies))
```

改为：
```python
    def _load_proxies(self):
        from utils.fetcher_config import get_proxy_urls
        self._proxies = get_proxy_urls()
        if not self._proxies:
            logger.info("Proxy pool: no proxies configured (direct connection)")
            return
        logger.info("Proxy pool: loaded %d proxies", len(self._proxies))
```

- [ ] **步骤 2：验证**

如果 `.env` 的 `PROXY_URLS` 有值，重启服务后确认代理池加载成功；`/api/health` 返回 `proxy_pool.enabled: true`。

- [ ] **步骤 3：Commit**

```bash
git add utils/proxy_pool.py
git commit -m "feat: proxy_pool reads from fetcher_config instead of raw env"
```

---

### 任务 4：http_client.py 加 allow_direct_fallback 参数

**文件：**
- 修改：`utils/http_client.py:56-86`（`fetch_page` 函数签名 + 逻辑）

- [ ] **步骤 1：修改 fetch_page() 签名和内部逻辑**

第 56-58 行：
```python
async def fetch_page(url: str, extra_headers: Optional[Dict] = None,
                     timeout: int = 30) -> str:
```

改为：
```python
async def fetch_page(url: str, extra_headers: Optional[Dict] = None,
                     timeout: int = 30, allow_direct_fallback: bool = True) -> str:
```

第 70 行的 for 循环之后，直连兜底逻辑（第 85-86 行）：
```python
    logger.info("fetch_page: url=%s proxy=direct (fallback)", url[:80])
    return await _do_fetch(url, headers, timeout, None)
```

改为：
```python
    if allow_direct_fallback:
        logger.info("fetch_page: url=%s proxy=direct (fallback)", url[:80])
        return await _do_fetch(url, headers, timeout, None)
    raise Exception("All proxies failed and direct fallback disabled")
```

- [ ] **步骤 2：验证**

对现有调用方（所有不传 `allow_direct_fallback` 的地方默认 `True`），行为不变。可手动测试 `/api/article` 正常返回。

- [ ] **步骤 3：Commit**

```bash
git add utils/http_client.py
git commit -m "feat: add allow_direct_fallback param to fetch_page"
```

---

### 任务 5：cf_worker_client.py — CF Worker 节点池客户端

**文件：**
- 创建：`utils/cf_worker_client.py`

- [ ] **步骤 1：创建 CF Worker 客户端**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CF Worker 节点池客户端
通过 Cloudflare Worker 代理获取微信公众号文章。
节点轮转、单节点冷却、全层熔断、后台健康探测。
"""

import asyncio
import logging
import time
import threading
from typing import Optional, List, Dict
from urllib.parse import quote

import httpx

from utils.fetcher_config import get_cf_worker_urls

logger = logging.getLogger(__name__)

FAIL_COOLDOWN = 120          # 单节点连续失败冷却时间
CONSECUTIVE_FAIL_THRESHOLD = 3  # 连续失败次数阈值
CIRCUIT_BREAKER_RATIO = 0.8  # 80% 节点冷却 → 熔断
CIRCUIT_BREAKER_DURATION = 60  # 熔断持续时间
HEALTH_CHECK_INTERVAL = 300  # 后台健康探测间隔
L1_TIMEOUT = 15.0            # CF Worker 请求超时


class CFWorkerClient:
    """CF Worker 节点池"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._lock = threading.Lock()
        self._index = 0
        self._fail_counts: Dict[str, int] = {}
        self._fail_until: Dict[str, float] = {}
        self._circuit_breaker_until: float = 0.0
        self._health_task: Optional[asyncio.Task] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._initialized = True

    @property
    def enabled(self) -> bool:
        return len(get_cf_worker_urls()) > 0

    async def start(self):
        """启动后台健康探测"""
        self._http_client = httpx.AsyncClient(
            timeout=L1_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        self._health_task = asyncio.create_task(self._health_check_loop())
        logger.info("CF Worker client started")

    async def stop(self):
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        if self._http_client:
            await self._http_client.aclose()

    def _get_nodes(self) -> List[str]:
        return get_cf_worker_urls()

    def _is_circuit_open(self) -> bool:
        return time.time() < self._circuit_breaker_until

    def _open_circuit(self):
        self._circuit_breaker_until = time.time() + CIRCUIT_BREAKER_DURATION
        logger.warning("CF Worker circuit breaker OPEN for %ds", CIRCUIT_BREAKER_DURATION)

    def _check_circuit(self):
        """检查是否需要开熔断：80% 节点冷却 → 开熔断"""
        nodes = self._get_nodes()
        if not nodes:
            return
        now = time.time()
        cooled = sum(1 for n in nodes if self._fail_until.get(n, 0) > now)
        if cooled / len(nodes) >= CIRCUIT_BREAKER_RATIO:
            self._open_circuit()

    def next_node(self) -> Optional[str]:
        if not self._get_nodes():
            return None
        if self._is_circuit_open():
            return None
        now = time.time()
        with self._lock:
            nodes = self._get_nodes()
            for _ in range(len(nodes)):
                self._index = (self._index + 1) % len(nodes)
                node = nodes[self._index]
                if self._fail_until.get(node, 0) <= now:
                    return node
        return None

    def mark_failed(self, node: str):
        with self._lock:
            self._fail_counts[node] = self._fail_counts.get(node, 0) + 1
            if self._fail_counts[node] >= CONSECUTIVE_FAIL_THRESHOLD:
                self._fail_until[node] = time.time() + FAIL_COOLDOWN
                logger.warning("CF Worker %s cooled for %ds (fail count=%d)",
                             node, FAIL_COOLDOWN, self._fail_counts[node])
        self._check_circuit()

    def mark_ok(self, node: str):
        with self._lock:
            self._fail_counts[node] = 0
            self._fail_until.pop(node, None)

    def get_status(self) -> dict:
        nodes = self._get_nodes()
        now = time.time()
        healthy = []
        cooldown = []
        for n in nodes:
            if self._fail_until.get(n, 0) > now:
                cooldown.append(n)
            else:
                healthy.append(n)
        return {
            "healthy": len(healthy),
            "cooldown": len(cooldown),
            "total": len(nodes),
            "circuit_open": self._is_circuit_open(),
        }

    async def fetch(self, article_url: str) -> Optional[str]:
        """
        通过 CF Worker 代理获取文章内容。
        返回 HTML 字符串，失败返回 None。
        """
        node = self.next_node()
        if not node:
            logger.warning("[L1] No available CF Worker node")
            return None

        # 拼接 CF Worker proxy URL
        node_url = node.rstrip("/")
        encoded_url = quote(article_url, safe="")
        proxy_url = f"{node_url}/?url={encoded_url}&preset=mp"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "Chrome/120.0.0.0 Safari/537.36",
        }

        try:
            if self._http_client is None:
                async with httpx.AsyncClient(timeout=L1_TIMEOUT) as client:
                    resp = await client.get(proxy_url, headers=headers)
            else:
                resp = await self._http_client.get(proxy_url, headers=headers)

            if resp.status_code == 200 and len(resp.text) > 500:
                self.mark_ok(node)
                return resp.text

            logger.warning("[L1] CF Worker returned status=%d len=%d",
                         resp.status_code, len(resp.text))
            self.mark_failed(node)
            return None

        except Exception as e:
            logger.warning("[L1] CF Worker request failed: %s", str(e)[:80])
            self.mark_failed(node)
            return None

    async def _health_check_loop(self):
        """后台每 300s 探测所有节点"""
        while True:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                await self._probe_all()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("Health check error: %s", e)

    async def _probe_all(self):
        """对所有节点发健康探测请求"""
        nodes = self._get_nodes()
        if not nodes:
            return
        logger.info("[L1 Health] Probing %d CF Worker nodes", len(nodes))
        for node in nodes:
            try:
                node_url = node.rstrip("/")
                probe_url = f"{node_url}/?url={quote('https://mp.weixin.qq.com', safe='')}&preset=mp"
                client = self._http_client or httpx.AsyncClient(timeout=10.0)
                resp = await client.get(probe_url)
                if resp.status_code == 200:
                    self.mark_ok(node)
                else:
                    self.mark_failed(node)
            except Exception:
                self.mark_failed(node)

    async def test_nodes(self) -> List[dict]:
        """异步测试所有节点的速度和可用性，返回逐节点结果"""
        import time as time_mod
        nodes = self._get_nodes()
        if not nodes:
            return []

        async def test_one(node: str) -> dict:
            node_url = node.rstrip("/")
            test_url = f"{node_url}/?url={quote('https://mp.weixin.qq.com', safe='')}&preset=mp"
            start = time_mod.monotonic()
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(test_url)
                latency = (time_mod.monotonic() - start) * 1000
                if resp.status_code == 200:
                    return {"level": "L1", "node": node, "status": "ok", "latency_ms": round(latency, 1)}
                return {"level": "L1", "node": node, "status": "fail",
                        "latency_ms": round(latency, 1), "error": f"HTTP {resp.status_code}"}
            except Exception as e:
                latency = (time_mod.monotonic() - start) * 1000
                return {"level": "L1", "node": node, "status": "fail",
                        "latency_ms": round(latency, 1), "error": str(e)[:100]}

        tasks = [test_one(node) for node in nodes]
        return list(await asyncio.gather(*tasks))


cf_worker_client = CFWorkerClient()
```

- [ ] **步骤 2：验证**

```bash
python -c "from utils.cf_worker_client import cf_worker_client; print(vars(cf_worker_client))"
```

确认单例初始化成功，`enabled` 属性根据配置返回 True/False。

- [ ] **步骤 3：Commit**

```bash
git add utils/cf_worker_client.py
git commit -m "feat: add CF Worker client with node pool and health checks"
```

---

### 任务 6：重写 article_fetcher.py 为回落调度器

**文件：**
- 修改：`utils/article_fetcher.py`（完整重写）

- [ ] **步骤 1：重写为三级回落调度器**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章回落获取器 — L1(CF Worker) → L2(SOCKS5代理) → L3(直连) 三级回落
"""

import asyncio
import logging
import secrets
from typing import Optional

logger = logging.getLogger(__name__)

FALLBACK_TOTAL_TIMEOUT = 90  # 全链路总超时


class AllLevelsFailedError(Exception):
    """所有等级均失败"""
    pass


class ArticleFallbackFetcher:
    """统一回落调度器 — 单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _trace_id(self) -> str:
        return secrets.token_hex(4)

    async def fetch(self, article_url: str, timeout: int = 60,
                    wechat_token: Optional[str] = None,
                    wechat_cookie: Optional[str] = None) -> Optional[str]:
        """
        按 L1→L2→L3 逐级尝试获取文章。
        签名与旧 fetch_article_content() 兼容。
        """
        tid = self._trace_id()
        from utils.fetcher_config import get_active_levels
        from utils.http_client import fetch_page

        active = get_active_levels()
        logger.info("[Fetch %s] url=%s levels=%s", tid, article_url[:60], "→".join(active))

        try:
            return await asyncio.wait_for(
                self._do_fetch(article_url, tid, wechat_token, wechat_cookie),
                timeout=FALLBACK_TOTAL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("[Fetch %s] total timeout %ds exceeded", tid, FALLBACK_TOTAL_TIMEOUT)
            return None

    async def _do_fetch(self, article_url: str, tid: str,
                        wechat_token: Optional[str],
                        wechat_cookie: Optional[str]) -> Optional[str]:
        from utils.fetcher_config import get_active_levels
        from utils.http_client import fetch_page

        active = get_active_levels()

        full_url = article_url
        if wechat_token:
            separator = '&' if '?' in article_url else '?'
            full_url = f"{article_url}{separator}token={wechat_token}"

        extra_headers = {"Referer": "https://mp.weixin.qq.com/"}
        if wechat_cookie:
            extra_headers["Cookie"] = wechat_cookie

        # L1: CF Worker
        if "L1" in active:
            logger.info("[Fetch %s] L1 trying CF Worker", tid)
            from utils.cf_worker_client import cf_worker_client
            html = await cf_worker_client.fetch(full_url)
            if html and self._is_valid(html):
                logger.info("[Fetch %s] L1 SUCCESS len=%d", tid, len(html))
                return html
            logger.warning("[Fetch %s] L1 FAILED", tid)
            self._notify_degraded("L1")

        # L2: SOCKS5 代理（禁止直连兜底，直连留给 L3）
        if "L2" in active:
            logger.info("[Fetch %s] L2 trying SOCKS5 proxy", tid)
            try:
                html = await fetch_page(full_url, extra_headers=extra_headers,
                                        timeout=30, allow_direct_fallback=False)
                if html and self._is_valid(html):
                    logger.info("[Fetch %s] L2 SUCCESS len=%d", tid, len(html))
                    return html
            except Exception as e:
                logger.warning("[Fetch %s] L2 error: %s", tid, str(e)[:80])
            logger.warning("[Fetch %s] L2 FAILED", tid)
            self._notify_degraded("L2")

        # L3: curl_cffi 直连（始终可用）
        if "L3" in active:
            logger.info("[Fetch %s] L3 trying direct connection", tid)
            try:
                html = await fetch_page(full_url, extra_headers=extra_headers,
                                        timeout=30, allow_direct_fallback=True)
                if html and self._is_valid(html):
                    logger.info("[Fetch %s] L3 SUCCESS len=%d", tid, len(html))
                    return html
            except Exception as e:
                logger.error("[Fetch %s] L3 error: %s", tid, str(e)[:80])

        logger.error("[Fetch %s] ALL LEVELS FAILED", tid)
        return None

    def _is_valid(self, html: str) -> bool:
        from utils.helpers import has_article_content, is_article_unavailable
        if is_article_unavailable(html):
            return False
        return has_article_content(html)

    def _notify_degraded(self, level: str):
        """异步通知 webhook（不阻塞主流程）"""
        async def _notify():
            try:
                from utils.webhook import webhook
                await webhook.notify("fallback_degraded", {
                    "level": level,
                    "message": f"回落等级 {level} 所有节点不可用，已降级",
                })
            except Exception:
                pass
        asyncio.ensure_future(_notify())


fallback_fetcher = ArticleFallbackFetcher()


# ── 兼容旧接口 ─────────────────────────────────────────────


async def fetch_article_content(
    article_url: str,
    timeout: int = 60,
    wechat_token: Optional[str] = None,
    wechat_cookie: Optional[str] = None
) -> Optional[str]:
    """兼容旧的 fetch_article_content() 接口"""
    return await fallback_fetcher.fetch(article_url, timeout, wechat_token, wechat_cookie)


async def fetch_articles_batch(
    article_urls: list,
    max_concurrency: int = 5,
    timeout: int = 60,
    wechat_token: Optional[str] = None,
    wechat_cookie: Optional[str] = None
) -> dict:
    """批量获取文章内容（并发版），兼容旧接口"""
    semaphore = asyncio.Semaphore(max_concurrency)
    results = {}

    async def fetch_one(url):
        async with semaphore:
            html = await fallback_fetcher.fetch(url, timeout, wechat_token, wechat_cookie)
            results[url] = html
            await asyncio.sleep(1)

    logger.info("[Batch] 开始批量获取 %d 篇文章", len(article_urls))
    await asyncio.gather(*[fetch_one(url) for url in article_urls], return_exceptions=True)

    success_count = sum(1 for html in results.values() if html)
    logger.info("[Batch] 完成: 成功=%d, 失败=%d", success_count, len(results) - success_count)
    return results
```

- [ ] **步骤 2：验证**

重启服务，通过 Swagger UI 调用 `POST /api/article` 确认文章获取正常（当前没有 CF Worker 和代理时，应该走 L3 直连）。

- [ ] **步骤 3：Commit**

```bash
git add utils/article_fetcher.py
git commit -m "feat: rewrite article_fetcher as L1→L2→L3 fallback orchestrator"
```

---

### 任务 7：routes/article.py 接入回落调度器

**文件：**
- 修改：`routes/article.py:76-80`

- [ ] **步骤 1：替换 fetch_page 调用**

当前第 22 行导入：
```python
from utils.http_client import fetch_page
```
保持不变（其他地方可能还有引用）。

第 76-80 行：
```python
        html = await fetch_page(
            article_request.url,
            extra_headers={"Referer": "https://mp.weixin.qq.com/"},
            timeout=120
        )
```

改为：
```python
        from utils.article_fetcher import fallback_fetcher

        html = await fallback_fetcher.fetch(article_request.url, timeout=60)
```

- [ ] **步骤 2：验证**

重启服务，调用 `POST /api/article` 传入有效微信公众号文章 URL，确认返回正常。

- [ ] **步骤 3：Commit**

```bash
git add routes/article.py
git commit -m "feat: wire /api/article to fallback fetcher"
```

---

### 任务 8：routes/health.py 增强

**文件：**
- 修改：`routes/health.py`

- [ ] **步骤 1：加 fallback 健康状态**

将当前 `health_check()` 函数体替换为：

```python
@router.get("/health", summary="健康检查")
async def health_check():
    from utils.http_client import ENGINE_NAME
    from utils.proxy_pool import proxy_pool
    from utils.fetcher_config import get_active_levels
    from utils.cf_worker_client import cf_worker_client

    return {
        "status": "healthy",
        "version": "1.0.0",
        "framework": "FastAPI",
        "http_engine": ENGINE_NAME,
        "proxy_pool": proxy_pool.get_status(),
        "fallback": {
            "active_levels": get_active_levels(),
            "cf_worker": cf_worker_client.get_status(),
        },
    }
```

- [ ] **步骤 2：验证**

```bash
curl http://localhost:5000/api/health | python -m json.tool
```

预期输出包含 `fallback` 字段。

- [ ] **步骤 3：Commit**

```bash
git add routes/health.py
git commit -m "feat: add fallback health status to /api/health"
```

---

### 任务 9：routes/admin.py 新增 fetch-config 端点 + effective_route

**文件：**
- 修改：`routes/admin.py`（在现有路由末尾追加）

- [ ] **步骤 1：追加 GetConfigRequest/TestResult 模型 + 4 个端点**

文件末尾追加：

```python
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
        # 格式校验 + 去重
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

    # 热重载代理池
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

    # L2 代理测试
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


# ── 增强 /api/admin/status ────────────────────────────────────

# effective_route 加到现有 get_status() 响应中
# 修改 get_status() 函数追加 effective_route 字段:
```

- [ ] **步骤 2：StatusResponse 加 effective_route 字段**

在 `StatusResponse` 模型（第 24-33 行）中追加字段：

```python
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
    effective_route: Optional[str] = ""      # 新增
```

- [ ] **步骤 3：修改 get_status() 加 effective_route**

将：

```python
@router.get("/status", response_model=StatusResponse, summary="获取登录状态")
async def get_status():
    """获取当前登录状态"""
    return auth_manager.get_status()
```

改为：

```python
@router.get("/status", response_model=StatusResponse, summary="获取登录状态")
async def get_status():
    """获取当前登录状态"""
    from utils.fetcher_config import get_active_levels
    result = auth_manager.get_status()
    result["effective_route"] = " → ".join(get_active_levels())
    return result
```

- [ ] **步骤 3：验证**

```bash
curl http://localhost:5000/api/admin/fetch-config | python -m json.tool
curl -X PUT http://localhost:5000/api/admin/fetch-config \
  -H "Content-Type: application/json" \
  -d '{"cf_worker_urls": ["https://example.worker.dev"]}'
curl http://localhost:5000/api/admin/status | python -m json.tool
```

- [ ] **步骤 4：Commit**

```bash
git add routes/admin.py
git commit -m "feat: add fetch-config CRUD endpoints and effective_route to /admin/status"
```

---

### 任务 10：utils/webhook.py 新增 fallback_degraded 事件

**文件：**
- 修改：`utils/webhook.py:21-28`（`EVENT_LABELS` 字典）

- [ ] **步骤 1：添加新事件类型**

在 `EVENT_LABELS` 字典中新增一项：

```python
EVENT_LABELS = {
    "login_success": "登录成功",
    "login_expired": "登录过期",
    "login_expiring_soon": "登录即将过期",
    "login_expiring_critical": "登录即将过期（紧急）",
    "verification_required": "触发验证",
    "content_fetch_failed": "文章内容获取失败",
    "fallback_degraded": "回落降级",
}
```

- [ ] **步骤 2：Commit**

```bash
git add utils/webhook.py
git commit -m "feat: add fallback_degraded webhook event"
```

---

### 任务 11：app.py 增强 — proxy-config 路由 + CF Worker 生命周期

**文件：**
- 修改：`app.py`

- [ ] **步骤 1：lifespan 中启动/停止 CF Worker 客户端**

在 `lifespan()` 函数中，`init_db()` 之后：

```python
    init_db()
    await rss_poller.start()

    # 启动 CF Worker 客户端
    from utils.cf_worker_client import cf_worker_client
    await cf_worker_client.start()

    from utils.login_reminder import login_reminder
    await login_reminder.start()

    yield

    await login_reminder.stop()
    await cf_worker_client.stop()
    await rss_poller.stop()
```

- [ ] **步骤 2：添加 proxy-config.html 路由**

在 `history.html` 路由之后追加：

```python
@app.get("/proxy-config.html", include_in_schema=False)
async def proxy_config_page():
    """回落节点配置页面"""
    return FileResponse(static_dir / "proxy-config.html")
```

- [ ] **步骤 3：验证**

重启服务，访问 `http://localhost:5000/proxy-config.html` 应返回 404（页面文件还不存在，任务 13 创建后才会正常）。

- [ ] **步骤 4：Commit**

```bash
git add app.py
git commit -m "feat: add proxy-config route and CF Worker client lifecycle"
```

---

### 任务 12：utils/rss_poller.py 日志加 trace_id

**文件：**
- 修改：`utils/rss_poller.py` — `_enrich_articles_content()` 方法

- [ ] **步骤 1：生成 trace_id 并注入日志**

`_enrich_articles_content()` 方法（第 244 行）开头添加 trace_id 生成：

第 256-259 行之间，在调用 `fetch_articles_batch` 之前插入：

```python
        import secrets
        tid = secrets.token_hex(4)
        logger.info("[Poll %s] fetching full content for %d articles", tid, len(article_links))
```

然后批量获取日志中带这个 tid（调用的 `fetch_articles_batch` 已经内部日志会带 trace_id，所以 poller 自己不需要在多处带）。

- [ ] **步骤 2：Commit**

```bash
git add utils/rss_poller.py
git commit -m "feat: add trace_id to RSS poller full-content fetch logs"
```

---

### 任务 13：static/proxy-config.html — Web 配置页面

**文件：**
- 创建：`static/proxy-config.html`

- [ ] **步骤 1：创建纯 HTML 配置管理页面**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>节点配置 — WeChat Download API</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; }
  .header { background: #1a1a2e; color: #fff; padding: 16px 24px; display: flex; align-items: center; gap: 24px; }
  .header h1 { font-size: 18px; }
  .header a { color: #a0a0c0; text-decoration: none; font-size: 14px; }
  .header a:hover { color: #fff; }
  .container { max-width: 900px; margin: 24px auto; padding: 0 16px; }
  .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 24px; margin-bottom: 20px; }
  .card h2 { font-size: 16px; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
  .badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; color: #fff; }
  .badge-l1 { background: #4caf50; }
  .badge-l2 { background: #ff9800; }
  .badge-l3 { background: #2196f3; }
  label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: #666; }
  textarea { width: 100%; min-height: 100px; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; font-family: monospace; resize: vertical; }
  .hint { font-size: 12px; color: #999; margin-top: 4px; }
  .route-banner { background: #e8f5e9; border-radius: 6px; padding: 12px 16px; font-size: 14px; margin-bottom: 20px; display: flex; align-items: center; gap: 12px; }
  .route-arrow { color: #666; }
  .btn { padding: 8px 16px; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; font-weight: 600; }
  .btn-primary { background: #1a73e8; color: #fff; }
  .btn-primary:hover { background: #1557b0; }
  .btn-outline { background: #fff; color: #1a73e8; border: 1px solid #1a73e8; }
  .btn-outline:hover { background: #e8f0fe; }
  .btn-danger { background: #fff; color: #d93025; border: 1px solid #d93025; }
  .btn-danger:hover { background: #fce8e6; }
  .btn-group { display: flex; gap: 8px; margin-top: 12px; }
  .result { margin-top: 12px; padding: 10px; border-radius: 6px; font-size: 13px; }
  .result-ok { background: #e8f5e9; color: #2e7d32; }
  .result-err { background: #ffebee; color: #c62828; }
  .test-table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }
  .test-table th { text-align: left; padding: 8px; background: #f5f5f5; border-bottom: 2px solid #ddd; }
  .test-table td { padding: 8px; border-bottom: 1px solid #eee; }
  .status-ok { color: #2e7d32; font-weight: 600; }
  .status-fail { color: #c62828; font-weight: 600; }
  .source-tag { font-size: 11px; padding: 1px 6px; border-radius: 3px; background: #e3f2fd; color: #1565c0; }
</style>
</head>
<body>
<div class="header">
  <h1>WeChat Download API</h1>
  <a href="/admin.html">管理</a>
  <a href="/rss.html">RSS</a>
  <a href="/proxy-config.html" style="color:#fff;font-weight:600;">节点配置</a>
  <a href="/blacklist.html">黑名单</a>
  <a href="/categories.html">分类</a>
  <a href="/history.html">历史文章</a>
</div>

<div class="container">
  <div class="route-banner" id="routeBanner">
    <strong>当前回落链路：</strong><span id="effectiveRoute">加载中...</span>
    <span style="margin-left:auto;font-size:12px;color:#999;" id="configSource"></span>
  </div>

  <!-- L1: CF Worker -->
  <div class="card">
    <h2><span class="badge badge-l1">L1</span> CF Worker 节点</h2>
    <p style="font-size:13px;color:#999;margin-bottom:12px;">每行一个 Worker URL，如 <code>https://00.worker-proxy.asia</code></p>
    <textarea id="cfWorkerUrls" placeholder="https://your-worker.dev&#10;https://another-worker.dev"></textarea>
    <div class="hint">留空则跳过 L1，直接进入 L2</div>
    <div class="btn-group">
      <button class="btn btn-primary" onclick="saveConfig()">保存配置</button>
      <button class="btn btn-outline" onclick="testNodes()">测试节点</button>
      <button class="btn btn-danger" onclick="resetConfig()">恢复 .env 默认</button>
    </div>
  </div>

  <!-- L2: SOCKS5 -->
  <div class="card">
    <h2><span class="badge badge-l2">L2</span> SOCKS5 代理</h2>
    <p style="font-size:13px;color:#999;margin-bottom:12px;">每行一个代理地址</p>
    <textarea id="proxyUrls" placeholder="socks5://ip1:1080&#10;socks5://user:pass@ip2:1080"></textarea>
    <div class="hint">留空则跳过 L2，直接进入 L3</div>
  </div>

  <!-- L3: 始终可用 -->
  <div class="card">
    <h2><span class="badge badge-l3">L3</span> 直连（兜底）</h2>
    <p style="font-size:13px;color:#999;">始终启用，无需配置</p>
  </div>

  <!-- Test Results -->
  <div class="card" id="testCard" style="display:none;">
    <h2>节点测试结果</h2>
    <table class="test-table" id="testResults"><tbody></tbody></table>
  </div>

  <div id="msgBox"></div>
</div>

<script>
const API = '/api/admin/fetch-config';

async function loadConfig() {
  try {
    const resp = await fetch(API);
    const data = await resp.json();
    document.getElementById('cfWorkerUrls').value = (data.cf_worker_urls || []).join('\n');
    document.getElementById('proxyUrls').value = (data.proxy_urls || []).join('\n');
    document.getElementById('effectiveRoute').textContent = data.effective_route || '—';
  } catch(e) {
    showMsg('加载配置失败: ' + e.message, false);
  }
}

async function saveConfig() {
  const cfUrls = document.getElementById('cfWorkerUrls').value
    .split('\n').map(s => s.trim()).filter(s => s);
  const proxyUrls = document.getElementById('proxyUrls').value
    .split('\n').map(s => s.trim()).filter(s => s);

  try {
    const resp = await fetch(API, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({cf_worker_urls: cfUrls, proxy_urls: proxyUrls}),
    });
    const data = await resp.json();
    if (data.success) {
      document.getElementById('effectiveRoute').textContent = data.effective_route || '—';
      showMsg('配置已保存: ' + data.effective_route, true);
    } else {
      showMsg('保存失败', false);
    }
  } catch(e) {
    showMsg('保存失败: ' + e.message, false);
  }
}

async function testNodes() {
  const card = document.getElementById('testCard');
  const tbody = document.getElementById('testResults').querySelector('tbody');
  card.style.display = 'block';
  tbody.innerHTML = '<tr><td colspan="4">测试中...</td></tr>';

  try {
    const resp = await fetch(API + '/test');
    const data = await resp.json();
    tbody.innerHTML = '';
    if (!data.results || data.results.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4">没有配置任何节点</td></tr>';
      return;
    }
    data.results.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML =
        `<td><span class="badge badge-${r.level.toLowerCase()}">${r.level}</span></td>
         <td>${r.node}</td>
         <td class="${r.status === 'ok' ? 'status-ok' : 'status-fail'}">${r.status === 'ok' ? 'OK' : 'FAIL'}</td>
         <td>${r.latency_ms != null ? r.latency_ms + ' ms' : '—'}</td>
         <td style="font-size:12px;color:#999;">${r.error || ''}</td>`;
      tbody.appendChild(tr);
    });
  } catch(e) {
    tbody.innerHTML = '<tr><td colspan="4">测试失败: ' + e.message + '</td></tr>';
  }
}

async function resetConfig() {
  if (!confirm('确认恢复为 .env 文件中的默认配置？这将清空 Web 页面配置。')) return;
  try {
    const resp = await fetch(API + '/reset', {method: 'POST'});
    const data = await resp.json();
    document.getElementById('effectiveRoute').textContent = data.effective_route || '—';
    await loadConfig();
    showMsg('已恢复 .env 默认配置: ' + data.effective_route, true);
  } catch(e) {
    showMsg('重置失败: ' + e.message, false);
  }
}

function showMsg(msg, ok) {
  const box = document.getElementById('msgBox');
  box.innerHTML = `<div class="result ${ok ? 'result-ok' : 'result-err'}">${msg}</div>`;
  setTimeout(() => box.innerHTML = '', 5000);
}

loadConfig();
</script>
</body>
</html>
```

- [ ] **步骤 2：验证**

访问 `http://localhost:5000/proxy-config.html`，确认页面加载、配置显示正常。

- [ ] **步骤 3：Commit**

```bash
git add static/proxy-config.html
git commit -m "feat: add proxy config web UI page"
```

---

### 任务 14：static/admin.html 导航加节点配置入口

**文件：**
- 修改：`static/admin.html`

- [ ] **步骤 1：导航栏加链接**

在 `admin.html` 第 591 行（`<a href="/history.html">` 管理工具区）之后插入同级导航链接：

```html
                    <li><a href="/proxy-config.html"><span>⚙️ 节点配置</span><span class="arrow">&#8250;</span></a></li>
```

- [ ] **步骤 2：Commit**

```bash
git add static/admin.html
git commit -m "feat: add proxy-config nav link to admin page"
```

---

### 任务 15：env.example 新增 CF_WORKER_URLS 注释

**文件：**
- 修改：`env.example`

- [ ] **步骤 1：在 PROXY_URLS 后面新增加说明**

在 `PROXY_URLS=` 空行之后、`# 服务配置` 之前插入：

```
# Cloudflare Worker 代理节点（L1 回落，优先于 SOCKS5 代理）
# 用途：利用 CF 全球 CDN 网络作为文章获取通道，抗微信 IP 封控
# 兼容 wechat-article-exporter 的公共节点和自建私有节点
# 多个节点用逗号分隔，留空则跳过 L1
# 示例: https://00.worker-proxy.asia,https://01.worker-proxy.asia
CF_WORKER_URLS=
```

- [ ] **步骤 2：Commit**

```bash
git add env.example
git commit -m "docs: add CF_WORKER_URLS to env.example"
```

---

### 任务 16：端到端验证

- [ ] **步骤 1：无 CF Worker/代理时走 L3**

```bash
curl -X POST http://localhost:5000/api/article \
  -H "Content-Type: application/json" \
  -d '{"url": "https://mp.weixin.qq.com/s/xxxxx"}'
```

确认返回文章内容，日志显示 `[Fetch xxx] levels=L3` 和 `L3 SUCCESS`。

- [ ] **步骤 2：Web 页面添加 CF Worker 节点测试**

访问 `http://localhost:5000/proxy-config.html`，添加一个 CF Worker URL，保存，确认 `effective_route` 从 `L3` 变为 `L1 → L3`。

- [ ] **步骤 3：health 端点验证**

```bash
curl http://localhost:5000/api/health | python -m json.tool
```

确认 `fallback.active_levels` 和 `fallback.cf_worker` 字段存在且值正确。

- [ ] **步骤 4：/api/admin/status 验证**

```bash
curl http://localhost:5000/api/admin/status | python -m json.tool
```

确认 `effective_route` 字段存在。

- [ ] **步骤 5：Commit**

```bash
git commit --allow-empty -m "test: end-to-end verification of multi-level fallback"
```
