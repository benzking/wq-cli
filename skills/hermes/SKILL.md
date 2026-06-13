---
name: wechat-query
description: |
  微信公众号订阅、查询与推送 Skill。通过 wq CLI 操作本地 wq-cli 服务 (localhost:5000)，
  支持公众号搜索/订阅、文章缓存查询/抓取、扫码登录重登、每日推送与巡检。
  当用户提到"微信"、"公众号"、"订阅号"、"扫码登录"、"文章推送"等时触发。
triggers:
  - 微信/公众号/订阅号
  - 扫码登录/重登/重新登录
  - 文章推送/每日推送/文章汇总
  - 服务巡检/检查服务/公众号状态
  - 微信公众号文章链接 (https://mp.weixin.qq.com/s/...)
tags: [wechat, rss, monitor, automation]
metadata:
  hermes:
    tags: [wechat, rss, monitor, automation]
---

# wechat-query Skill

## 概况

本地部署了 wq-cli 服务（FastAPI，`localhost:5000`），通过微信公众号后台 API 拉取已订阅公众号的文章，缓存到 SQLite。

> ⚠️ 旧入口 `~/.hermes/skills/wechat-query/scripts/wechat-query.py` 已于 2026-05-22 标记 deprecated，
> 保留至 2026-05-29 作为 rollback。新入口为 `wq` 命令。

> 后端服务迁移记录见 `references/migration-wq-cli.md`

## CLI 速查

所有操作通过 `wq` 命令完成。如果 `wq` 不在 PATH，使用 wrapper：

```bash
# 首选（如果 pip install -e 生效）
wq check

# 备用（wrapper 脚本）
/home/gly/wq-cli/wq.sh check
```

### 基础检查
```bash
wq check                          # 健康 + 登录状态 (含 version/framework/proxy_pool/fallback)
wq check --auto-recover           # 健康检查 + 失败时尝试自动重启
wq status                         # 仅认证状态 (JSON)
```

### 公众号搜索与详情
```bash
wq search <关键词>                 # 搜索公众号 → [fakeid, nickname, alias]
wq search <关键词> --format=table  # 表格展示
wq info <fakeid>                   # 认证主体、状态、原创文章数
```

### 订阅管理
```bash
wq subscribe <fakeid> --nickname=<名称> [--alias=<微信号>] [--head-img=<URL>]
wq unsubscribe <fakeid>
wq subscriptions                   # JSON 列表 (含 alias/ingested/historical)
wq subscriptions --format=table    # 表格展示 (Nickname, Alias, FakeID, Articles, Ingested)
wq poll                            # 手动触发全量轮询
```

### 文章
```bash
wq articles --hours=48 --limit=10
wq articles --hours=24 --keyword=数据 --format=json
wq fetch <url>                     # JSON, 默认
wq fetch <url> --format=md --outdir=./output
wq fetch <url> --format=mhtml --outdir=./output
```

### 推送
```bash
wq push-report --hours=24          # JSON 推送报告
wq md-push --hours=24              # ⚠️ 纯 Markdown 输出（非 JSON）
```

### 运维
```bash
wq login                           # 引导打开浏览器扫码
wq cron-setup                      # cron 注册指引
wq version                         # 版本信息
```

## 交互式工作流

### 场景：用户说"帮我搜一下 XX 公众号"
```bash
wq search XX
# → 返回 fakeid + nickname 列表，确认后 subscribe
```

### 场景：用户说"看看今天有什么新文章"
```bash
wq md-push
# → 输出 Markdown 报告，可直接发送给用户
```

### 场景：用户发来文章链接
```bash
wq fetch "https://mp.weixin.qq.com/s/xxx"
# → 返回结构化文章数据
```

### 场景：用户说"登录失效了/需要重登"
```bash
wq login
# → 输出 http://localhost:5000/login.html
# → 让用户用浏览器打开，扫码重登
```

## 定时任务

详见 `references/cron-setup.md`

## 参考

- 命令详细入参/出参: `references/commands.md`
- 文章输出格式: `references/formats.md`
- cron 配置: `references/cron-setup.md`
- 迁移记录: `references/migration-wq-cli.md`

## 常见问题

| 问题 | 处理 |
|------|------|
| 服务不可用 | `wq check` → 如果失败，`wq check --auto-recover` 或 `bash /home/gly/wq-cli/start.sh` |
| 登录失效 | `wq login` 打开 http://localhost:5000/login.html 扫码重登 |
| 触发验证 | 在浏览器中打开文章链接完成验证，等待 30 分钟重试 |
| DB 权限问题 | `wq articles` 自动 API 兜底；根治：`sudo usermod -aG wechat-api gly` |
