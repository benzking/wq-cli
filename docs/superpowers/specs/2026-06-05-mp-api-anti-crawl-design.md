# 设计文档：文章列表扫描反爬加固

> **日期**: 2026-06-05
> **状态**: 已批准
> **来源**: 深度分析 we-mp-rss 项目后，移植其管理后台 API 请求层防护策略到 wq-cli

## 一、背景与范围

wq-cli 中所有调用微信 `appmsgpublish` 管理后台 API 的位置（共3处）均使用裸 `httpx.AsyncClient` + 静态 UA，
而正文抓取路径已有完整的 curl_cffi + 代理池防线。本次将请求层防护统一到管理后台 API 路径。

**范围内**:
- RSS 轮询器 `_fetch_article_list` / `poll_single`
- `routes/articles.py` 公开文章列表 API
- `routes/admin.py` 管理后台批量导入

**范围外**:
- 正文抓取路径（域二）：curl_cffi + L1→L2→L3 回落管道不做修改
- Playwright / JS 反检测沙箱：不做
- 代理池/熔断器/CF Worker 基础设施：不做修改

## 二、新增模块

### `utils/user_agent.py`

从 we-mp-rss `driver/user_agent.py` 完整移植 `UserAgentGenerator` 类：
- 6 类浏览器（Chrome 65% / Edge 12% / Firefox 8% / Safari 8% / Opera 5% / QQ 2%）
- 动态版本号范围（Chrome 110-125、Edge 110-125、Firefox 110-125、Safari 15-17、Opera 90-110）
- Windows/Mac/Linux OS 变体
- 移动端生成逻辑保留但不主动使用

公开接口：`random_ua() -> str`

### `utils/mp_api_client.py`

```python
@dataclass
class MpApiResult:
    data: Optional[dict] = None       # ret=0 时的完整 JSON 响应
    error_type: str = ""             # "" | "frequency_control" | "token_expired" | "invalid_fakeid" | "network_error" | "unknown"

    @property
    def is_ok(self) -> bool:
        return self.data is not None and self.error_type == ""

async def fetch_mp_api(
    url: str, params: dict, creds: dict,
    use_proxy: bool = False,        # 默认关闭，通过 MP_API_USE_PROXY=true 开启
    timeout: int = 30,
) -> MpApiResult:
```

内部流程：
1. `build_headers()` 生成随机 UA headers，注入 Cookie + Referer
2. 若 `use_proxy=True`，从 `proxy_pool.next()` 获取代理
3. 线程安全的持久 `CurlSession(impersonate="chrome120")` 执行 GET
4. 解析 JSON：ret=0 → `mark_ok(proxy)`，ret≠0 → 分类错误码
5. 网络异常：`mark_failed(proxy)`（如使用代理），`error_type="network_error"`

错误分类：200013→frequency_control、200003→token_expired、200002+"invalid arg"→invalid_fakeid、其他非0→unknown

## 三、改造模块

### `utils/http_client.py`

`BROWSER_HEADERS` 静态字典 → `build_headers()` 函数（内部调用 `random_ua()`）。
`fetch_page` 内部调用替换。所有正文抓取调用者零改动自动获得随机 UA。

### `utils/rss_poller.py`

新增 `TokenExpiredError` 异常类。

`_fetch_article_list` 重写：
- 调用 `fetch_mp_api` → 解析 `MpApiResult`
- `is_ok` → 解析 `publish_page.publish_list[].publish_info.appmsgex[]` 返回 `List[Dict]`
- `invalid_fakeid` → `raise WechatInvalidFakeidError`（保持现有契约）
- `token_expired` → `raise TokenExpiredError`（新）
- 其余错误 → `return []`

`_poll_all` 改动：
- 间隔改为 `random.randint(3, 8)` 秒（原固定 3s）
- 新增 `except TokenExpiredError: break` 中断整轮
- 保留 `consecutive_failures` / 黑名单逻辑不动

`poll_single`：切换到 `fetch_mp_api`，保留黑名单逻辑。

### `routes/articles.py` + `routes/admin.py`

裸 `httpx.AsyncClient` → `fetch_mp_api()`。
根据 `error_type` 转换为对应的 HTTP 异常（401/429/500）。

## 四、配置

| 键 | 默认值 | 说明 |
|----|--------|------|
| `MP_API_USE_PROXY` | `false` | 管理后台 API 是否通过代理池转发 |

## 五、测试要点

- `test_mp_api_client.py`: mock curl_cffi，验证 4 种错误码分类 + 正常返回
- `test_user_agent.py`: 验证 random_ua() 非空、格式合法
- `test_rss_poller.py`: mock fetch_mp_api，验证 _poll_all 的统计 / 中断 / 黑名单逻辑
- `test_http_client.py`: 验证 build_headers() 迁移后 fetch_page 行为不变
- 全链路回归：验证 RSS 轮询 + `/api/articles` + admin 批量导入正常
