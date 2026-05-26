<script setup>
import { onMounted, inject, ref } from 'vue'
import { useIngestion } from '@/composables/useIngestion'
import StatCard from '@/components/StatCard.vue'
import SearchInput from '@/components/SearchInput.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Pagination from '@/components/Pagination.vue'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const toast = inject('toast')
const { stats, logs, total, page, totalPages, status, channel, keyword, loading, loadStats, loadLogs, changePage, reset } = useIngestion()

const retryFakeid = ref('')
const retryLink = ref('')
const retrying = ref(false)

onMounted(() => { loadStats(); loadLogs() })

const columns = [
  { key: 'nickname', label: '公众号' },
  { key: 'article_link', label: '文章链接', width: '240px' },
  { key: 'status', label: '状态', width: '80px' },
  { key: 'channel', label: '渠道', width: '90px' },
  { key: 'error_msg', label: '错误信息' },
  { key: 'attempt', label: '尝试', width: '60px' },
  { key: 'updated_at', label: '时间', width: '140px' },
]

async function handleRetry() {
  if (!retryFakeid.value && !retryLink.value) return
  retrying.value = true
  try {
    const res = await fetch('/api/admin/ingestion/retry', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fakeid: retryFakeid.value || undefined, article_links: retryLink.value ? [retryLink.value] : undefined, limit: 10 }),
    })
    const data = await res.json()
    toast[data.success ? 'success' : 'error'](data.success ? `已重试 ${data.data?.retried || 0} 条` : (data.error || '重试失败'))
    loadStats(); loadLogs()
  } finally { retrying.value = false }
}

function formatTime(ts) { return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-' }
</script>

<template>
  <div class="ingestion-page">
    <Teleport to="#topbar-title">
      <h1 class="text-[20px] font-bold text-text-primary">入库管理</h1>
    </Teleport>

    <div class="stats-row">
      <StatCard label="总计" :value="stats?.total ?? '-'" />
      <StatCard label="成功" :value="stats?.success ?? '-'" accent="#2f9e44" />
      <StatCard label="失败" :value="stats?.failed ?? '-'" accent="#c92a2a" />
      <StatCard label="等待中" :value="stats?.pending ?? '-'" accent="#e07b39" />
    </div>

    <div class="retry-section">
      <h3>手动重试</h3>
      <div class="retry-form">
        <input v-model="retryFakeid" placeholder="公众号 FakeID (可选)" class="retry-input" />
        <input v-model="retryLink" placeholder="文章链接 (可选)" class="retry-input" />
        <button class="btn btn-primary" @click="handleRetry" :disabled="retrying">{{ retrying ? '重试中...' : '开始重试' }}</button>
      </div>
    </div>

    <div class="toolbar">
      <select v-model="status" class="filter-select" @change="reset()">
        <option value="">全部状态</option>
        <option value="success">成功</option>
        <option value="failed">失败</option>
        <option value="pending">等待中</option>
      </select>
      <select v-model="channel" class="filter-select" @change="reset()">
        <option value="">全部渠道</option>
        <option value="poll">轮询</option>
        <option value="deep_fetch">深度抓取</option>
      </select>
      <SearchInput v-model="keyword" placeholder="搜索..." @keyup.enter="reset()" />
      <button class="btn" @click="reset()">查询</button>
    </div>

    <div class="data-table-wrap">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th v-for="c in columns" :key="c.key" :style="{ width: c.width }">{{ c.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td :colspan="columns.length"><SkeletonLoader :lines="4" /></td></tr>
            <tr v-else-if="!logs.length"><td :colspan="columns.length"><EmptyState text="暂无入库记录" /></td></tr>
            <tr v-for="l in logs" :key="l.id">
              <td>{{ l.nickname || l.fakeid || '-' }}</td>
              <td class="link-cell" :title="l.article_link">{{ l.article_link || '-' }}</td>
              <td><StatusBadge :type="l.status">{{ l.status }}</StatusBadge></td>
              <td><StatusBadge :type="l.channel">{{ l.channel }}</StatusBadge></td>
              <td class="err-cell" :title="l.error_msg">{{ l.error_msg || '-' }}</td>
              <td>{{ l.attempt }}</td>
              <td class="time-cell">{{ formatTime(l.updated_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pagination :page="page" :total-pages="totalPages" @page-change="changePage" />
    </div>
  </div>
</template>

<style scoped>
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.retry-section { background: var(--bg-primary); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 16px; margin-bottom: 16px; }
.retry-section h3 { font-size: 14px; margin-bottom: 10px; }
.retry-form { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.retry-input { padding: 6px 10px; border: 1px solid var(--border-base); border-radius: var(--radius-sm); font-size: 13px; min-width: 180px; }
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.link-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.err-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--error); }
.time-cell { white-space: nowrap; font-size: 11px; color: var(--text-muted); }
@media (max-width: 768px) { .stats-row { grid-template-columns: repeat(2, 1fr); } }
</style>
