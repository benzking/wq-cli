<script setup>
import { computed } from 'vue'
import { AlertTriangle, X } from 'lucide-vue-next'
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
  <div v-if="alerts.length" class="flex flex-col gap-2 pb-2.5">
    <div
      v-for="a in alerts"
      :key="a.id"
      class="flex items-center gap-3 px-4 py-2.5 rounded-[var(--radius-md)] text-[13px] border"
      :style="a.type === 'error'
        ? 'background: var(--error-bg); border-color: rgba(189,60,60,0.2); color: var(--error);'
        : 'background: var(--warning-bg); border-color: rgba(196,127,45,0.2); color: var(--warning);'"
    >
      <AlertTriangle :size="15" class="shrink-0 opacity-80" />
      <span class="flex-1">{{ a.message }}</span>
      <button
        v-if="a.action"
        class="px-3 py-1 text-[11px] font-medium rounded-[var(--radius-sm)] border cursor-pointer transition-all duration-150 hover:opacity-80"
        :style="{
          background: 'var(--bg-primary)',
          borderColor: 'currentColor',
          color: 'inherit',
        }"
        @click="go(a.to)"
      >{{ a.action.label }}</button>
      <button
        class="flex items-center justify-center w-5 h-5 rounded border-none cursor-pointer opacity-50 hover:opacity-100 transition-opacity"
        style="background: transparent; color: inherit;"
        @click="dismiss(a.id)"
      ><X :size="13" /></button>
    </div>
  </div>
</template>
