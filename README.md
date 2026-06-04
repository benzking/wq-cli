# wq-cli — 微信公众号文章获取 & RSS 订阅工具

**完全开源 | 私有化部署 | RSS 订阅 | 文章抓取 | CLI 命令行**

[![License](https://img.shields.io/badge/License-AGPL%203.0-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

> 100% 开源，100% 免费。代码完全公开，私有化部署无任何限制。

---

## 功能特性

- **RSS 订阅** — 订阅任意公众号，自动定时拉取新文章（包含完整文章内容和图片），生成标准 RSS 2.0 源，兼容 FreshRSS / Feedly / NetNewsWire 等主流阅读器
- **文章内容获取** — 通过 URL 获取文章完整内容（标题、作者、正文 HTML / 纯文本、图片列表），支持多种内容类型（富文本、图文消息、短内容、音频等）
- **命令行工具（wq CLI）** — 提供 10 个子命令，覆盖文章获取、公众号搜索、RSS 订阅管理、内容推送、健康检查等，适合脚本和自动化场景
- **反风控体系** — 三层代理回落：Cloudflare Worker 代理（L1）→ SOCKS5 代理池轮转（L2）→ 直连（L3），配合 Chrome TLS 指纹模拟，有效对抗微信封控
- **文章列表 & 搜索** — 获取任意公众号历史文章列表，支持分页和关键词搜索
- **公众号搜索** — 按名称搜索公众号，获取 FakeID 及认证主体信息
- **扫码登录** — 微信公众平台扫码登录，凭证自动保存，有效期约 4 天，过期前 Webhook 预警
- **图片代理** — 代理微信 CDN 图片，解决防盗链问题
- **文章导出** — 支持将文章导出为 Obsidian 兼容的 Markdown 格式，图片自动打包 ZIP 下载
- **入库管理** — Worker 调度 + 渠道熔断器，自动采集和入库文章内容，支持禁止/重试等操作
- **系统日志** — 按日期滚动的日志文件 + 前端日志查看面板，方便排查问题
- **Webhook 通知** — 登录过期提醒（提前 24h/6h 预警 + 已过期通知）、轮询失败等事件自动推送（支持企业微信机器人）

---

## 使用前提

> 本工具需要通过微信公众平台后台的登录凭证来调用接口，因此使用前需要：

1. 拥有一个微信公众号（订阅号、服务号均可）
2. 部署并启动服务后，访问登录页面用**公众号管理员微信**扫码登录
3. 登录成功后凭证自动保存，有效期约 4 天，过期后需重新扫码

登录后即可通过 API 获取任意公众号的公开文章（不限于自己的公众号）。

> **本地电脑可以直接使用！** 不需要公网服务器——在本地启动服务后通过 `localhost` 访问即可完成扫码登录和全部功能。只有当你需要从其他设备远程访问时，才需要公网服务器或内网穿透。

---

## 快速开始

### 环境要求

- Python 3.8+

### 直接运行

```bash
git clone https://github.com/benzking/wq-cli.git
cd wq-cli
pip install -r requirements.txt
python app.py
```

服务启动后访问 `http://localhost:5000` 进入管理面板，或访问 `http://localhost:5000/login.html` 扫码登录。

### 一键脚本

```bash
bash start.sh        # Linux/macOS
start.bat            # Windows
```

脚本会自动完成环境检查、虚拟环境创建、依赖安装和服务启动。

### CLI 命令行

```bash
python -m cli --help                           # 查看所有命令
python -m cli search "人民日报"                 # 搜索公众号
python -m cli fetch "https://mp.weixin.qq.com/s/xxxxx"   # 获取文章
python -m cli subscribe add <fakeid> --nickname "人民日报"  # 添加订阅
python -m cli subscribe list                   # 查看订阅
python -m cli health                           # 健康检查
```

### Docker（本地构建）

```bash
docker-compose up -d                           # docker-compose
# 或
docker build -t wq-cli . && docker run -d -p 5000:5000 -v $(pwd)/data:/app/data wq-cli
```

---

## 访问地址

| 地址 | 说明 |
|------|------|
| `http://localhost:5000` | 管理面板首页 |
| `http://localhost:5000/login.html` | 扫码登录 |
| `http://localhost:5000/rss.html` | RSS 订阅管理 |
| `http://localhost:5000/ingestion.html` | 入库管理看板 |
| `http://localhost:5000/browse.html` | 文章在线浏览 |
| `http://localhost:5000/logs.html` | 系统日志查看 |
| `http://localhost:5000/api/docs` | Swagger API 文档 |
| `http://localhost:5000/api/health` | 健康检查 |

---

## 服务器部署

### Linux 生产环境（systemd）

```bash
sudo bash start.sh          # 自动注册 systemd 服务并开机自启
bash status.sh               # 查看运行状态
bash stop.sh                 # 停止服务
sudo systemctl restart wq-cli
```

### 反向代理（可选）

如需通过域名或 HTTPS 访问，配置 Nginx 反向代理到 `localhost:5000`：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## 配置说明

首次使用需复制配置模板：

```bash
cp env.example .env
```

编辑 `.env`，**至少设置 `SITE_URL`** 为你的实际访问地址（用于 RSS 图片代理，否则图片无法显示）：

```bash
SITE_URL=http://localhost:5000    # 本地开发
# SITE_URL=https://your-domain.com   # 公网部署
```

代理节点（CF Worker、SOCKS5）等运行时可调配置已迁移到 Web 管理面板，服务启动后在前端页面修改即可实时生效，无需手动编辑文件。

> **⚠️ 强烈建议**：启用 RSS 完整内容获取时，务必配置 CF Worker 代理或 SOCKS5 代理，避免直连微信导致账号风控。

---

## 反风控体系

三层代理回落机制：

```
文章请求
    │
    ▼
L1: Cloudflare Worker 代理
    │  利用 CF 全球 CDN 网络分散请求
    │  兼容 wechat-article-exporter 的公共节点和自建私有节点
    │  （未配置则跳过）
    ▼
L2: SOCKS5 代理池轮转
    │  多 VPS 代理 IP 轮转 + 失败冷却
    │  curl_cffi 模拟 Chrome TLS 指纹
    │  （未配置则跳过）
    ▼
L3: 直连（最终回落）
```

代理节点可在 Web 管理面板的「节点配置」页面动态增删，无需重启服务。

---

## 代理节点搭建

### Cloudflare Worker（推荐首选）

参考 [wechat-article-exporter](https://github.com/wechat-article/wechat-article-exporter) 的 Worker 部署方案，使用 Cloudflare 免费额度即可。部署后将 Worker URL 填入管理面板的 L1 节点配置。

### SOCKS5 代理池（L2 补充）

准备 2-3 台低价 VPS，每台运行 SOCKS5 代理服务。推荐使用 [gost](https://github.com/go-gost/gost)：

```bash
# VPS 上安装 gost
wget https://github.com/go-gost/gost/releases/download/v3.2.6/gost_3.2.6_linux_amd64.tar.gz
tar -xzf gost_3.2.6_linux_amd64.tar.gz && mv gost /usr/local/bin/

# 启动 SOCKS5 代理
gost -L socks5://myuser:mypass@:1080
```

将代理地址填入管理面板的 L2 节点配置即可。

---

## 内容类型支持

本项目支持多种微信公众号内容类型（富文本、图文消息、短内容、音频/视频分享等），并能正确识别各类不可用状态（已删除、违规、隐私限制、验证页面等）。

详细说明请查看 **[CONTENT_TYPES.md](CONTENT_TYPES.md)**。

---

## 项目结构

```
├── app.py                     # FastAPI 主应用入口
├── cli/                       # wq CLI 命令行工具（10 个子命令）
├── routes/                    # FastAPI 路由模块（15 个）
├── utils/                     # 工具模块（20+ 个）
├── static/                    # 前端页面（无框架，纯 HTML/CSS/JS）
├── data/                      # 运行时数据（SQLite，gitignored）
├── requirements.txt           # Python 依赖
├── env.example                # 初始配置模板
├── Dockerfile                 # Docker 构建文件
├── docker-compose.yml         # Docker Compose 配置
├── start.sh / start.bat       # 一键启动脚本
├── stop.sh / status.sh        # 服务管理脚本
└── CONTENT_TYPES.md           # 内容类型识别策略文档
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| ASGI 服务器 | Uvicorn |
| HTTP 客户端 | curl_cffi（Chrome TLS 指纹）/ HTTPX（降级） |
| 反风控 | CF Worker 代理 + SOCKS5 代理池 + 三层回落 |
| 数据存储 | SQLite（WAL 模式，零配置） |
| 前端 | 原生 HTML/CSS/JS（Tailwind CSS），无构建步骤 |
| 配置管理 | SQLite + Web 管理面板 |
| 运行环境 | Python 3.8+ |

---

## 常见问题

<details>
<summary><b>提示"服务器未登录"</b></summary>

访问 `http://localhost:5000/login.html` 扫码登录即可。
</details>

<details>
<summary><b>触发微信风控 / 需要验证</b></summary>

1. 在管理面板配置 CF Worker 或 SOCKS5 代理分散请求 IP
2. 在浏览器中打开提示的文章 URL 完成验证
3. 等待冷却后重试（系统已内置自动限频）
</details>

<details>
<summary><b>如何获取公众号的 FakeID</b></summary>

搜索接口或 CLI：`python -m cli search "公众号名称"`，从返回结果的 `fakeid` 字段获取。
</details>

<details>
<summary><b>Token 多久过期？</b></summary>

约 4 天。系统会提前 24h / 6h 通过 Webhook 预警，过期后立即通知。配置 Webhook 地址可在管理面板中操作。
</details>

---

## 开源协议

本项目采用 **AGPL 3.0** 协议开源。

| 使用场景 | 是否允许 |
|---------|---------|
| 个人学习和研究 | ✅ 允许 |
| 企业内部使用 | ✅ 允许 |
| 私有化部署 | ✅ 允许 |
| 修改后对外提供网络服务 | ⚠️ 需开源修改后的代码 |

### 免责声明

- 本软件按"原样"提供，不提供任何形式的担保
- 本项目仅供学习和研究目的，请遵守微信公众平台相关服务条款
- 使用者对自己的操作承担全部责任

---

## 致谢

本项目受以下项目的启发，在其基础上进行了重新设计与实现：

- **[wechat-download-api](https://github.com/tmwgsicp/wechat-download-api)** — 提供了微信公众号文章抓取与 RSS 订阅的核心思路和基础架构
- **[wechat-article-exporter](https://github.com/wechat-article/wechat-article-exporter)** — 提供了浏览器扩展端的文章导出方案和 Cloudflare Worker 代理思路

感谢原作者的探索与研究。

此外，以下开源项目为本项目提供了重要支持：

- [FastAPI](https://fastapi.tiangolo.com/) — 高性能 Python Web 框架
- [curl_cffi](https://github.com/lexiforest/curl_cffi) — 支持浏览器 TLS 指纹模拟的 HTTP 客户端
- [HTTPX](https://www.python-httpx.org/) — 现代化 HTTP 客户端
- [gost](https://github.com/go-gost/gost) — 轻量级代理工具
