# 历史获取接入 Worker 队列 — 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在历史获取 `save_articles()` 后追加 `log_ingestion_start()` + `fetch_worker.wake()`，使 Worker 能发现历史文章并抓取正文。

**架构：** 修改 `routes/admin.py` 中 `_fetch_history_internal` 函数，在保存文章元数据后，将文章链接写入 `ingestion_logs`（channel=deep_fetch）并唤醒 Worker。Worker 优先级排序已有 `deep_fetch` 规则，翻页计数器已有 `deep_fetch` 统计，均无需改动。

**技术栈：** Python 3.10+ / FastAPI / SQLite

---

### 任务 1：修改 _fetch_history_internal

**文件：**
- 修改：`routes/admin.py:446-452`

- [ ] **步骤 1：在 save_articles 后追加入列和唤醒**

```python
    # 截取到目标数量
    historical_articles = historical_articles[:target_count]

    # 保存到数据库（去重）
    new_count = rss_store.save_articles(fakeid, historical_articles)

    # 将新文章链接写入待办清单，唤醒 Worker 抓取正文
    links = [a["link"] for a in historical_articles if a.get("link")]
    if links:
        from utils.ingestion_store import log_ingestion_start
        log_ingestion_start(fakeid, links, channel="deep_fetch")
        from utils.fetch_worker import fetch_worker
        fetch_worker.wake()

    return len(historical_articles), new_count
```

- [ ] **步骤 2：验证语法正确**

运行：`python -c "import ast; ast.parse(open('routes/admin.py').read()); print('OK')"`
预期：输出 `OK`
