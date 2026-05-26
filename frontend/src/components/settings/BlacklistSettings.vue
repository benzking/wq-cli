<script setup>
import { ref, onMounted, inject } from 'vue'
import StatusBadge from '@/components/StatusBadge.vue'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'

const toast = inject('toast')

const items = ref([])
const fakeid = ref('')
const nickname = ref('')
const loading = ref(false)
const confirmDelId = ref(null)

async function load() {
  loading.value = true
  const res = await fetch('/api/admin/blacklist')
  const data = await res.json()
  items.value = data.blacklist || []
  loading.value = false
}

async function add() {
  if (!fakeid.value) return
  const res = await fetch('/api/admin/blacklist', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fakeid: fakeid.value, nickname: nickname.value, reason: 'manual', note: '手动添加' }),
  })
  const data = await res.json()
  toast[data.success ? 'success' : 'error'](data.message || '添加失败')
  fakeid.value = ''; nickname.value = ''
  load()
}

async function remove(fid) {
  await fetch(`/api/admin/blacklist/${fid}`, { method: 'DELETE' })
  toast.success('已移除')
  load()
}

async function del(id) {
  await fetch(`/api/admin/blacklist/record/${id}`, { method: 'DELETE' })
  toast.success('已删除')
  confirmDelId.value = null
  load()
}

function formatTime(ts) { return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-' }

onMounted(load)
</script>

<template>
  <div class="flex gap-2 items-center mb-4">
    <input v-model="fakeid" placeholder="FakeID" class="py-1.5 px-2.5 border border-border-base rounded-sm text-[13px]" />
    <input v-model="nickname" placeholder="公众号名称" class="py-1.5 px-2.5 border border-border-base rounded-sm text-[13px]" />
    <button class="btn btn-primary" @click="add">添加</button>
  </div>
  <SkeletonLoader v-if="loading" :lines="3" />
  <EmptyState v-else-if="!items.length" icon="🛡️" text="黑名单为空" />
  <div v-else class="table-wrap"><table>
    <thead><tr><th>公众号</th><th>FakeID</th><th>原因</th><th>触发次数</th><th>状态</th><th>时间</th><th>操作</th></tr></thead>
    <tbody>
      <tr v-for="b in items" :key="b.id">
        <td>{{ b.nickname }}</td><td>{{ b.fakeid }}</td><td>{{ b.reason }}</td><td>{{ b.verification_count }}</td>
        <td><StatusBadge :type="b.is_active ? 'warning' : 'info'">{{ b.is_active ? '生效中' : '已解除' }}</StatusBadge></td>
        <td>{{ formatTime(b.blacklisted_at) }}</td>
        <td>
          <button v-if="b.is_active" class="btn btn-sm" @click="remove(b.fakeid)">移除</button>
          <button v-else class="btn btn-sm !text-error" @click="confirmDelId = b.id">删除</button>
        </td>
      </tr>
    </tbody>
  </table></div>
  <ConfirmModal :show="!!confirmDelId" title="永久删除" message="此操作不可撤销" @confirm="del(confirmDelId)" @cancel="confirmDelId = null" />
</template>
