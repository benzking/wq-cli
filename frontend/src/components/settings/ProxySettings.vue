<script setup>
import { ref, onMounted, inject } from 'vue'
import StatusBadge from '@/components/StatusBadge.vue'

const toast = inject('toast')

const cfUrls = ref('')
const proxyUrls = ref('')
const effectiveRoute = ref('')
const testResults = ref([])
const loading = ref(false)
const testing = ref(false)

async function load() {
  loading.value = true
  const res = await fetch('/api/admin/fetch-config')
  const data = await res.json()
  cfUrls.value = (data.cf_worker_urls || []).join('\n')
  proxyUrls.value = (data.proxy_urls || []).join('\n')
  effectiveRoute.value = data.effective_route || ''
  loading.value = false
}

async function save() {
  const res = await fetch('/api/admin/fetch-config', {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cf_worker_urls: cfUrls.value.split('\n').filter(Boolean),
      proxy_urls: proxyUrls.value.split('\n').filter(Boolean),
    }),
  })
  const data = await res.json()
  if (data.success) { toast.success('配置已保存'); load() }
  else toast.error(data.message || '保存失败')
}

async function test() {
  testing.value = true
  const res = await fetch('/api/admin/fetch-config/test')
  const data = await res.json()
  testResults.value = data.results || []
  testing.value = false
}

async function reset() {
  await fetch('/api/admin/fetch-config/reset', { method: 'POST' })
  toast.success('已恢复默认配置')
  load()
}

onMounted(load)
</script>

<template>
  <div class="bg-accent-light text-accent py-2 px-3.5 rounded-md text-[13px] mb-4">
    当前回落链路: <strong>{{ effectiveRoute }}</strong>
  </div>
  <div class="mb-3.5">
    <label class="block text-xs font-semibold text-text-secondary mb-1">L1 CF Worker 节点</label>
    <textarea v-model="cfUrls" rows="4" class="w-full py-2 px-3 border border-border-base rounded-sm text-[13px] font-mono resize-y" placeholder="每行一个 Worker URL"></textarea>
  </div>
  <div class="mb-3.5">
    <label class="block text-xs font-semibold text-text-secondary mb-1">L2 SOCKS5 代理</label>
    <textarea v-model="proxyUrls" rows="4" class="w-full py-2 px-3 border border-border-base rounded-sm text-[13px] font-mono resize-y" placeholder="每行一个代理地址"></textarea>
  </div>
  <div class="mb-3.5">
    <label class="block text-xs font-semibold text-text-secondary mb-1">L3 直连（兜底，无需配置）</label>
  </div>
  <div class="flex gap-2 mb-4">
    <button class="btn btn-primary" @click="save">保存配置</button>
    <button class="btn" @click="test" :disabled="testing">{{ testing ? '测试中...' : '测试节点' }}</button>
    <button class="btn" @click="reset">恢复默认</button>
  </div>
  <div v-if="testResults.length" class="mt-4">
    <h3 class="text-sm font-semibold mb-2.5">测试结果</h3>
    <div class="table-wrap"><table>
      <thead><tr><th>等级</th><th>节点</th><th>状态</th><th>延迟</th><th>错误</th></tr></thead>
      <tbody>
        <tr v-for="r in testResults" :key="r.node">
          <td>{{ r.level }}</td>
          <td class="max-w-[200px] overflow-hidden text-ellipsis whitespace-nowrap">{{ r.node }}</td>
          <td><StatusBadge :type="r.status === 'ok' ? 'success' : 'error'">{{ r.status }}</StatusBadge></td>
          <td>{{ r.latency_ms }}ms</td>
          <td class="max-w-[150px] overflow-hidden text-ellipsis whitespace-nowrap text-error">{{ r.error || '-' }}</td>
        </tr>
      </tbody>
    </table></div>
  </div>
</template>
