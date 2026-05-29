<script setup>
import { onMounted, inject, ref, computed } from 'vue'
import { useIngestion } from '@/composables/useIngestion'
import StatCard from '@/components/StatCard.vue'
import SearchInput from '@/components/SearchInput.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Pagination from '@/components/Pagination.vue'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const toast = inject('toast')
const {
  stats, workerStatus, logs, total, page, totalPages,
  status, channel, keyword, fakeid, loading,
  loadStats, loadLogs, changePage, reset,
  retryArticle, banArticle, unbanArticle,
} = useIngestion()

onMounted(() => { loadStats(); loadLogs() })

const activeFetchers = computed(() =>
  (workerStatus.value?.fetchers || []).filter(f => f.state === 'active').length
)
const totalFetchers = computed(() =>
  (workerStatus.value?.fetchers || []).length
)

const columns = [
  { key: 'nickname', label: '公众号', width: '120px' },
  { key: 'article_title', label: '标题' },
  { key: 'article_link', label: '链接', width: '150px' },
  { key: 'status', label: '状态', width: '90px' },
  { key: 'channel', label: '类型', width: '80px' },
  { key: 'fetcher', label: '渠道', width: '70px' },
  { key: 'attempt', label: '尝试', width: '50px' },
  { key: 'created_at', label: '入库时间', width: '130px' },
  { key: 'fetch_time', label: '抓取时间', width: '130px' },
  { key: 'actions', label: '操作', width: '70px' },
]

function statusLabel(s) {
  const map = {
    pending: '等待中', in_progress: '抓取中', success: '已入库',
    failed_retryable: '失败可重试', failed_permanent: '已禁止',
  }
  return map[s] || s
}

function channelLabel(c) {
  const map = { poll: '轮询器', deep_fetch: '深度抓取', manual: '手动' }
  return map[c] || c
}

function fetcherLabel(f) {
  if (!f) return '-'
  if (f.startsWith('cf_node_')) return 'CF-' + f.split('_').pop()
  if (f.startsWith('proxy_')) return '代理-' + f.split('_').pop()
  if (f === 'direct') return '直连'
  return f
}

function formatTime(ts) { return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-' }

async function handleRetry(row) {
  if (row.status === 'pending' || row.status === 'in_progress') return
  const ok = await retryArticle(row.fakeid, row.article_link)
  toast[ok ? 'success' : 'error'](ok ? '已加入重试队列' : '重试失败')
  if (ok) loadLogs()
}

async function handleBan(row) {
  if (row.status === 'failed_permanent') {
    const ok = await unbanArticle(row.fakeid, row.article_link)
    toast[ok ? 'success' : 'error'](ok ? '已解除禁止' : '操作失败')
  } else {
    const ok = await banArticle(row.fakeid, row.article_link)
    toast[ok ? 'success' : 'error'](ok ? '已禁止入库' : '操作失败')
  }
  if (ok) { loadStats(); loadLogs() }
}
</script>

<template>
  <div class="ingestion-page">
    <Teleport to="#topbar-title">
      <h1 class="text-[20px] font-bold text-text-primary">入库管理</h1>
    </Teleport>

    <div class="grid grid-cols-3 gap-3 mb-5 max-sm:grid-cols-2">
      <StatCard
        label="入库总览"
        :value="`已入库 ${stats?.success ?? 0}`"
        :sub="`全部文章 ${stats?.total ?? 0}`"
        accent="#2f9e44"
      />
      <StatCard
        label="今日动态"
        :value="`今日入库 ${stats?.today_success ?? 0}`"
        :sub="`队列中 ${stats?.pending ?? 0} / 失败 ${stats?.failed ?? 0}`"
        accent="#1890ff"
      />
      <StatCard
        label="渠道状态"
        :value="`可用 ${activeFetchers} / 全部 ${totalFetchers}`"
        accent="#7c3aed"
      />
    </div>

    <div class="flex gap-2 items-center mb-4 flex-wrap">
      <SearchInput v-model="fakeid" placeholder="公众号 (nickname)" />
      <SearchInput v-model="keyword" placeholder="搜索标题/链接" @keyup.enter="reset()" />
      <select v-model="channel" class="filter-select" @change="reset()">
        <option value="">全部类型</option>
        <option value="poll">轮询器</option>
        <option value="deep_fetch">深度抓取</option>
        <option value="manual">手动</option>
      </select>
      <select v-model="status" class="filter-select" @change="reset()">
        <option value="">全部状态</option>
        <option value="success">已入库</option>
        <option value="pending">等待中</option>
        <option value="in_progress">抓取中</option>
        <option value="failed_retryable">失败可重试</option>
        <option value="failed_permanent">已禁止</option>
      </select>
      <button class="btn btn-primary" @click="reset()">查询</button>
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
              <td class="title-cell" :title="l.article_title">{{ l.article_title || '-' }}</td>
              <td class="link-cell" :title="l.article_link">
                <a :href="l.article_link" target="_blank" class="text-accent">{{ (l.article_link || '').substring(0, 50) }}...</a>
              </td>
              <td><StatusBadge :type="l.status">{{ statusLabel(l.status) }}</StatusBadge></td>
              <td><StatusBadge :type="l.channel">{{ channelLabel(l.channel) }}</StatusBadge></td>
              <td><span class="fetcher-tag">{{ fetcherLabel(l.fetcher) }}</span></td>
              <td>{{ l.attempt }}</td>
              <td class="time-cell">{{ formatTime(l.created_at) }}</td>
              <td class="time-cell">{{ formatTime(l.updated_at) }}</td>
              <td class="actions-cell">
                <button
                  class="action-btn"
                  :class="{ disabled: l.status === 'pending' || l.status === 'in_progress' }"
                  :disabled="l.status === 'pending' || l.status === 'in_progress'"
                  :title="l.status === 'pending' || l.status === 'in_progress' ? '已在队列中' : '重新入库'"
                  @click="handleRetry(l)"
                >&#x21bb;</button>
                <button
                  class="action-btn"
                  :title="l.status === 'failed_permanent' ? '解除禁止' : '禁止入库'"
                  @click="handleBan(l)"
                >{{ l.status === 'failed_permanent' ? '&#x2714;' : '&#x2717;' }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pagination :page="page" :total-pages="totalPages" @page-change="changePage" />
    </div>
  </div>
</template>

<style scoped>
.filter-select {
  padding: 6px 10px; border: 1px solid var(--border-base); border-radius: var(--radius-sm);
  font-size: 13px; background: var(--bg-primary); color: var(--text-primary); outline: none;
}
.filter-select:focus { border-color: var(--accent); }
.title-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.link-cell { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.time-cell { white-space: nowrap; font-size: 11px; color: var(--text-muted); }
.fetcher-tag { font-size: 11px; color: var(--text-muted); padding: 1px 4px; background: var(--bg-hover); border-radius: 3px; }
.actions-cell { display: flex; gap: 6px; justify-content: center; align-items: center; }
.action-btn {
  background: none; border: 1px solid var(--border-base); border-radius: 4px;
  padding: 2px 6px; cursor: pointer; font-size: 14px; color: var(--text-muted);
  transition: color 0.15s, border-color 0.15s; line-height: 1.2;
}
.action-btn:hover:not(.disabled) { color: var(--accent); border-color: var(--accent); }
.action-btn.disabled { opacity: 0.35; cursor: not-allowed; }
</style>
