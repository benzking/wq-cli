# 历史获取功能迁移至 RSS 页面 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 Settings 页的「历史获取」tab 移除，改为在 RSS 管理页每个公众号操作栏添加「深度获取」按钮，点击弹出数量输入弹窗，确认后执行历史文章获取。

**架构：** SettingsView.vue 删除 HistorySettings 组件引用及相关 tab；RssManageView.vue 新增 inline modal 和请求逻辑。后端 API 无需任何改动。

**技术栈：** Vue 3 + Composition API（`<script setup>`）, Vite。

---

### 文件改动清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `frontend/src/views/SettingsView.vue` | 修改 | 删除 HistorySettings 引用和渲染 |
| `frontend/src/components/settings/HistorySettings.vue` | 删除 | 不再被引用 |
| `frontend/src/views/RssManageView.vue` | 修改 | 新增深度获取按钮 + inline modal |
| （后端） | 不动 | `POST /api/admin/history/fetch` 已存在 |

---

### 任务 1：移除 Settings 页的历史获取 tab

**文件：**
- 修改：`frontend/src/views/SettingsView.vue`
- 删除：`frontend/src/components/settings/HistorySettings.vue`

- [ ] **步骤 1：编辑 SettingsView.vue，删除 3 处引用**

`frontend/src/views/SettingsView.vue` 中：

**第 8 行：** 删除 `import HistorySettings from '@/components/settings/HistorySettings.vue'`

**第 17 行：** 删除 `{ key: 'history', label: '历史获取' },`

**第 40 行：** 删除 `<HistorySettings v-if="activeTab === 'history'" />`

- [ ] **步骤 2：删除 HistorySettings.vue 文件**

```bash
rm frontend/src/components/settings/HistorySettings.vue
```

- [ ] **步骤 3：验证**

运行：`cd frontend && npx vite build 2>&1 | grep -i error`
预期：无报错

- [ ] **步骤 4：Commit**

```bash
git add frontend/src/views/SettingsView.vue
git rm frontend/src/components/settings/HistorySettings.vue
git commit -m "refactor: remove history fetch tab from Settings page"
```

---

### 任务 2：RSS 管理页新增深度获取功能

**文件：**
- 修改：`frontend/src/views/RssManageView.vue`

**改点 4 处：**
1. `<script setup>` 中新增状态和函数（`handleSinglePoll` 之后、`COL_KEYS` 之前）
2. desktop 操作栏（`<!-- 操作按钮 — 居中 -->` 内的 `取消` 按钮前）新增按钮
3. mobile 操作栏（`取消` 按钮前）新增按钮
4. `<!-- Modals -->` 区域末尾新增 inline modal

- [ ] **步骤 1：script 中新增状态和函数**

在代码中 `handleSinglePoll` 函数之后（约第 137 行之后）、`// ── column resize ────────────────────────────────────`（约第 139 行）之前，插入：

```js
// ── depth fetch ─────────────────────────────────────
const historyFetchTarget = ref(null)
const historyFetchName = ref('')
const historyFetchCount = ref(10)
const historyFetchLoading = ref(false)

function openHistoryFetch(fakeid, nickname) {
  historyFetchTarget.value = fakeid
  historyFetchName.value = nickname || ''
  historyFetchCount.value = 10
  historyFetchLoading.value = false
}

function closeHistoryFetch() {
  historyFetchTarget.value = null
}

async function confirmHistoryFetch() {
  if (!historyFetchTarget.value) return
  const count = Math.min(100, Math.max(1, parseInt(historyFetchCount.value) || 1))
  historyFetchLoading.value = true
  try {
    const res = await fetch('/api/admin/history/fetch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fakeid: historyFetchTarget.value, count }),
    })
    const data = await res.json()
    if (data.success) {
      toast.success(data.message || '获取完成')
      await loadSubscriptions()
    } else {
      toast.error(data.message || '获取失败')
    }
  } catch (e) {
    toast.error('网络错误: ' + e.message)
  } finally {
    historyFetchLoading.value = false
    closeHistoryFetch()
  }
}
```

- [ ] **步骤 2：desktop 操作栏新增按钮**

在 desktop 操作栏（约第 391 行 `<Trash2 :size="11" /> 取消` 按钮之前）插入：

```vue
          <button class="btn btn-xs" @click="openHistoryFetch(s.fakeid, s.nickname)" title="深度获取历史文章">
            深度获取
          </button>
```

修改后该区域变为：

```vue
          <button class="btn btn-xs" @click="openHistoryFetch(s.fakeid, s.nickname)" title="深度获取历史文章">
            深度获取
          </button>
          <button class="btn btn-xs" style="color:var(--error);border-color:rgba(189,60,60,0.25);" @click="openConfirm(s.fakeid)" title="取消订阅">
            <Trash2 :size="11" /> 取消
          </button>
```

- [ ] **步骤 3：mobile 操作栏新增按钮**

在 mobile 操作栏（约第 427 行 `取消` 按钮之前）插入：

```vue
          <button class="btn btn-xs flex-1" @click="openHistoryFetch(s.fakeid, s.nickname)">深度获取</button>
```

- [ ] **步骤 4：新增 inline modal**

在 `<!-- Modals -->`（约第 439 行）区域末尾、`</div>` 闭合前追加：

```vue
    <!-- Depth Fetch Modal -->
    <Teleport to="body">
      <transition name="scale">
        <div
          v-if="!!historyFetchTarget"
          class="fixed inset-0 z-[999] flex items-center justify-center p-5"
          style="background: rgba(0,0,0,0.35); backdrop-filter: blur(4px);"
          @click.self="closeHistoryFetch"
        >
          <div class="w-full max-w-[360px] rounded-2xl p-6 shadow-lg"
            style="background: var(--bg-primary);"
          >
            <h3 class="text-[15px] font-semibold mb-1" style="color: var(--text-primary);">深度获取</h3>
            <p class="text-[13px] mb-4" style="color: var(--text-secondary);">
              获取「{{ historyFetchName }}」的历史文章
            </p>

            <div class="flex items-center gap-3 mb-5">
              <label class="text-[13px] font-semibold shrink-0" style="color: var(--text-primary);">获取数量</label>
              <input
                v-model.number="historyFetchCount"
                type="number"
                min="1"
                max="100"
                class="w-20 py-1.5 px-2.5 border rounded-md text-[13px] outline-none"
                style="border-color: var(--border-base); color: var(--text-primary); background: var(--bg-primary);"
                :disabled="historyFetchLoading"
              />
              <span class="text-[11px]" style="color: var(--text-muted);">篇 (1-100)</span>
            </div>

            <div class="flex gap-2.5 justify-end">
              <button class="btn" :disabled="historyFetchLoading" @click="closeHistoryFetch">取消</button>
              <button class="btn btn-primary" :disabled="historyFetchLoading" @click="confirmHistoryFetch">
                {{ historyFetchLoading ? '获取中...' : '确定' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
```

- [ ] **步骤 5：验证构建**

```bash
cd frontend && npx vite build 2>&1 | tail -5
```

预期：Build 成功，无报错

- [ ] **步骤 6：Commit**

```bash
git add frontend/src/views/RssManageView.vue
git commit -m "feat(rss): add depth fetch button with count modal to subscription rows"
```

---

### 任务 3：构建 SPA

- [ ] **步骤 1：构建前端**

```bash
cd frontend && npm run build
```

预期：产物写入 `../static/assets/`，`../static/index.html` 引用更新

- [ ] **步骤 2：提交构建产物**

```bash
git add static/
git commit -m "build: rebuild SPA with depth fetch in RSS page"
```

---

### 验证清单

1. 访问 `/#/rss` → 每个公众号行出现「深度获取」按钮
2. 点击「深度获取」→ 弹出带数量输入框的弹窗，显示公众号名
3. 输入数量（如 5）→ 点击「确定」→ 弹窗关闭，toast 显示结果
4. 点击弹窗外空白或「取消」→ 弹窗关闭，无操作
5. 访问 `/#/settings` → 确认无「历史获取」tab
6. 访问 `/#/settings/history` → 页面空白（无害，路由仍匹配但无对应 tab 渲染）
