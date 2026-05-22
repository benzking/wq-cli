---
name: wechat-query
description: |
  WeChat Official Account subscription, query, and push. Operates local wq-cli service
  (localhost:5000) via `wq` CLI. Supports account search, RSS subscription, article
  fetch/cache, QR code login, daily inspection and article push.
tags: [wechat, rss, monitor, automation]
triggers:
  - 微信/公众号/订阅号/公众号文章
  - 扫码登录/重登/重新登录
  - 文章推送/每日推送/文章汇总/文章抓取
  - 服务巡检/检查服务/公众号状态/RSS
  - 微信公众号文章链接 (https://mp.weixin.qq.com/s/...)
  - wq / wechat-query / subscribe / poll / fetch article
tool_groups: [reader, monitor]
---

# wechat-query (OpenClaw)

## Pre-check

```bash
wq check || (cd /home/gly/wq-cli && bash start.sh && sleep 3 && wq check)
```

If `wq` is not found, use the wrapper:
```bash
/home/gly/wq-cli/wq.sh check
```

## Commands

### Search & Subscribe

```bash
wq search <关键词>
wq subscribe <fakeid> --nickname=<名称>
wq unsubscribe <fakeid>
wq subscriptions --format=table
wq info <fakeid>
```

### Articles

```bash
wq poll
wq articles --hours=48 --limit=10
wq articles --hours=24 --keyword=数据 --format=json
wq fetch <url>
wq fetch <url> --format=md --outdir=./output
wq fetch <url> --format=mhtml --outdir=./output
```

### Push & Ops

```bash
wq md-push --hours=24
wq push-report --hours=24
wq login
wq check
wq check --auto-recover
```

## References

- Command details: `references/commands.md`
- Output formats: `references/formats.md`
- Error troubleshooting: `references/troubleshooting.md`
