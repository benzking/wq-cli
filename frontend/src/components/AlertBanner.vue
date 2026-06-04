<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const { alertStatus } = useAuth()

const dismissed = new Set()

const alerts = computed(() => {
  const result = []
  const s = alertStatus.value
  if (!s) return result

  if (s.credential_expired && !dismissed.has('credential_expired')) {
    result.push({
      id: 'credential_expired',
      type: 'error',
      message: `${s.credential_nickname || '当前公众号'} 的登录凭据已过期，RSS 轮询和文章抓取将受影响`,
      action: { label: '重新登录', to: '/login' },
    })
  } else if (s.credential_expiring_soon && !dismissed.has('credential_expiring_soon')) {
    result.push({
      id: 'credential_expiring_soon',
      type: 'warning',
      message: `${s.credential_nickname || '当前公众号'} 的登录凭据将在 ${s.credential_hours_left} 小时后过期`,
      action: { label: '重新登录', to: '/login' },
    })
  }

  if (s.poll_consecutive_failures >= 3 && !dismissed.has('poll_fail_3')) {
    result.push({
      id: 'poll_fail_3',
      type: 'error',
      message: `RSS 轮询连续 ${s.poll_consecutive_failures} 次失败（${s.poll_last_fail_msg || '未知原因'}），可能影响文章更新`,
      action: { label: '查看 RSS', to: '/rss' },
    })
  } else if (s.poll_consecutive_failures >= 1 && !dismissed.has('poll_fail_1')) {
    result.push({
      id: 'poll_fail_1',
      type: 'warning',
      message: `RSS 轮询最近一次失败（${s.poll_last_fail_msg || '未知原因'}），请检查网络或凭据`,
      action: { label: '查看 RSS', to: '/rss' },
    })
  }

  return result
})

function dismiss(id) { dismissed.add(id) }
function go(to) { router.push(to) }
</script>

<template>
  <div v-if="alerts.length" class="alert-stack">
    <div v-for="a in alerts" :key="a.id" class="alert-item" :class="'alert-' + a.type">
      <span class="alert-icon">&#9888;</span>
      <span class="alert-msg">{{ a.message }}</span>
      <button v-if="a.action" class="alert-action" @click="go(a.to)">{{ a.action.label }}</button>
      <button class="alert-close" @click="dismiss(a.id)">&times;</button>
    </div>
  </div>
</template>

<style scoped>
.alert-stack { display: flex; flex-direction: column; gap: 6px; padding: 0 0 10px 0; }
.alert-item { display: flex; align-items: center; gap: 10px; padding: 10px 16px; border-radius: var(--radius-md); font-size: 13px; }
.alert-error { background: #fff5f5; border: 1px solid #ffc9c9; color: #c92a2a; }
.alert-warning { background: #fff9db; border: 1px solid #ffec99; color: #e67700; }
.alert-icon { flex-shrink: 0; }
.alert-msg { flex: 1; }
.alert-action { padding: 4px 12px; background: var(--bg-primary); border: 1px solid currentColor; border-radius: var(--radius-sm); font-size: 11px; cursor: pointer; color: inherit; }
.alert-action:hover { opacity: 0.8; }
.alert-close { background: none; border: none; font-size: 18px; cursor: pointer; color: inherit; opacity: 0.6; padding: 0 2px; }
.alert-close:hover { opacity: 1; }
</style>
