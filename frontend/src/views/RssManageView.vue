<script setup>
import { onMounted, inject, ref, computed } from 'vue'
import { useRss } from '@/composables/useRss'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import SubscribeModal from '@/components/SubscribeModal.vue'
import CategoryPickerModal from '@/components/CategoryPickerModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import { Rss, History, Tag, Trash2, Plus, RefreshCw, Copy } from 'lucide-vue-next'

const toast = inject('toast')
const baseUrl = window.location.origin

const {
  subscriptions, loading,
  pollerStatus, loadSubscriptions, loadStatus,
  unsubscribe, setCategory, triggerPoll, exportUrl,
} = useRss()

// ── categories ──────────────────────────────────────
const categories = ref([])
async function loadCategories() {
  const res = await fetch('/api/admin/categories')
  const data = await res.json()
  if (data.categories) categories.value = data.categories
}

// ── modals state ────────────────────────────────────
const showSubscribe = ref(false)
const categoryTarget = ref(null)
const confirmTarget = ref(null)

onMounted(() => { loadSubscriptions(); loadStatus(); loadCategories() })

// ── computed ────────────────────────────────────────
const subscriptionIdList = computed(() => subscriptions.value.map(s => s.fakeid))

// ── actions ─────────────────────────────────────────
async function handlePoll() {
  const r = await triggerPoll()
  toast[r.success ? 'success' : 'error'](r.success ? '轮询已触发' : (r.detail || '触发失败'))
}

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function copyLink(url, label) {
  const full = baseUrl + url
  const doCopy = () => {
    const el = document.createElement('textarea')
    el.value = full; el.style.position = 'fixed'; el.style.left = '-9999px'
    document.body.appendChild(el)
    el.select(); document.execCommand('copy'); document.body.removeChild(el)
    toast.success(label + ' 已复制')
  }
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(full).then(() => toast.success(label + ' 已复制')).catch(doCopy)
  } else {
    doCopy()
  }
}

// ── category colors (前端映射) ───────────────────────
const catColorMap = { blue: '#3b82f6', green: '#22c55e', red: '#ef4444', purple: '#a855f7', yellow: '#eab308', teal: '#0d9488', orange: '#f97316', pink: '#ec4899' }
const catBgMap = { blue: '#eff6ff', green: '#f0fdf4', red: '#fef2f2', purple: '#f5f3ff', yellow: '#fefce8', teal: '#f0fdfa', orange: '#fff7ed', pink: '#fdf2f8' }

function catStyle(cat) {
  if (!cat?.category_name) return { background: '#f3f4f6', color: '#9ca3af' }
  const color = cat.category_color || 'gray'
  return { background: catBgMap[color] || '#f3f4f6', color: catColorMap[color] || '#6b7280' }
}

// ── category picker ─────────────────────────────────
function openCategory(fakeid) { categoryTarget.value = fakeid }
async function handleCategorySelect(categoryId) {
  if (!categoryTarget.value) return
  await setCategory(categoryTarget.value, categoryId)
  await loadSubscriptions()
  categoryTarget.value = null
}

// ── unsubscribe confirm ─────────────────────────────
const confirmName = computed(() => {
  if (!confirmTarget.value) return ''
  const s = subscriptions.value.find(x => x.fakeid === confirmTarget.value)
  return s?.nickname || s?.alias || confirmTarget.value
})

function openConfirm(fakeid) { confirmTarget.value = fakeid }
async function handleConfirmUnsubscribe() {
  if (!confirmTarget.value) return
  const r = await unsubscribe(confirmTarget.value)
  toast[r.success ? 'success' : 'error'](r.success ? '已取消订阅' : (r.detail || '取消失败'))
  confirmTarget.value = null
}

// ── subscribe success ───────────────────────────────
function onSubscribed() {
  toast.success('订阅成功')
  loadSubscriptions()
}

// ── single poll ──────────────────────────────────────
const pollingSet = ref(new Set())

async function handleSinglePoll(fakeid) {
  if (pollingSet.value.has(fakeid)) return
  pollingSet.value = new Set([...pollingSet.value, fakeid])
  try {
    const res = await fetch(`/api/rss/poll/${fakeid}`, { method: 'POST' })
    const data = await res.json()
    if (res.status === 429) {
      toast.warning(data.detail || '为避免风险，请勿频繁轮询')
    } else if (data.success) {
      toast.success(data.message || '已加入轮询队列')
    } else {
      toast.error(data.message || '轮询失败')
    }
    await loadSubscriptions()
  } catch (e) {
    toast.error('网络错误: ' + e.message)
  } finally {
    pollingSet.value = new Set([...pollingSet.value].filter(id => id !== fakeid))
  }
}

// ── column layout (dynamic grid, will be enhanced in Task 6) ──
const COL_KEYS = ['name','all','ingested','non_ingested','poll','category','actions']
const DEFAULT_COLS = { name: 1.5, all: 0.4, ingested: 0.4, non_ingested: 0.4, poll: 0.9, category: 0.8, actions: 1.3 }

function getGridStyle() {
  return COL_KEYS.map(k => (DEFAULT_COLS[k] || 0.4) + 'fr').join(' ')
}

// ── helpers ─────────────────────────────────────────
function getInitial(name) { return (name || '?').charAt(0) }
function avatarBg(i) {
  const colors = ['#dbeafe','#fce7f3','#fef3c7','#dcfce7','#ede9fe','#fee2e2']
  const txts = ['#2563eb','#be185d','#b45309','#16a34a','#7c3aed','#dc2626']
  return { bg: colors[i % colors.length], color: txts[i % txts.length] }
}
</script>

<template>
  <div>
    <!-- Page title -->
    <Teleport to="#topbar-title">
      <h1 class="text-[18px] font-bold tracking-[-0.01em]" style="color: var(--text-primary); font-family: var(--font-display);">公众号订阅</h1>
    </Teleport>

    <!-- Status bar -->
    <div class="flex items-center justify-between px-4 py-3 rounded-[var(--radius-md)] mb-4 gap-3 flex-wrap"
      style="background: var(--bg-primary); border: 1px solid var(--border-light); box-shadow: var(--shadow-xs);">
      <div class="flex items-center gap-3">
        <span class="flex items-center gap-1.5 text-[12px]" style="color: var(--text-secondary);">
          <span class="w-[7px] h-[7px] rounded-full" :style="pollerStatus.running ? 'background:var(--success);box-shadow:0 0 6px rgba(59,140,94,0.4)' : 'background:var(--text-muted)'"></span>
          {{ pollerStatus.running ? '轮询器运行中' : '轮询器已停止' }}
        </span>
        <span v-if="pollerStatus.next_poll" class="text-[11px]" style="color: var(--text-muted);">下次: {{ formatTime(pollerStatus.next_poll) }}</span>
      </div>

      <div v-if="pollerStatus.consecutive_failures > 0"
        class="text-[11px] px-2.5 py-1 rounded-full text-xs"
        :style="pollerStatus.consecutive_failures >= 3
          ? 'background: var(--error-bg); color: var(--error);'
          : 'background: var(--warning-bg); color: var(--warning);'">
        最近 {{ pollerStatus.consecutive_failures }} 次轮询失败
        <span v-if="pollerStatus.last_fail_msg" class="opacity-70">: {{ pollerStatus.last_fail_msg }}</span>
      </div>

      <div class="flex items-center gap-2">
        <button class="btn btn-sm" @click="copyLink('/api/rss/all', '聚合 RSS')">
          <Copy :size="12" /> 复制聚合 RSS
        </button>
        <button class="btn btn-primary btn-sm" @click="handlePoll">
          <RefreshCw :size="12" /> 立即轮询
        </button>
      </div>
    </div>

    <!-- Header + add button -->
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-[14px] font-semibold" style="color: var(--text-primary);">
        已订阅 ({{ subscriptions.length }})
      </h3>
      <button class="btn btn-primary btn-sm" @click="showSubscribe = true">
        <Plus :size="14" /> 添加订阅
      </button>
    </div>

    <!-- Loading / empty -->
    <SkeletonLoader v-if="loading" :lines="5" />
    <EmptyState v-else-if="!subscriptions.length" text="暂无订阅，点击「添加订阅」开始" />

    <!-- Desktop table (>= 768px) -->
    <div v-else
      class="hidden md:block rounded-[var(--radius-md)] overflow-hidden"
      style="background: var(--bg-primary); border: 1px solid var(--border-light); box-shadow: var(--shadow-xs);">

      <!-- Header row -->
      <div class="grid gap-3 px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.06em]"
        :style="{ gridTemplateColumns: getGridStyle(), background: 'var(--bg-secondary)', color: 'var(--text-muted)', borderBottom: '2px solid var(--border-light)' }">
        <span>公众号</span>
        <span class="text-center">全部</span>
        <span class="text-center">已入库</span>
        <span class="text-center">待入库</span>
        <span class="text-center">最后轮询</span>
        <span class="text-center">分类</span>
        <span class="text-center">操作</span>
      </div>

      <!-- Rows -->
      <div v-for="(s, i) in subscriptions" :key="s.fakeid"
        class="grid gap-3 px-4 py-3 items-center text-[12px] transition-colors duration-150"
        :style="{ gridTemplateColumns: getGridStyle(), borderBottom: '1px solid var(--border-light)' }"
        @mouseenter="(e) => e.currentTarget.style.background = 'var(--bg-hover)'"
        @mouseleave="(e) => e.currentTarget.style.background = ''">

        <!-- 公众号 — 左对齐 -->
        <div class="flex items-center gap-2.5 min-w-0" style="text-align:left;">
          <img v-if="s.head_img" :src="s.head_img" class="w-7 h-7 rounded-full shrink-0 object-cover" />
          <div v-else class="w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-[12px] font-semibold"
            :style="{ background: avatarBg(i).bg, color: avatarBg(i).color }">{{ getInitial(s.nickname) }}</div>
          <div class="min-w-0">
            <div class="font-semibold truncate leading-snug" style="color: var(--text-primary);">{{ s.nickname || s.fakeid }}</div>
            <div v-if="s.alias" class="text-[10px] truncate leading-snug" style="color: var(--text-muted);">{{ s.alias }}</div>
          </div>
        </div>

        <!-- 全部 -->
        <span class="font-semibold text-center tabular-nums" style="color: var(--text-primary);">{{ s.article_count || 0 }}</span>

        <!-- 已入库 -->
        <span class="font-semibold text-center tabular-nums" style="color: var(--success);">{{ s.ingested_count != null ? s.ingested_count : s.article_count }}</span>

        <!-- 待入库 -->
        <span class="font-semibold text-center tabular-nums" :style="{ color: (s.non_ingested_count || 0) > 0 ? 'var(--warning)' : 'var(--text-muted)' }">{{ s.non_ingested_count || 0 }}</span>

        <!-- 最后轮询 -->
        <span style="color: var(--text-muted); text-align:center;" class="tabular-nums">{{ formatTime(s.last_poll) }}</span>

        <!-- 分类 -->
        <div style="text-align:center;">
          <span v-if="s.category_name" class="badge" :style="catStyle(s)">{{ s.category_name }}</span>
          <span v-else class="badge" style="background: #f3f4f6; color: #9ca3af;">未分类</span>
        </div>

        <!-- 操作按钮 — 居中 -->
        <div class="flex gap-1.5 justify-center">
          <button class="btn btn-xs" @click="handleSinglePoll(s.fakeid)" title="手动刷新" :disabled="pollingSet.has(s.fakeid)">
            <RefreshCw :size="11" :class="{ 'animate-spin': pollingSet.has(s.fakeid) }" /> 刷新
          </button>
          <button class="btn btn-xs" @click="copyLink('/api/rss/' + s.fakeid, 'RSS 链接')" title="复制新文章 RSS">
            <Rss :size="11" /> RSS
          </button>
          <button class="btn btn-xs" @click="copyLink('/api/rss/' + s.fakeid + '/history', '历史 RSS')" title="复制历史文章 RSS">
            <History :size="11" /> 历史
          </button>
          <button class="btn btn-xs" @click="openCategory(s.fakeid)" title="更改分类">
            <Tag :size="11" /> 分类
          </button>
          <button class="btn btn-xs" style="color:var(--error);border-color:rgba(189,60,60,0.25);" @click="openConfirm(s.fakeid)" title="取消订阅">
            <Trash2 :size="11" /> 取消
          </button>
        </div>
      </div>
    </div>

    <!-- Mobile cards (< 768px) -->
    <div v-if="!loading && subscriptions.length" class="md:hidden flex flex-col gap-2.5">
      <div v-for="(s, i) in subscriptions" :key="s.fakeid" class="card p-4">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2.5 min-w-0">
            <img v-if="s.head_img" :src="s.head_img" class="w-7 h-7 rounded-full shrink-0 object-cover" />
            <div v-else class="w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-[12px] font-semibold"
              :style="{ background: avatarBg(i).bg, color: avatarBg(i).color }">{{ getInitial(s.nickname) }}</div>
            <div class="min-w-0">
              <div class="font-semibold text-[13px] leading-snug truncate" style="color: var(--text-primary);">{{ s.nickname }}</div>
              <div v-if="s.alias" class="text-[10px] leading-snug" style="color: var(--text-muted);">{{ s.alias }}</div>
            </div>
          </div>
          <span v-if="s.category_name" class="badge shrink-0" :style="catStyle(s)">{{ s.category_name }}</span>
          <span v-else class="badge shrink-0" style="background: #f3f4f6; color: #9ca3af;">未分类</span>
        </div>

        <div class="flex items-center gap-4 text-[11px] mb-3" style="color: var(--text-muted);">
          <span>全部: <b style="color: var(--text-primary);">{{ s.article_count || 0 }}</b></span>
          <span>已入库: <b style="color: var(--success);">{{ s.ingested_count != null ? s.ingested_count : s.article_count }}</b></span>
          <span>待入库: <b :style="{ color: (s.non_ingested_count || 0) > 0 ? 'var(--warning)' : 'var(--text-muted)' }">{{ s.non_ingested_count || 0 }}</b></span>
          <span>轮询: {{ formatTime(s.last_poll) }}</span>
        </div>

        <div class="flex gap-1.5 flex-wrap">
          <button class="btn btn-xs flex-1" @click="handleSinglePoll(s.fakeid)" :disabled="pollingSet.has(s.fakeid)"><RefreshCw :size="10" :class="{ 'animate-spin': pollingSet.has(s.fakeid) }" /> 刷新</button>
          <button class="btn btn-xs flex-1" @click="copyLink('/api/rss/' + s.fakeid, 'RSS 链接')"><Rss :size="10" /> RSS</button>
          <button class="btn btn-xs flex-1" @click="copyLink('/api/rss/' + s.fakeid + '/history', '历史 RSS')"><History :size="10" /> 历史</button>
          <button class="btn btn-xs flex-1" @click="openCategory(s.fakeid)"><Tag :size="10" /> 分类</button>
          <button class="btn btn-xs flex-1" style="color:var(--error);border-color:rgba(189,60,60,0.25);" @click="openConfirm(s.fakeid)"><Trash2 :size="10" /> 取消</button>
        </div>
      </div>
    </div>

    <!-- Export -->
    <div class="flex items-center gap-3 mt-6 pt-4" style="border-top: 1px solid var(--border-light);">
      <span class="text-[11px] font-semibold uppercase tracking-[0.05em]" style="color: var(--text-muted);">导出订阅</span>
      <a :href="exportUrl('csv')" class="btn btn-sm" target="_blank">导出 CSV</a>
      <a :href="exportUrl('opml')" class="btn btn-sm" target="_blank">导出 OPML</a>
    </div>

    <!-- Modals -->
    <SubscribeModal
      :visible="showSubscribe"
      :subscription-ids="subscriptionIdList"
      @close="showSubscribe = false"
      @subscribed="onSubscribed"
    />

    <CategoryPickerModal
      :visible="!!categoryTarget"
      :categories="categories"
      :current-category-id="categoryTarget ? subscriptions.find(s => s.fakeid === categoryTarget)?.category_id : null"
      @select="handleCategorySelect"
      @close="categoryTarget = null"
    />

    <ConfirmModal
      :show="!!confirmTarget"
      title="确认取消订阅"
      :message="'确定取消订阅「' + confirmName + '」吗？取消后不再轮询该公众号，但已缓存的文章数据会保留。'"
      confirm-text="确认取消"
      cancel-text="再想想"
      :danger="true"
      @confirm="handleConfirmUnsubscribe"
      @cancel="confirmTarget = null"
    />
  </div>
</template>
