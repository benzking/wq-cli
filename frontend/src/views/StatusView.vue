<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useWorkerStatus } from '@/composables/useWorkerStatus'

const { worker, poller, refresh } = useWorkerStatus()
const refreshLabel = ref('自适应刷新')
const refreshDot = ref('idle')

let timer = null
let interval = 5000

function schedule() {
  const busy = !!(worker.value?.current_task || poller.value?.batch_progress)
  interval = busy ? 3000 : 10000
  refreshLabel.value = busy ? '自适应刷新 · 3s（活跃）' : '自适应刷新 · 10s（空闲）'
  refreshDot.value = busy ? 'active' : 'idle'
  clearInterval(timer)
  timer = setInterval(tick, interval)
}

async function tick() {
  await refresh()
  schedule()
}

async function togglePause() {
  try {
    const r = await fetch('/api/admin/ingestion/worker/pause', { method: 'POST' })
    const d = await r.json()
    if (d.success) await refresh()
  } catch (e) { console.error(e) }
}

function fmtTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function fmtTimeShort(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toTimeString().slice(0, 5)
}

function escapeHtml(s) {
  if (!s) return ''
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
}

onMounted(async () => {
  await refresh()
  schedule()
})
onUnmounted(() => { clearInterval(timer) })
</script>

<template>
  <div>
    <Teleport to="#topbar-title">
      <h1 class="text-[20px] font-bold text-text-primary">服务状态</h1>
    </Teleport>

    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2 text-[12px] text-text-muted">
        <span class="w-[7px] h-[7px] rounded-full"
          :class="refreshDot === 'active' ? 'bg-success shadow-[0_0_6px_rgba(59,140,94,0.4)]' : 'bg-warning'"></span>
        {{ refreshLabel }}
      </div>
      <button class="btn btn-sm" @click="refresh">立即刷新</button>
    </div>

    <!-- Worker Card -->
    <div class="card p-4 mb-4">
      <div class="flex items-center gap-2 mb-3">
        <span class="w-[8px] h-[8px] rounded-full"
          :style="{ background: worker?.running ? (worker?.paused ? 'var(--warning)' : 'var(--success)') : 'var(--text-muted)' }"></span>
        <h2 class="text-[15px] font-semibold text-text-primary">入库 Worker</h2>
        <button class="btn btn-xs ml-auto" @click="togglePause">
          {{ worker?.paused ? '恢复' : '暂停' }}
        </button>
      </div>

      <div class="grid grid-cols-2 gap-3 mb-3 text-[13px]">
        <div><span class="font-semibold text-text-secondary">状态:</span>
          <span :style="{ color: worker?.running ? (worker?.paused ? 'var(--warning)' : 'var(--success)') : 'var(--error)' }">
            {{ worker?.running ? (worker?.paused ? '已暂停' : '运行中') : '已停止' }}
          </span>
        </div>
        <div><span class="font-semibold text-text-secondary">队列:</span>
          {{ worker?.pending_count ?? 0 }} 篇待抓取
        </div>
      </div>

      <div v-if="worker?.current_task" class="mb-3 text-[13px]">
        <span class="font-semibold text-text-secondary">当前:</span>
        <a :href="worker.current_task.link" target="_blank" class="text-accent ml-1">
          {{ worker.current_task.nickname || worker.current_task.fakeid?.slice(0,8) }} ·
          {{ (worker.current_task.title || '').slice(0, 40) }}
        </a>
      </div>

      <h3 class="text-[13px] font-semibold text-text-secondary mb-2">渠道列表</h3>
      <table class="w-full text-[12px]">
        <thead>
          <tr class="text-text-muted border-b border-border-light">
            <th class="text-left py-2 font-semibold">状态</th>
            <th class="text-left py-2 font-semibold">名称</th>
            <th class="text-left py-2 font-semibold">阶段</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!worker?.fetchers?.length">
            <td colspan="3" class="py-3 text-center text-text-muted">暂无渠道</td>
          </tr>
          <tr v-for="f in worker?.fetchers || []" :key="f.name" class="border-b border-border-light">
            <td class="py-2">
              <span v-if="f.state === 'active' && worker?.current_task?.fetcher === f.name">🟢</span>
              <span v-else-if="f.state === 'active'">✅</span>
              <span v-else-if="f.state === 'cooling'">⏳</span>
              <span v-else>❌</span>
            </td>
            <td class="py-2">{{ f.label || f.name }}</td>
            <td class="py-2">
              <span v-if="worker?.current_task?.fetcher === f.name">正在抓取</span>
              <span v-else-if="f.state === 'active'">空闲</span>
              <span v-else-if="f.state === 'cooling'">冷却中</span>
              <span v-else>已熔断</span>
            </td>
          </tr>
        </tbody>
      </table>

      <h3 class="text-[13px] font-semibold text-text-secondary mt-4 mb-2">按公众号队列深度</h3>
      <div class="max-h-[300px] overflow-y-auto border border-border-light rounded-md">
        <table class="w-full text-[12px]">
          <thead>
            <tr class="text-text-muted border-b border-border-light bg-bg-secondary">
              <th class="text-left py-2 px-2 font-semibold">公众号</th>
              <th class="text-left py-2 px-2 font-semibold">FakeID</th>
              <th class="text-right py-2 px-2 font-semibold">待抓取</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!worker?.per_fakeid_pending?.length">
              <td colspan="3" class="py-3 text-center text-text-muted">队列为空</td>
            </tr>
            <tr v-for="(item, i) in worker?.per_fakeid_pending?.slice(0, 20) || []" :key="item.fakeid"
              class="border-b border-border-light">
              <td class="py-1.5 px-2">{{ item.nickname || item.fakeid }}</td>
              <td class="py-1.5 px-2 font-mono text-[11px] text-text-muted">{{ item.fakeid?.slice(0, 12) }}...</td>
              <td class="py-1.5 px-2 text-right font-semibold">{{ item.count }}</td>
            </tr>
            <tr v-if="(worker?.per_fakeid_pending?.length || 0) > 20">
              <td colspan="3" class="py-2 text-center text-text-muted">
                ... 还有 {{ worker.per_fakeid_pending.length - 20 }} 个 fakeid
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Poller Card -->
    <div class="card p-4 mb-4">
      <div class="flex items-center gap-2 mb-3">
        <span class="w-[8px] h-[8px] rounded-full"
          :style="{ background: poller?.running ? 'var(--success)' : 'var(--text-muted)' }"></span>
        <h2 class="text-[15px] font-semibold text-text-primary">RSS 轮询器</h2>
        <span class="text-[11px] text-text-muted ml-auto">
          (订阅: {{ poller?.subscription_count || '?' }} 个公众号)
        </span>
      </div>

      <div class="mb-3 text-[13px]">
        <span class="font-semibold text-text-secondary">状态:</span>
        <span :style="{ color: poller?.running ? 'var(--success)' : 'var(--error)' }">
          {{ poller?.running ? '运行中' : '已停止' }}
        </span>
      </div>

      <div v-if="poller?.batch_progress" class="mb-3 text-[13px]">
        <span class="font-semibold text-text-secondary">进度:</span>
        <span class="text-success font-semibold">{{ poller.batch_progress.done }} / {{ poller.batch_progress.total }}</span>
        <span v-if="poller.current_nickname" class="ml-2 text-text-muted">
          当前: {{ poller.current_nickname }}
        </span>
      </div>
      <div v-else-if="poller?.next_poll" class="mb-3 text-[13px] text-text-muted">
        空闲中 · 下次轮询: {{ fmtTimeShort(poller.next_poll.timestamp) }}
        (约 {{ Math.round(poller.next_poll.in_seconds / 60) }} 分钟后)
      </div>
      <div v-else-if="poller?.running" class="mb-3 text-[13px] text-text-muted">
        空闲中 · 等待首次轮询
      </div>
      <div v-else class="mb-3 text-[13px] text-text-muted">未启动</div>

      <h3 class="text-[13px] font-semibold text-text-secondary mb-2">本批次详情</h3>
      <div class="max-h-[400px] overflow-y-auto border border-border-light rounded-md">
        <table class="w-full text-[12px]">
          <thead>
            <tr class="text-text-muted border-b border-border-light bg-bg-secondary">
              <th class="text-left py-2 px-2 font-semibold">状态</th>
              <th class="text-left py-2 px-2 font-semibold">公众号</th>
              <th class="text-left py-2 px-2 font-semibold">FakeID</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!poller?.batch_detail?.length">
              <td colspan="3" class="py-3 text-center text-text-muted">暂无进行中的批次</td>
            </tr>
            <tr v-for="item in poller?.batch_detail || []" :key="item.fakeid"
              class="border-b border-border-light">
              <td class="py-1.5 px-2">
                <span class="badge text-[10px]"
                  :class="item.status === 'done' ? 'badge-success' : item.status === 'current' ? 'badge-primary' : 'badge-warning'">
                  {{ item.status === 'done' ? '✅ 已完成' : item.status === 'current' ? '⏳ 当前' : '☐ 待处理' }}
                </span>
              </td>
              <td class="py-1.5 px-2">{{ item.nickname || '-' }}</td>
              <td class="py-1.5 px-2 font-mono text-[11px] text-text-muted">{{ item.fakeid?.slice(0, 12) }}...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.badge-success { background: #f6ffed; color: #52c41a; }
.badge-primary { background: #e6f7ff; color: var(--accent, #1890ff); }
.badge-warning { background: #fffbe6; color: #fa8c16; }
</style>
