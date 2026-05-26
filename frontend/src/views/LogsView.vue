<script setup>
import { onMounted, ref } from 'vue'
import { useLogs } from '@/composables/useLogs'
import SearchInput from '@/components/SearchInput.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Pagination from '@/components/Pagination.vue'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const { logs, total, page, totalPages, level, module, keyword, since, until, loading, modules, autoRefresh, loadLogs, loadModules, changePage, reset, toggleAutoRefresh, cleanupDays } = useLogs()

const showDetail = ref(false)
const detailLog = ref(null)

onMounted(() => { loadModules(); loadLogs() })

function openDetail(row) { detailLog.value = row; showDetail.value = true }
function formatTime(ts) { return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-' }

const columns = [
  { key: 'level', label: '级别', width: '80px' },
  { key: 'timestamp', label: '时间', width: '160px' },
  { key: 'module', label: '模块', width: '140px' },
  { key: 'message', label: '内容' },
]
</script>

<template>
  <div class="logs-page">
    <h2 class="page-title">系统日志</h2>

    <div class="toolbar">
      <select v-model="level" class="filter-select" @change="reset()">
        <option value="">全部级别</option>
        <option value="INFO">INFO</option>
        <option value="WARNING">WARNING</option>
        <option value="ERROR">ERROR</option>
      </select>
      <select v-model="module" class="filter-select" @change="reset()">
        <option value="">全部模块</option>
        <option v-for="m in modules" :key="m" :value="m">{{ m }}</option>
      </select>
      <SearchInput v-model="keyword" placeholder="搜索内容..." @keyup.enter="reset()" />
      <button class="btn" @click="reset()">查询</button>
      <button class="btn btn-sm" @click="cleanupDays(7)">清理 7 天前</button>
      <label class="auto-refresh-label">
        <input type="checkbox" :checked="autoRefresh" @change="toggleAutoRefresh($event.target.checked)" />
        自动刷新
      </label>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th v-for="c in columns" :key="c.key" :style="{ width: c.width }">{{ c.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td :colspan="columns.length"><SkeletonLoader :lines="4" /></td></tr>
          <tr v-else-if="!logs.length"><td :colspan="columns.length"><EmptyState text="暂无日志" /></td></tr>
          <tr v-for="l in logs" :key="l.id" class="clickable" @click="openDetail(l)">
            <td><StatusBadge :type="l.level?.toLowerCase() === 'error' ? 'error' : l.level?.toLowerCase() === 'warning' ? 'warning' : 'info'">{{ l.level }}</StatusBadge></td>
            <td class="time-cell">{{ formatTime(l.timestamp) }}</td>
            <td>{{ l.module }}</td>
            <td class="msg-cell">{{ l.message }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <Pagination :page="page" :total-pages="totalPages" @page-change="changePage" />

    <Teleport to="body">
      <div v-if="showDetail" class="fixed inset-0 z-[999] bg-black/30 flex items-center justify-center" @click.self="showDetail = false">
        <div class="bg-bg-primary rounded-lg p-6 min-w-[450px] max-w-[600px] shadow-lg max-h-[80vh] overflow-y-auto">
          <h3>日志详情</h3>
          <div class="my-3 text-[13px]">
            <div class="mb-1.5"><strong>级别:</strong> {{ detailLog?.level }}</div>
            <div class="mb-1.5"><strong>时间:</strong> {{ formatTime(detailLog?.timestamp) }}</div>
            <div class="mb-1.5"><strong>模块:</strong> {{ detailLog?.module }}</div>
            <pre class="bg-bg-secondary p-3 rounded-sm mt-2 font-mono text-xs whitespace-pre-wrap max-h-[300px] overflow-y-auto">{{ detailLog?.message }}</pre>
          </div>
          <button class="btn" @click="showDetail = false">关闭</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.auto-refresh-label { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--text-muted); cursor: pointer; }
tr.clickable { cursor: pointer; }
.time-cell { white-space: nowrap; font-size: 11px; color: var(--text-muted); }
.msg-cell { max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 640px) { .toolbar { flex-direction: column; align-items: stretch; } }
</style>
