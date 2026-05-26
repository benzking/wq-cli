# UI 全面重构设计

## 目标

将 13 个独立 HTML 页面重构为统一 SPA，Notion 风格（浅色主基调、圆角卡片、柔和阴影），侧边栏导航，首页为数据看板，文章浏览为三栏 Google Reader 风格。

## 技术栈

- **Vue 3 + Vite**：`.vue` SFC（`<script setup>`），零运行时依赖（产出为纯静态文件）
- **构建产物**：`vite build` → `static/` 目录，FastAPI 直接 serve
- **前端路由**：`vue-router`（hash 模式），侧边栏固定不动
- **安全**：DOMPurify 净化文章 HTML（文章内容通过 `v-html` 渲染）
- **CSS**：`<style scoped>` 组件隔离 + 全局 CSS 变量（Notion 风格变量值）

## 构建与部署

```
frontend/                  ← Vite 项目根目录
├── package.json
├── vite.config.js         → build.outDir = ../static
└── src/
    ├── main.js            ← createApp + router + provide/inject
    ├── App.vue            ← 侧边栏 + 顶栏 + <router-view>
    ├── assets/
    │   └── main.css       ← CSS 变量 + reset + 全局基础样式
    ├── router/
    │   └── index.js
    ├── composables/       ← 响应式数据逻辑
    │   ├── useAuth.js        ← 登录状态 + scan 轮询
    │   ├── useDashboard.js
    │   ├── useArticles.js    ← 浏览: 订阅源/文章列表/详情/star
    │   ├── useRss.js         ← 订阅搜索/管理/导出
    │   ├── useIngestion.js
    │   ├── useLogs.js
    │   └── useBackup.js
    ├── components/        ← 可复用 UI 组件
    │   ├── Sidebar.vue
    │   ├── TopBar.vue
    │   ├── StatCard.vue
    │   ├── DataTable.vue
    │   ├── Pagination.vue
    │   ├── StatusBadge.vue
    │   ├── SearchInput.vue
    │   ├── SkeletonLoader.vue  ← 骨架屏
    │   ├── EmptyState.vue      ← 空状态插画+文案
    │   ├── Toast.vue           ← 全局 toast 通知
    │   └── ConfirmModal.vue    ← 确认弹窗
    └── views/             ← 路由级页面（薄壳，组合组件）
        ├── DashboardView.vue
        ├── BrowseView.vue
        ├── RssManageView.vue
        ├── IngestionView.vue
        ├── LogsView.vue
        ├── BackupView.vue
        ├── SettingsView.vue
        └── LoginView.vue
```

构建命令：
```bash
cd frontend && npm run build   # 产出到 ../static/
# FastAPI 已有的 StaticFiles mount 即可 serve SPA
```

## 设计系统

### 字体

对于微信公众号阅读器，字体是区分气质的第一要素。文章内容使用衬线体营造纸媒阅读感，UI 使用无衬线保持清晰。

| 用途 | 字体 | 来源 |
|------|------|------|
| 文章正文 | **LXGW WenKai** (霞鹜文楷) | Google Fonts CDN |
| 备选正文字体 | **Noto Serif SC** | Google Fonts CDN |
| UI 标题/导航 | **PingFang SC** → **HarmonyOS Sans** → `sans-serif` | 系统内置 |
| 数据/代码/日志 | **JetBrains Mono** | Google Fonts CDN |

```css
@import url('https://fonts.googleapis.com/css2?family=LXGW+WenKai&family=JetBrains+Mono&display=swap');

:root {
  --font-body: 'LXGW WenKai', 'Noto Serif SC', 'STSong', 'SimSun', serif;
  --font-ui: 'PingFang SC', 'HarmonyOS Sans', 'Microsoft YaHei', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;
}
```

### 配色（暖白基础 + 深青强调）

保留 Notion 的灰白基础，强调色从标准蓝换为深青——在灰白背景上更安静，和阅读场景气质更匹配。

```css
:root {
  /* 基础色 */
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --bg-reading: #fefefe;       /* 阅读区暖白纸色 */
  --bg-hover: #f1f3f5;
  --border-light: #e9ecef;
  --border-base: #dee2e6;
  --text-primary: #212529;
  --text-secondary: #495057;
  --text-muted: #868e96;

  /* 强调色 — 深青 */
  --accent: #0c8599;
  --accent-light: #e3fafc;
  --accent-hover: #0b7285;

  /* 语义色 — 降低饱和度，保持功能清晰 */
  --success: #2f9e44;
  --warning: #e07b39;
  --error: #c92a2a;

  /* 间距/圆角/阴影 */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.06);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.08);
}
```

### 动效

所有动画用 CSS transition/transition + Vue `<Transition>`，不引入外部动画库。

| 场景 | 动效 | 实现 |
|------|------|------|
| 路由切换 | 内容区淡入 + 微上移 (8px) | `<Transition name="fade-slide">` |
| 看板卡片入场 | 错位渐入 (stagger reveal) | `animation-delay: calc(var(--i) * 80ms)` |
| 侧边栏折叠 | 宽度过渡 + 文字淡出 | `transition: width 250ms ease` |
| 数据加载中 | 微光骨架屏 (shimmer skeleton) | CSS linear-gradient infinite |
| 文章切换 | 内容区淡入，不退位 | `<Transition mode="out-in">` |
| Hover 反馈 | 卡片微上浮 + 阴影加深 | `transition: transform 150ms, box-shadow 150ms` |
| 数量变化 | 数字缩放弹跳 | `transition: transform 200ms cubic-bezier(0.34,1.56,0.64,1)` |

路由过渡 CSS：
```css
.fade-slide-enter-active { transition: all 0.25s ease-out; }
.fade-slide-leave-active { transition: all 0.15s ease-in; }
.fade-slide-enter-from { opacity: 0; transform: translateY(8px); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-4px); }
```

### 视觉层次与氛围

- **侧边栏分组**：每组标签处有一条 2px 微妙的彩色顶线，替代纯文字分隔
- **看板卡片"在线"状态**：卡片左边框 3px 绿条 + 顶部微绿底色渐变，不仅靠一个点
- **文章阅读区**：白色背景 + 衬线字体 + 正文 `max-width: 680px` 居中，两侧留白——模拟纸张阅读感
- **空状态**：精致 SVG 插画 + 一行文案，不使用纯文字提示

### 响应式断点策略

| 断点 | 布局 | 侧边栏 | 文章浏览 |
|------|------|--------|---------|
| >= 1280px | 完整三栏 | 220px 正常显示 | 三栏完整 |
| 1024–1279px | 两栏 | 折叠至 56px 仅图标 | 隐藏第一栏，顶栏下拉选公众号 |
| 768–1023px | 单栏 + 底栏 | 隐藏，底部 TabBar | 列表 + 点击进详情 |
| < 768px | 单栏移动 | 汉堡菜单 | 列表 + 点击进详情 |

## 前端路由表

| 路径 | View | 说明 |
|------|------|------|
| `/` | DashboardView | 首页数据看板 |
| `/browse` | BrowseView | 文章三栏浏览 |
| `/rss` | RssManageView | RSS 订阅管理 |
| `/ingestion` | IngestionView | 入库管理 |
| `/logs` | LogsView | 系统日志 |
| `/backup` | BackupView | 备份管理 |
| `/settings` | SettingsView | 设置（回落/黑名单/分类/历史） |
| `/settings/:tab` | SettingsView | 设置子页面（深层链接） |
| `/login` | LoginView | 扫码登录 |
| `/verify` | VerifyView | 验证码引导 |

`vue-router` hash 模式，URL 格式为 `/#/browse`。

## package.json 依赖

```json
{
  "name": "wq-cli-frontend",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5",
    "vue-router": "^4.5",
    "dompurify": "^3.2"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2",
    "vite": "^6.3"
  }
}
```

`vue` / `vue-router` / `dompurify` 打包进产物，Google Fonts 在 `index.html` 中 `<link>` 引用。构建产物体积：Vue ~50KB gzip + router ~10KB + DOMPurify ~17KB + 业务代码 —— 总计 ~100KB gzip。

## vite.config.js

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
  build: {
    outDir: resolve(__dirname, '../static'),
    emptyOutDir: false,  // 保留 qrcodes/ 等已有静态文件
  },
})
```

`emptyOutDir: false` —— Vite 构建时不删除 `static/` 下已有的 `qrcodes/` 等文件，只覆盖 SPA 产物。

## 全局状态设计（provide/inject）

不需要 Pinia，用 `provide/inject` 覆盖当前规模：

```js
// main.js 顶层 provide
provide('sidebarCollapsed', readonly(sidebar))       // 侧边栏折叠态
provide('toggleSidebar', toggleSidebar)
provide('currentUser', readonly(currentUser))         // 登录状态 + 账号信息
provide('refreshUser', refreshUser)
```

路由间切换时各 view 自己 `inject` 获取，不跨层传递。

## 数据流设计

每个路由级 View 遵循相同模式：

```vue
<!-- views/DashboardView.vue -->
<script setup>
import { useDashboard } from '@/composables/useDashboard'
import StatCard from '@/components/StatCard.vue'
import DataTable from '@/components/DataTable.vue'

const { stats, loading, error, refresh } = useDashboard()
</script>
```

- **composable** 持有 `ref`/`computed` + 异步请求，返回 `readonly` 状态 + 操作函数
- **组件** 只接收 props 和 emit events，不自己发 HTTP 请求
- 纯工具函数（日期格式化、链接截断）放在 `src/utils/` 目录，不使用 composable

## 组件树（路由级拆分明细）

### App.vue

```
App (布局壳)
├── TopBar          ← 折叠按钮 + 登录状态 + 快捷操作
├── Sidebar         ← 分组导航 + 当前路由高亮 + 订阅数/更新数
└── <router-view>
```

### DashboardView

```
DashboardView (容器——调用 useDashboard)
├── div.stats-grid
│   ├── StatCard (在线状态)
│   ├── StatCard (累计入库)
│   ├── StatCard (今日入库: 成功/失败/成功率)
│   ├── StatCard (已订阅公众号)
│   ├── StatCard (待处理队列)
│   └── StatCard (今日有更新)
└── DataTable (最近失败列表)
```

### BrowseView

```
BrowseView (容器——路由级，组合三栏)
├── SourceSidebar     ← 分类 + 公众号列表，折叠/展开
│   每个条目: icon + name + count
├── ArticleList       ← 文章列表 + SearchInput + Pagination
│   每个条目: title(2行) + nickname + pub_date
└── ArticleReader     ← 文章详情
    ├── ArticleToolbar ← 星标/重抓/原文/导出PDF/导出MD
    └── articleBody    ← DOMPurify 净化后 v-html 渲染
```

**BrowseView 详细样式指引**（核心页面，投入最高）：

第一栏 SourceSidebar（220px → 折叠 56px）：
- 顶部标题"订阅源" + 文章计数 badge
- "全部文章" 置顶，加粗，默认选中
- 分类组标签：小号大写 + 2px 顶线，和下方公众号用 2px 微间距分隔
- 悬停条目：浅青背景 `--accent-light`，左侧 2px `--accent` 竖线指示器
- 选中条目：青背景 + 竖线，选中项右侧隐藏计数 badge（减少视觉干扰）
- 公众号头像：20px 圆形，未加载时显示首字 placeholder

第二栏 ArticleList（320px）：
- 顶部公众号名 + 文章总数，下方搜索框
- 文章条目：两行标题截断 + 来源名(灰色) + 时间(灰色)，间距充裕
- 选中条目：背景 `--accent-light`，左侧 3px `--accent` 竖条，标题变 `--accent`
- 条目间用极浅分隔线 `--border-light`
- 底部分页栏：`← 上一页` `页码/总页数` `下一页 →`，居中
- 滚动条定制：宽 6px，半透明 thumb，hover 变深

第三栏 ArticleReader：
- 标题区：大号衬线体 + 元信息行（头像+公众号名+日期+原文链接+"已抓取"标签）
- 工具栏右上角：6 个图标按钮（32×32，悬停变色），用分隔线分组
- 正文区：白色背景 + 衬线体 + `max-width: 680px` 水平居中 + `line-height: 1.8` + 字号 `17px`
- 正文内图片：`max-width: 100%` + `border-radius: 8px`
- 滚动条定制同第二栏

### RssManageView

```
RssManageView
├── 状态栏 (轮询器运行 dot + "立即轮询"按钮 + 聚合 RSS 链接)
├── 搜索区 (SearchInput + 搜索按钮 → 结果下拉列表)
├── 订阅列表卡片 (导出下拉: CSV/OPML)
│   每个: 头像 + 名称 + 文章数 + 最后轮询时间 + 分类标签
│   操作: 分类选择下拉 + 复制 RSS + 历史 RSS + 取消订阅
└── API:
    GET /api/rss/status, GET /api/rss/subscriptions,
    GET /api/public/searchbiz?query=,
    POST /api/rss/subscribe,
    DELETE /api/rss/subscribe/{fakeid},
    POST /api/rss/poll,
    PUT /api/admin/subscriptions/{fakeid}/category,
    GET /api/rss/export?format=csv|opml,
    GET /api/admin/categories,
    GET /api/rss/category/{id} (分类聚合 RSS 链接)
```

### IngestionView

```
IngestionView
├── 统计行 (StatCard × n)
├── 筛选工具栏 (SearchInput + 状态/渠道下拉)
├── DataTable (入库记录表格)
└── 重试区 (输入框 + 按钮)
```

### LogsView

```
LogsView
├── 筛选工具栏 (SearchInput + 级别/模块下拉 + 自动刷新开关)
└── DataTable (日志表格)
```

### BackupView

```
BackupView
├── 导出区 (全量/仅数据/仅设置 按钮)
├── 导入拖拽区
└── 历史备份列表
```

### SettingsView

```
SettingsView (Tab 切换，vue-router param :tab)
├── TabBar (回落配置 / 黑名单 / 分类管理 / 历史获取)
└── 对应内容区
    回落配置:
      - 三级回落链路说明（L1 CF Worker / L2 SOCKS5 / L3 直连）
      - 两个 textarea（Worker URL 列表 / 代理列表）
      - 保存配置 / 测试节点 / 恢复默认 三个按钮
      - 节点测试结果表格（等级/节点/状态/延迟/错误）
      - API: GET/PUT /api/admin/fetch-config, GET /api/admin/fetch-config/test,
        POST /api/admin/fetch-config/reset
    黑名单:
      - 添加区：FakeID 输入 + 公众号名称 + 添加按钮
      - 表格列：公众号 / FakeID / 原因 / 触发次数 / 状态 / 时间 / 操作
      - 操作：移除(active) / 删除(inactive)
      - API: GET/POST /api/admin/blacklist, DELETE /api/admin/blacklist/{fakeid},
        DELETE /api/admin/blacklist/record/{id}
    分类管理:
      - 创建区：名称 + 描述 + 6 色选择器 + 创建按钮
      - 分类卡片列表：色标 / 名称 / 描述 / 订阅数 / RSS URL / 复制RSS / 删除
      - API: GET/POST /api/admin/categories, DELETE /api/admin/categories/{id}
    历史获取:
      - 左侧订阅列表 / 右侧已选 + 数量输入 + "开始获取"按钮
      - 注意事项提示 + 结果展示
      - API: GET /api/rss/subscriptions, POST /api/admin/history/fetch
```

### LoginView

```
LoginView
└── 居中卡片: QR 码 + 状态消息 + 刷新按钮
```

登录流程状态机（保持现有逻辑不变，用 Vue 实现）：
```
初始化 → GET /api/login/session/{sessionid}
     ↓
显示二维码 → GET /api/login/getqrcode (返回图片)
     ↓
开始轮询 → GET /api/login/scan (每 2s)
     ↓
  status=1(已扫码) → POST /api/login/bizlogin → 完成 → 跳转看板
  status=4/6(等待) → 继续轮询
  status=2(过期) → 提示刷新二维码
  status=3(失败) → 显示错误，可重试
```
页面可见性变化时暂停/恢复轮询，切换回页面时重新检查状态。

### VerifyView

验证码处理引导页（独立路由 `/verify`，从 SettingsView 中也可访问）：
- 文章 URL 输入框 + "在新窗口打开"按钮
- 操作步骤图文引导（粘贴链接 → 打开页面 → 完成验证 → 等待恢复）
- 提示文案："验证通过后 Cookie 自动更新，建议等待 5-10 分钟"
- 不调用任何 API，纯客户端引导

## XSS 防护

所有文章 HTML 内容在 `v-html` 渲染前必须通过 DOMPurify 净化：

```js
// composables/useArticles.js
import DOMPurify from 'dompurify'

function sanitize(html) {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'a', 'img', 'h1', 'h2', 'h3',
      'h4', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'span', 'div',
      'table', 'thead', 'tbody', 'tr', 'td', 'th', 'section', 'figure',
      'figcaption', 'video', 'source'],
    ALLOWED_ATTR: ['href', 'src', 'alt', 'class', 'id', 'width', 'height',
      'style', 'data-*'],
  })
}
```

## 导航结构

### 侧边栏（220px 宽，可折叠至 56px 仅图标）

**概览**
- 数据看板

**内容**
- 文章浏览
- RSS 订阅

**管理**
- 入库管理
- 系统日志
- 备份管理
- 设置（回落配置、黑名单、分类管理、历史获取合并到此页）

### 顶部栏

- 侧边栏折叠按钮
- 登录状态指示（绿点 + 账号名）
- 刷新/登出快捷操作

## 图片本地化

### 流程

```
抓取文章 → 立即可读（图走 /api/image 代理，现有逻辑不变）
     ↓
  图片 URL 入队 → image_download_queue 表
     ↓
  后台 worker 逐一下载到 data/images/{article_id}/
     ↓
  全部下载完成 → 一次性替换 HTML 中图片路径为本地
     ↓
  标记 article.images_localized = 1
```

### 存储

```
data/images/{article_id}/img_001.jpg
```

### image_download_queue 表

```sql
CREATE TABLE image_download_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    image_url TEXT NOT NULL,
    local_path TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    attempt INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);
```

### articles 表新增字段

```sql
ALTER TABLE articles ADD COLUMN starred INTEGER NOT NULL DEFAULT 0;
ALTER TABLE articles ADD COLUMN images_localized INTEGER NOT NULL DEFAULT 0;
```

### 新增/改动 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/admin/dashboard` | GET | 看板数据聚合 |
| `/api/browse/article/{id}/star` | PATCH | 切换星标 |
| `/api/browse/article/{id}/refetch` | POST | 重新抓取 |
| `/api/browse/article/{id}/export` | GET | 导出 MD + 图片 zip |
| `/api/admin/image-queue` | GET | 图片下载队列状态 |
| `/api/admin/image-queue/retry` | POST | 重试失败图片下载 |

### 现有 API 兼容（无需改动，前端直接对接）

以下所有现有 API 保持不变，Vue 前端直接对接。已在各 View 中标注。

| API | 用途 | 对接 View |
|-----|------|-----------|
| `GET /api/admin/status` | 登录状态 | TopBar / DashboardView |
| `POST /api/admin/logout` | 退出登录 | TopBar |
| `GET /api/admin/fetch-config` | 回落配置读 | SettingsView |
| `PUT /api/admin/fetch-config` | 回落配置写 | SettingsView |
| `GET /api/admin/fetch-config/test` | 测试节点 | SettingsView |
| `POST /api/admin/fetch-config/reset` | 重置配置 | SettingsView |
| `GET /api/admin/blacklist` | 黑名单列表 | SettingsView |
| `POST /api/admin/blacklist` | 添加黑名单 | SettingsView |
| `DELETE /api/admin/blacklist/{fakeid}` | 移除黑名单 | SettingsView |
| `DELETE /api/admin/blacklist/record/{id}` | 删除记录 | SettingsView |
| `GET /api/admin/categories` | 分类列表 | SettingsView / RssManageView |
| `POST /api/admin/categories` | 创建分类 | SettingsView |
| `DELETE /api/admin/categories/{id}` | 删除分类 | SettingsView |
| `GET /api/admin/history/fetch` → `POST` | 历史文章获取 | SettingsView |
| `GET /api/rss/subscriptions` | 订阅列表 | RssManageView |
| `GET /api/public/searchbiz` | 搜索公众号 | RssManageView |
| `POST /api/rss/subscribe` | 添加订阅 | RssManageView |
| `DELETE /api/rss/subscribe/{fakeid}` | 取消订阅 | RssManageView |
| `POST /api/rss/poll` | 手动轮询 | RssManageView |
| `GET /api/rss/status` | 轮询器状态 | RssManageView |
| `GET /api/rss/export` | 导出订阅 | RssManageView |
| `PUT /api/admin/subscriptions/{fakeid}/category` | 设置分类 | RssManageView |
| `GET /api/browse/subscriptions` | 有文章订阅 | BrowseView |
| `GET /api/browse/articles` | 文章列表 | BrowseView |
| `GET /api/browse/article/{id}` | 文章详情 | BrowseView |
| `GET /api/admin/ingestion/stats` | 入库统计 | IngestionView |
| `GET /api/admin/ingestion` | 入库查询 | IngestionView |
| `POST /api/admin/ingestion/retry` | 重试入库 | IngestionView |
| `GET /api/admin/backup/list` | 备份列表 | BackupView |
| `POST /api/admin/backup/export` | 导出备份 | BackupView |
| `POST /api/admin/backup/import/upload` | 导入备份 | BackupView |
| `DELETE /api/admin/backup/delete` | 删除备份 | BackupView |
| `GET /api/admin/logs/modules` | 模块列表 | LogsView |
| `GET /api/admin/logs` | 日志查询 | LogsView |
| `POST /api/admin/logs/cleanup` | 清理日志 | LogsView |
| `POST /api/login/session/{sessionid}` | 初始化登录 | LoginView |
| `GET /api/login/getqrcode` | 二维码图片 | LoginView |
| `GET /api/login/scan` | 扫码状态轮询 | LoginView |
| `POST /api/login/bizlogin` | 完成登录 | LoginView |
| `POST /api/article` | 测试获取文章 | admin.html 接口测试 (并入 DashboardView 或 SettingsView) |

### 后端文件改动

| 文件 | 改动 |
|------|------|
| `utils/ingestion_store.py` | 新增 `get_dashboard_stats()` |
| `utils/rss_store.py` | 新增 `toggle_star()`、图片队列操作 |
| `utils/image_downloader.py` | **新增** — 后台图片下载 worker |
| `routes/browse.py` | 新增 star/refetch/export 端点 |
| `routes/ingestion.py` | 新增 `/admin/dashboard` 端点 |
| `routes/admin.py` | 新增 image-queue 端点 |
| `app.py` | 启动 image_downloader worker + SPA fallback 路由 |

## SPA 路由 fallback（后端）

```python
# app.py — 所有非 /api/ 路径返回 index.html（vue-router 处理）
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)
    return FileResponse(static_dir / "index.html")
```

## 不保留的旧文件

重构完成后删除所有旧 HTML 页面：`admin.html`, `browse.html`, `rss.html`, `logs.html`, `ingestion.html`, `backup.html`, `blacklist.html`, `categories.html`, `history.html`, `proxy-config.html`, `verify.html`, `login.html`。

## 全局 Toast 通知系统

所有 API 操作结果通过 Toast 组件统一反馈，不复用旧页面的 `alert()` 或内联消息：

- `Toast.vue` — 使用 Vue `<TransitionGroup>` 叠加显示多条
- 全局 provide：`showToast(message, type)` —— type: `success` / `error` / `warning` / `info`
- 自动消失 3s，error 类型手动关闭
- 位置：右下角，堆叠排列

## 错误处理策略

- 所有 fetch 调用通过 composable 统一 try/catch
- HTTP 错误（4xx/5xx）→ Toast 显示友好消息
- 登录过期（凭证无效）→ 自动跳转 `/login`，保留原意图路由
- 网络错误 → Toast "网络异常，请检查连接"
- 加载中状态 → 骨架屏（首次）/ 半透明遮罩（刷新）

## 实施顺序

按依赖关系和风险分级：

| 阶段 | 任务 | 依赖 | 风险 |
|------|------|------|------|
| **0. 基础设施** | Vite 项目初始化、Vue Router、CSS 变量、App.vue 壳 | 无 | 低 |
| **1. 后端 API** | dashboard/stare/refetch/export 端点 + image_download_queue 表 | 阶段 0 | 中 |
| **2. 核心页面** | BrowseView（三栏）+ LoginView（扫码） | 阶段 0,1 | 高 |
| **3. 看板** | DashboardView + StatCard + SkeletonLoader | 阶段 1 | 低 |
| **4. 管理页面** | RssManageView / IngestionView / LogsView / BackupView | 阶段 0 | 中 |
| **5. 设置页** | SettingsView（回落/黑名单/分类/历史 + VerifyView） | 阶段 0 | 低 |
| **6. 打磨收尾** | 图片本地化 worker、动效调优、响应式测试、删除旧文件 | 阶段 2-5 | 低 |

优先级理由：
- BrowseView 投入最高、用户价值最大、最体现三栏设计——先做以验证设计落地
- LoginView 必须紧跟——没有登录其他页面无法工作
- 管理页面批量迁移，大部分是现有逻辑平移

## 爆炸半径控制

每阶段完成后可独立验证：
- **阶段 0**：`npm run dev` 见到侧边栏 + 顶栏 + 空路由区 ✅
- **阶段 1**：`curl /api/admin/dashboard` 返回正确数据 ✅
- **阶段 2**：扫码登录 → 浏览文章 → 三栏交互正常 ✅
- **阶段 3-5**：每个 View 完成即切换到对应路由验证
- **阶段 6**：全链路回归 + 删除旧文件

现有功能在整个过程中持续可用（旧 HTML 保留不动，新前端在 `frontend/` 中独立开发，`vite build` 产出一组新文件到 `static/`）。只有在阶段 6 确认所有功能迁移完毕后，才删除旧文件并修改 `app.py` SPA fallback 路由。

## app.py 改动的爆炸半径

| 改动 | 影响 | 安全措施 |
|------|------|---------|
| 新增 `image_downloader` 启动 | `lifespan` 中多一个后台 task | worker 异常不影响主服务 |
| 新增 `/api/admin/dashboard` 等端点 | 新增路由文件/函数 | 只读查询，不影响任何现有路由 |
| `articles` 表新增字段 | SQLite schema 变更 | ALTER TABLE ADD COLUMN with DEFAULT，对现有行透明 |
| SPA fallback 路由 | 所有非 `/api/` 路径 | 放在所有路由注册 **之后**，FastAPI 按注册顺序匹配 |
| `static/` 新增 Vite 产物 | 文件数量增加 | `emptyOutDir: false` 不删已有文件
