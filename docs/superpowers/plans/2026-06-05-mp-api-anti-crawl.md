# 文章列表扫描反爬加固 — 实现计划

> **面向 AI 代理的工作者：** 使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法跟踪进度。

**目标：** 将微信管理后台 API（`appmsgpublish`）的 3 个调用点统一升级为 curl_cffi TLS 伪装 + 随机 UA + 可选代理 + 结构化错误分类。

**架构：** 新增 `utils/user_agent.py`（UA 生成器）和 `utils/mp_api_client.py`（管理后台 API 客户端），改造 `utils/http_client.py` 的 headers 从静态变为动态，重写 `utils/rss_poller.py` 的 `_fetch_article_list` 接入新客户端，`routes/articles.py` 和 `routes/admin.py` 同步切换。

**技术栈：** Python 3, curl_cffi, httpx, pytest, unittest.mock

---

## 文件结构

| 文件 | 职责 | 状态 |
|------|------|------|
| `utils/user_agent.py` | UA 生成器（按市场份额权重 × 动态版本 × 真实 OS 变体） | 新增 |
| `tests/test_user_agent.py` | UA 生成器单元测试 | 新增 |
| `utils/mp_api_client.py` | `MpApiResult` + `fetch_mp_api()` + 错误分类 | 新增 |
| `tests/test_mp_api_client.py` | mp_api_client 单元测试 | 新增 |
| `utils/http_client.py` | `BROWSER_HEADERS` → `build_headers()` | 改造 |
| `utils/rss_poller.py` | `TokenExpiredError` + 重写 `_fetch_article_list` + `_poll_all` 增强 | 改造 |
| `routes/articles.py` | 裸 httpx → `fetch_mp_api` | 改造 |
| `routes/admin.py` | 裸 httpx → `fetch_mp_api` | 改造 |

---

### 任务 1：新增 `utils/user_agent.py` — UA 生成器

**文件：**
- 创建：`utils/user_agent.py`

- [ ] **步骤 1：创建 `utils/user_agent.py`**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User-Agent 生成器
按市场份额权重分配浏览器类型，动态版本号，真实 OS 变体。
移植自 we-mp-rss (driver/user_agent.py)。
"""
import random

__all__ = ["random_ua", "UserAgentGenerator"]


class UserAgentGenerator:
    """生成符合真实市场分布的 User-Agent 字符串"""

    def __init__(self):
        self.mobile_browser_weights = {
            'chrome': 0.45, 'safari': 0.30, 'firefox': 0.10,
            'edge': 0.08, 'opera': 0.05, 'qq': 0.02,
        }
        self.desktop_browser_weights = {
            'chrome': 0.65, 'edge': 0.12, 'firefox': 0.08,
            'safari': 0.08, 'opera': 0.05, 'qq': 0.02,
        }

    def get_realistic_user_agent(self, mobile_mode: bool = False) -> str:
        if mobile_mode:
            return self._generate_mobile_ua()
        return self._generate_desktop_ua()

    def _generate_mobile_ua(self) -> str:
        browser_type = random.choices(
            list(self.mobile_browser_weights.keys()),
            weights=list(self.mobile_browser_weights.values()),
        )[0]
        return {
            'chrome': self._generate_chrome_mobile_ua,
            'safari': self._generate_safari_mobile_ua,
            'firefox': self._generate_firefox_mobile_ua,
            'edge': self._generate_edge_mobile_ua,
            'opera': self._generate_opera_mobile_ua,
            'qq': self._generate_qq_mobile_ua,
        }[browser_type]()

    def _generate_desktop_ua(self) -> str:
        browser_type = random.choices(
            list(self.desktop_browser_weights.keys()),
            weights=list(self.desktop_browser_weights.values()),
        )[0]
        return {
            'chrome': self._generate_chrome_desktop_ua,
            'edge': self._generate_edge_desktop_ua,
            'firefox': self._generate_firefox_desktop_ua,
            'safari': self._generate_safari_desktop_ua,
            'opera': self._generate_opera_desktop_ua,
            'qq': self._generate_qq_desktop_ua,
        }[browser_type]()

    # ========== 版本号 ==========

    def _get_chrome_version(self) -> str:
        return f"{random.randint(110, 125)}.{random.randint(0, 9)}.{random.randint(4000, 6500)}.{random.randint(0, 200)}"

    def _get_firefox_version(self) -> str:
        return str(random.randint(110, 125))

    def _get_safari_version(self) -> str:
        return f"{random.randint(15, 17)}.{random.randint(0, 6)}"

    def _get_edge_version(self) -> str:
        return f"{random.randint(110, 125)}.{random.randint(0, 9)}.{random.randint(1000, 2500)}.{random.randint(0, 100)}"

    def _get_opera_version(self) -> str:
        major = random.randint(90, 110)
        return f"{major}.{random.randint(0, 9)}.{random.randint(4000, 5500)}.{major - 13}"

    # ========== OS 版本 ==========

    def _get_android_version(self) -> str:
        return random.choices(
            ['10', '11', '12', '13', '14'],
            weights=[0.15, 0.20, 0.30, 0.25, 0.10]
        )[0]

    def _get_ios_version(self) -> str:
        return random.choices(
            ['15_0', '15_5', '16_0', '16_5', '17_0', '17_2', '17_4'],
            weights=[0.10, 0.15, 0.15, 0.20, 0.20, 0.15, 0.05]
        )[0]

    def _get_windows_version(self) -> str:
        versions = [
            ('Windows NT 10.0; Win64; x64', 0.70),
            ('Windows NT 10.0; WOW64', 0.15),
            ('Windows NT 6.3; Win64; x64', 0.08),
            ('Windows NT 6.1; Win64; x64', 0.05),
            ('Windows NT 11.0; Win64; x64', 0.02),
        ]
        return random.choices([v[0] for v in versions], weights=[v[1] for v in versions])[0]

    def _get_macos_version(self) -> str:
        versions = [
            ('10_15_7', 0.25), ('11_0', 0.15), ('12_0', 0.20),
            ('13_0', 0.25), ('14_0', 0.15),
        ]
        return random.choices([v[0] for v in versions], weights=[v[1] for v in versions])[0]

    def _get_linux_distro(self) -> str:
        return random.choice([
            'X11; Linux x86_64', 'X11; Ubuntu; Linux x86_64',
            'X11; Fedora; Linux x86_64', 'X11; Arch Linux; Linux x86_64',
        ])

    # ========== 设备型号 ==========

    def _get_android_device(self) -> str:
        return random.choice([
            'SM-G991B', 'SM-G998B', 'SM-S908B', 'SM-S918B',
            'Mi 10', 'Mi 11', 'Mi 12', 'Mi 13',
            'ELE-AL00', 'ANA-AL00',
            'OPPO A5', 'OPPO Reno6', 'Vivo X70', 'Vivo X80',
            'Pixel 5', 'Pixel 6', 'Pixel 7', 'Pixel 8',
            'OnePlus 8', 'OnePlus 9', 'OnePlus 10 Pro',
        ])

    # ========== 桌面端 UA ==========

    def _generate_chrome_desktop_ua(self) -> str:
        chrome_ver = self._get_chrome_version()
        os_str = random.choices(
            [self._get_windows_version(),
             f"Macintosh; Intel Mac OS X {self._get_macos_version()}",
             self._get_linux_distro()],
            weights=[0.75, 0.15, 0.10],
        )[0]
        return f"Mozilla/5.0 ({os_str}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"

    def _generate_edge_desktop_ua(self) -> str:
        edge_ver = self._get_edge_version()
        chrome_ver = self._get_chrome_version()
        return f"Mozilla/5.0 ({self._get_windows_version()}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 Edg/{edge_ver}"

    def _generate_firefox_desktop_ua(self) -> str:
        firefox_ver = self._get_firefox_version()
        os_str = random.choices(
            [self._get_windows_version(),
             f"Macintosh; Intel Mac OS X {self._get_macos_version()}",
             self._get_linux_distro()],
            weights=[0.60, 0.25, 0.15],
        )[0]
        return f"Mozilla/5.0 ({os_str}; rv:{firefox_ver}.0) Gecko/20100101 Firefox/{firefox_ver}.0"

    def _generate_safari_desktop_ua(self) -> str:
        return f"Mozilla/5.0 (Macintosh; Intel Mac OS X {self._get_macos_version()}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{self._get_safari_version()} Safari/605.1.15"

    def _generate_opera_desktop_ua(self) -> str:
        opera_ver = self._get_opera_version()
        chrome_ver = self._get_chrome_version()
        os_str = random.choices(
            [self._get_windows_version(),
             f"Macintosh; Intel Mac OS X {self._get_macos_version()}",
             self._get_linux_distro()],
            weights=[0.70, 0.20, 0.10],
        )[0]
        return f"Mozilla/5.0 ({os_str}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 OPR/{opera_ver}"

    def _generate_qq_desktop_ua(self) -> str:
        chrome_ver = self._get_chrome_version()
        qq_ver = f"{random.randint(13, 15)}.{random.randint(0, 5)}.{random.randint(5000, 5500)}"
        return f"Mozilla/5.0 ({self._get_windows_version()}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 QQBrowser/{qq_ver}"

    # ========== 移动端 UA ==========

    def _generate_chrome_mobile_ua(self) -> str:
        return f"Mozilla/5.0 (Linux; Android {self._get_android_version()}; {self._get_android_device()}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self._get_chrome_version()} Mobile Safari/537.36"

    def _generate_safari_mobile_ua(self) -> str:
        return f"Mozilla/5.0 (iPhone; CPU iPhone OS {self._get_ios_version()} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{self._get_safari_version()} Mobile/15E148 Safari/604.1"

    def _generate_firefox_mobile_ua(self) -> str:
        return f"Mozilla/5.0 (Android {self._get_android_version()}; Mobile; rv:{self._get_firefox_version()}.0) Gecko/{self._get_firefox_version()}.0 Firefox/{self._get_firefox_version()}.0"

    def _generate_edge_mobile_ua(self) -> str:
        return f"Mozilla/5.0 (Linux; Android {self._get_android_version()}; {self._get_android_device()}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self._get_chrome_version()} Mobile Safari/537.36 EdgA/{self._get_edge_version()}"

    def _generate_opera_mobile_ua(self) -> str:
        return f"Mozilla/5.0 (Linux; Android {self._get_android_version()}; {self._get_android_device()}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self._get_chrome_version()} Mobile Safari/537.36 OPR/{self._get_opera_version()}"

    def _generate_qq_mobile_ua(self) -> str:
        qq_ver = f"{random.randint(13, 15)}.{random.randint(0, 5)}.{random.randint(3000, 3500)}"
        return f"Mozilla/5.0 (Linux; Android {self._get_android_version()}; {self._get_android_device()}) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{self._get_chrome_version()} MQQBrowser/{qq_ver} Mobile Safari/537.36"


_generator = UserAgentGenerator()


def random_ua() -> str:
    """返回一条随机桌面端 UA（按市场份额权重 + 动态版本 + OS 变体）"""
    return _generator.get_realistic_user_agent(mobile_mode=False)
```

- [ ] **步骤 2：验证导入**

```bash
python -c "from utils.user_agent import random_ua; print(random_ua())"
```

预期：输出一条格式正确的 UA 字符串，如 `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36`

- [ ] **步骤 3：Commit**

```bash
git add utils/user_agent.py
git commit -m "feat: add UserAgentGenerator with market-share-weighted UA pool"
```

---

### 任务 2：新增 `tests/test_user_agent.py` — UA 生成器测试

**文件：**
- 创建：`tests/test_user_agent.py`

- [ ] **步骤 1：编写测试并运行**

```python
"""Tests for utils.user_agent."""
import unittest
from utils.user_agent import random_ua, UserAgentGenerator


class TestRandomUA(unittest.TestCase):
    def test_returns_non_empty_string(self):
        ua = random_ua()
        self.assertIsInstance(ua, str)
        self.assertGreater(len(ua), 50)

    def test_returns_different_on_successive_calls(self):
        uas = set()
        for _ in range(100):
            uas.add(random_ua()[:40])
        self.assertGreater(len(uas), 1, "Expected >1 unique UA in 100 calls")

    def test_output_looks_like_browser_ua(self):
        ua = random_ua()
        self.assertTrue(
            any(b in ua for b in ("Chrome/", "Firefox/", "Safari/", "Edg/", "OPR/", "QQBrowser/")),
            f"UA should contain a browser identifier, got: {ua}",
        )


class TestUserAgentGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = UserAgentGenerator()

    def test_desktop_ua_contains_platform(self):
        ua = self.gen.get_realistic_user_agent(mobile_mode=False)
        self.assertTrue(
            any(p in ua for p in ("Windows NT", "Macintosh", "Linux")),
            f"Desktop UA should contain a platform, got: {ua}",
        )

    def test_mobile_ua_contains_mobile_marker(self):
        ua = self.gen.get_realistic_user_agent(mobile_mode=True)
        self.assertIn("Mobile", ua)
```

- [ ] **步骤 2：运行测试**

```bash
python -m pytest tests/test_user_agent.py -v
```

预期：5 passed

- [ ] **步骤 3：Commit**

```bash
git add tests/test_user_agent.py
git commit -m "test: add unit tests for UserAgentGenerator"
```

---

### 任务 3：改造 `utils/http_client.py` — BROWSER_HEADERS → build_headers()

**文件：**
- 修改：`utils/http_client.py:34-49`（BROWSER_HEADERS 定义）
- 修改：`utils/http_client.py:68`（fetch_page 内的引用）

- [ ] **步骤 1：确认 BROWSER_HEADERS 未被外部导入**

```bash
grep -rn "BROWSER_HEADERS" --include="*.py" .
```

预期：仅 `utils/http_client.py` 有匹配。

- [ ] **步骤 2：实施替换**

将 `utils/http_client.py` 第 34-50 行：

```python
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
```

替换为：

```python
import re

from utils.user_agent import random_ua


def build_headers() -> dict:
    """构建带随机 UA 的浏览器请求头。每次调用生成新的 UA 及匹配的 Sec-CH-UA。"""
    ua = random_ua()
    chrome_ver_match = re.search(r"Chrome/(\d+)", ua)
    chrome_major = chrome_ver_match.group(1) if chrome_ver_match else "120"

    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": f'"Not_A Brand";v="8", "Chromium";v="{chrome_major}", "Google Chrome";v="{chrome_major}"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
```

将第 68 行：

```python
    headers = {**BROWSER_HEADERS}
```

替换为：

```python
    headers = build_headers()
```

- [ ] **步骤 3：验证**

```bash
python -c "from utils.http_client import build_headers; h = build_headers(); assert 'User-Agent' in h; print(h['User-Agent'][:80])"
```

预期：每次运行输出不同 UA。

- [ ] **步骤 4：运行现有测试**

```bash
python -m pytest tests/test_articles.py tests/test_subscribe.py -v
```

预期：所有已有测试通过。

- [ ] **步骤 5：Commit**

```bash
git add utils/http_client.py
git commit -m "refactor: replace static BROWSER_HEADERS with dynamic build_headers() using random UA"
```

---

### 任务 4：新增 `utils/mp_api_client.py` — 管理后台 API 客户端

**文件：**
- 创建：`utils/mp_api_client.py`

- [ ] **步骤 1：创建 `utils/mp_api_client.py`**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信管理后台 API 客户端
封装 appmsgpublish 等 JSON API 的请求：
curl_cffi TLS 伪装 + 可配置代理 + 随机 UA + 统一错误分类。
"""
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

from utils.user_agent import random_ua

try:
    from curl_cffi.requests import Session as CurlSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)
_local = threading.local()


@dataclass
class MpApiResult:
    """fetch_mp_api 的统一返回类型"""
    data: Optional[dict] = None
    error_type: str = ""  # "" | "frequency_control" | "token_expired" | "invalid_fakeid" | "network_error" | "unknown"

    @property
    def is_ok(self) -> bool:
        return self.data is not None and self.error_type == ""


def _get_session() -> CurlSession:
    """每线程一个持久 CurlSession，复用 TCP/TLS 连接"""
    if not hasattr(_local, 'session'):
        _local.session = CurlSession(impersonate="chrome120")
    return _local.session


def _classify_error(ret_code: int, err_msg: str) -> str:
    """将微信 ret code 映射为结构化错误类型"""
    if ret_code == 200013:
        return "frequency_control"
    if ret_code == 200003:
        return "token_expired"
    if ret_code == 200002 and "invalid arg" in (err_msg or "").lower():
        return "invalid_fakeid"
    return "unknown"


async def fetch_mp_api(
    url: str,
    params: dict,
    creds: dict,
    use_proxy: bool = False,
    timeout: int = 30,
) -> MpApiResult:
    """
    请求微信管理后台 JSON API。

    Args:
        url: API URL
        params: 查询参数
        creds: {"token": "...", "cookie": "..."}
        use_proxy: 是否通过代理池转发
        timeout: 超时秒数

    Returns:
        MpApiResult: .is_ok 为 True 时 .data 是完整 JSON dict
    """
    from utils.http_client import build_headers

    headers = build_headers()
    headers["Referer"] = "https://mp.weixin.qq.com/"
    headers["Cookie"] = creds.get("cookie", "")

    proxy = None
    if use_proxy:
        from utils.proxy_pool import proxy_pool
        proxy = proxy_pool.next()

    loop = asyncio.get_event_loop()

    if HAS_CURL_CFFI:
        try:
            data = await loop.run_in_executor(
                _executor,
                _fetch_sync_curl, url, params, headers, proxy, timeout,
            )
        except Exception as e:
            logger.warning("curl_cffi request failed: %s", e)
            if use_proxy and proxy:
                from utils.proxy_pool import proxy_pool
                proxy_pool.mark_failed(proxy)
            return MpApiResult(error_type="network_error")
    else:
        try:
            data = await _fetch_httpx_fallback(url, params, headers, timeout)
        except Exception as e:
            logger.warning("httpx fallback failed: %s", e)
            return MpApiResult(error_type="network_error")

    if data is None:
        return MpApiResult(error_type="network_error")

    base_resp = data.get("base_resp", {})
    ret_code = base_resp.get("ret", -1)

    if ret_code == 0:
        if use_proxy and proxy:
            from utils.proxy_pool import proxy_pool
            proxy_pool.mark_ok(proxy)
        return MpApiResult(data=data)

    error_type = _classify_error(ret_code, base_resp.get("err_msg", ""))
    logger.warning("WeChat API error: ret=%d type=%s", ret_code, error_type)
    if use_proxy and proxy and error_type in ("frequency_control", "network_error"):
        from utils.proxy_pool import proxy_pool
        proxy_pool.mark_failed(proxy)
    return MpApiResult(error_type=error_type)


def _fetch_sync_curl(
    url: str, params: dict, headers: dict,
    proxy: Optional[str], timeout: int,
) -> Optional[dict]:
    """同步 curl_cffi 请求，在线程池中执行"""
    kwargs = {"timeout": timeout, "allow_redirects": True}
    if proxy:
        kwargs["proxy"] = proxy
    with _get_session() as session:
        resp = session.get(url, params=params, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()


async def _fetch_httpx_fallback(
    url: str, params: dict, headers: dict, timeout: int,
) -> Optional[dict]:
    """httpx 降级请求"""
    async with httpx.AsyncClient(timeout=float(timeout), follow_redirects=True) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()
```

- [ ] **步骤 2：验证导入**

```bash
python -c "from utils.mp_api_client import fetch_mp_api, MpApiResult; print('OK')"
```

- [ ] **步骤 3：Commit**

```bash
git add utils/mp_api_client.py
git commit -m "feat: add mp_api_client with curl_cffi + classified error handling"
```

---

### 任务 5：新增 `tests/test_mp_api_client.py` — mp_api_client 测试

**文件：**
- 创建：`tests/test_mp_api_client.py`

- [ ] **步骤 1：编写测试并运行**

```python
"""Tests for utils.mp_api_client — error classification and fetch flow."""
import asyncio
import unittest
from utils.mp_api_client import MpApiResult, _classify_error


class TestMpApiResult(unittest.TestCase):
    def test_is_ok_with_data_and_no_error(self):
        result = MpApiResult(data={"base_resp": {"ret": 0}})
        self.assertTrue(result.is_ok)

    def test_is_not_ok_with_error_type(self):
        result = MpApiResult(error_type="frequency_control")
        self.assertFalse(result.is_ok)

    def test_is_not_ok_with_none_data(self):
        result = MpApiResult(data=None)
        self.assertFalse(result.is_ok)


class TestClassifyError(unittest.TestCase):
    def test_frequency_control(self):
        self.assertEqual(_classify_error(200013, ""), "frequency_control")

    def test_token_expired(self):
        self.assertEqual(_classify_error(200003, ""), "token_expired")

    def test_invalid_fakeid(self):
        self.assertEqual(_classify_error(200002, "invalid args"), "invalid_fakeid")

    def test_invalid_fakeid_case_insensitive(self):
        self.assertEqual(_classify_error(200002, "Invalid Args"), "invalid_fakeid")

    def test_unknown(self):
        self.assertEqual(_classify_error(99999, "some error"), "unknown")


class TestFetchMpApi(unittest.TestCase):
    def setUp(self):
        self.creds = {"token": "test", "cookie": "test"}
        self.params = {}

    def _run(self, coro):
        return asyncio.run(coro)

    @unittest.mock.patch('utils.mp_api_client._fetch_sync_curl')
    @unittest.mock.patch('utils.mp_api_client.HAS_CURL_CFFI', True)
    def test_fetch_returns_ok_on_success(self, mock_fetch):
        mock_fetch.return_value = {"base_resp": {"ret": 0}, "publish_page": "{}"}
        from utils.mp_api_client import fetch_mp_api
        result = self._run(fetch_mp_api("http://test", self.params, self.creds))
        self.assertTrue(result.is_ok)

    @unittest.mock.patch('utils.mp_api_client._fetch_sync_curl')
    @unittest.mock.patch('utils.mp_api_client.HAS_CURL_CFFI', True)
    def test_fetch_returns_frequency_control(self, mock_fetch):
        mock_fetch.return_value = {"base_resp": {"ret": 200013, "err_msg": "freq"}}
        from utils.mp_api_client import fetch_mp_api
        result = self._run(fetch_mp_api("http://test", self.params, self.creds))
        self.assertEqual(result.error_type, "frequency_control")

    @unittest.mock.patch('utils.mp_api_client._fetch_sync_curl')
    @unittest.mock.patch('utils.mp_api_client.HAS_CURL_CFFI', True)
    def test_fetch_returns_token_expired(self, mock_fetch):
        mock_fetch.return_value = {"base_resp": {"ret": 200003}}
        from utils.mp_api_client import fetch_mp_api
        result = self._run(fetch_mp_api("http://test", self.params, self.creds))
        self.assertEqual(result.error_type, "token_expired")

    @unittest.mock.patch('utils.mp_api_client._fetch_sync_curl')
    @unittest.mock.patch('utils.mp_api_client.HAS_CURL_CFFI', True)
    def test_fetch_handles_network_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("Connection refused")
        from utils.mp_api_client import fetch_mp_api
        result = self._run(fetch_mp_api("http://test", self.params, self.creds))
        self.assertEqual(result.error_type, "network_error")
```

- [ ] **步骤 2：运行测试**

```bash
python -m pytest tests/test_mp_api_client.py -v
```

预期：8 passed

- [ ] **步骤 3：Commit**

```bash
git add tests/test_mp_api_client.py
git commit -m "test: add unit tests for mp_api_client error classification"
```

---

### 任务 6：改造 `utils/rss_poller.py` — _fetch_article_list + _poll_all

**文件：**
- 修改：`utils/rss_poller.py`

- [ ] **步骤 1：新增 TokenExpiredError**

在第 40 行（`WechatInvalidFakeidError` 后面）插入：

```python
class TokenExpiredError(Exception):
    """RSS 轮询期间检测到 token 过期（ret=200003），轮询器应立即中断当前轮次。"""
    pass
```

在文件顶部导入中加入 `import random`（在第 12 行附近）。

- [ ] **步骤 2：重写 `_fetch_article_list`（第 220-307 行）**

将整个方法替换为：

```python
    async def _fetch_article_list(self, fakeid: str, creds: Dict) -> List[Dict]:
        """通过 fetch_mp_api 获取文章列表。"""
        from utils.mp_api_client import fetch_mp_api
        import os

        use_proxy = os.getenv("MP_API_USE_PROXY", "false").lower() == "true"

        params = {
            "sub": "list",
            "search_field": "null",
            "begin": 0,
            "count": ARTICLES_PER_POLL,
            "query": "",
            "fakeid": fakeid,
            "type": "101_1",
            "free_publish_type": 1,
            "sub_action": "list_ex",
            "token": creds["token"],
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1,
        }

        result = await fetch_mp_api(
            "https://mp.weixin.qq.com/cgi-bin/appmsgpublish",
            params=params, creds=creds, use_proxy=use_proxy,
        )

        if result.is_ok:
            assert result.data is not None
            data = result.data
            publish_page = data.get("publish_page", {})
            if isinstance(publish_page, str):
                try:
                    publish_page = json.loads(publish_page)
                except (json.JSONDecodeError, ValueError):
                    return []
            if not isinstance(publish_page, dict):
                return []

            articles = []
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
                    articles.append({
                        "aid": a.get("aid", ""),
                        "title": a.get("title", ""),
                        "link": a.get("link", ""),
                        "digest": a.get("digest", ""),
                        "cover": a.get("cover", ""),
                        "author": a.get("author", ""),
                        "publish_time": a.get("update_time", 0),
                    })
            return articles

        if result.error_type == "invalid_fakeid":
            raise WechatInvalidFakeidError(
                f"fakeid {fakeid[:8]} 已失效（注销/改名）"
            )
        if result.error_type == "token_expired":
            raise TokenExpiredError("登录过期，请重新扫码登录")
        logger.warning("Poll skip for %s: error_type=%s", fakeid[:8], result.error_type)
        return []
```

- [ ] **步骤 3：修改 `_poll_all` — 间隔 + TokenExpiredError 中断**

将第 204 行 `await asyncio.sleep(3)` 替换为：

```python
            await asyncio.sleep(random.randint(3, 8))
```

在 `except WechatInvalidFakeidError` 块之后（第 197 行之前）、`except Exception` 之前插入：

```python
            except TokenExpiredError:
                logger.error("Token expired, aborting poll cycle")
                self.consecutive_failures += 1
                self.last_fail_time = time.time()
                self.last_fail_msg = "Token 已过期，请重新扫码登录"
                break
```

- [ ] **步骤 4：运行测试**

```bash
python -m pytest tests/test_subscribe.py::TestPoll -v
```

预期：`test_poll_success` 通过。

- [ ] **步骤 5：Commit**

```bash
git add utils/rss_poller.py
git commit -m "feat: integrate fetch_mp_api into RSS poller with TokenExpiredError interrupt"
```

---

### 任务 7：改造 `routes/articles.py` — httpx → fetch_mp_api

**文件：**
- 修改：`routes/articles.py:100-113`

- [ ] **步骤 1：修改 `get_articles` 函数**

删除第 102-107 行的 headers 定义：

```python
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://mp.weixin.qq.com/",
            "Cookie": cookie
        }
```

将第 109-112 行：

```python
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            result = response.json()
```

替换为：

```python
        from utils.mp_api_client import fetch_mp_api
        import os

        creds_dict = {"token": token, "cookie": cookie}
        use_proxy = os.getenv("MP_API_USE_PROXY", "false").lower() == "true"
        api_result = await fetch_mp_api(
            url, params=params, creds=creds_dict, use_proxy=use_proxy,
        )

        if api_result.error_type == "token_expired":
            return ArticlesResponse(
                success=False, error="登录已过期，请重新登录"
            )
        if api_result.error_type == "frequency_control":
            return ArticlesResponse(
                success=False, error="请求过于频繁，请稍后重试"
            )
        if not api_result.is_ok:
            return ArticlesResponse(
                success=False, error=f"获取文章列表失败: {api_result.error_type}"
            )

        assert api_result.data is not None
        result = api_result.data
```

- [ ] **步骤 2：运行测试**

```bash
python -m pytest tests/test_articles.py -v
```

预期：所有已有测试通过。

- [ ] **步骤 3：Commit**

```bash
git add routes/articles.py
git commit -m "refactor: use fetch_mp_api in public articles listing endpoint"
```

---

### 任务 8：改造 `routes/admin.py` — httpx → fetch_mp_api

**文件：**
- 修改：`routes/admin.py:373-394`

- [ ] **步骤 1：修改 `_fetch_history_internal` 函数**

将第 373-394 行：

```python
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
```

替换为：

```python
        from utils.mp_api_client import fetch_mp_api
        import os

        creds_dict = {"token": creds["token"], "cookie": creds["cookie"]}
        use_proxy = os.getenv("MP_API_USE_PROXY", "false").lower() == "true"
        api_result = await fetch_mp_api(
            "https://mp.weixin.qq.com/cgi-bin/appmsgpublish",
            params=params, creds=creds_dict, use_proxy=use_proxy,
        )

        if api_result.error_type == "token_expired":
            raise ValueError("登录已过期，请重新扫码登录")
        if api_result.error_type == "frequency_control":
            raise ValueError("请求过于频繁，触发频率控制，请稍后重试")
        if not api_result.is_ok:
            raise ValueError(f"微信API错误: {api_result.error_type}")

        assert api_result.data is not None
        result = api_result.data
```

- [ ] **步骤 2：验证**

```bash
python -c "import routes.admin; print('OK')"
```

- [ ] **步骤 3：Commit**

```bash
git add routes/admin.py
git commit -m "refactor: use fetch_mp_api in admin history fetch endpoint"
```

---

### 任务 9：全链路回归测试

- [ ] **步骤 1：运行全部测试**

```bash
python -m pytest tests/ -v
```

预期：所有 76+ 测试通过（加上新增 13 个，共 89+ passed）。

- [ ] **步骤 2：Commit**

```bash
git commit -m "all tests passing after mp_api anti-crawl hardening" --allow-empty
```

---

## 自检报告

1. **规格覆盖度**：设计文档 §2-5 的每个模块均有对应任务。§6 测试要点被任务 2 和任务 5 覆盖。
2. **占位符扫描**：无 TODO/待定/后续实现。
3. **类型一致性**：`MpApiResult` 在任务 4 定义，任务 5-8 使用，属性名 `.data` / `.error_type` / `.is_ok` 一致。`fetch_mp_api` 签名各任务一致。
