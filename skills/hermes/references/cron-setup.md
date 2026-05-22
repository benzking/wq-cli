# Cron 任务配置

## Hermes Cron

### 每日 09:00 服务巡检
```
cronjob action=create \
  name="wechat-inspection" \
  schedule="0 9 * * *" \
  script="cd /home/gly/wq-cli && /home/gly/wq-cli/venv/bin/python -m cli check" \
  no_agent=true \
  deliver=origin
```

### 每日 18:00 文章推送
```
cronjob action=create \
  name="wechat-daily-push" \
  schedule="0 18 * * *" \
  script="cd /home/gly/wq-cli && /home/gly/wq-cli/venv/bin/python -m cli md-push --hours=24" \
  no_agent=true \
  deliver=origin
```

### 验证
```
cronjob action=list
```

## OpenCLI Cron (参考)

```
opencli cron create --name wechat-check --schedule "0 9 * * *" -- wq check
opencli cron create --name wechat-push --schedule "0 18 * * *" -- wq md-push --hours=24
```

## 手动执行
```bash
# Inspection
cd /home/gly/wq-cli && /home/gly/wq-cli/venv/bin/python -m cli check

# Push
cd /home/gly/wq-cli && /home/gly/wq-cli/venv/bin/python -m cli md-push --hours=24
```

## 路径说明

| 项目 | 路径 |
|------|------|
| wq-cli 仓库 | `/home/gly/wq-cli/` |
| Python venv | `/home/gly/wq-cli/venv/bin/python` |
| CLI 入口 | `python -m cli` |
| Wrapper 脚本 | `/home/gly/wq-cli/wq.sh` |
| 数据库 | `/home/gly/wq-cli/data/rss.db` |
