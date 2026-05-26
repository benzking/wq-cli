<script setup>
import { inject, ref, onMounted, onUnmounted } from 'vue'

const collapsed = inject('sidebarCollapsed')
const toggleSidebar = inject('toggleSidebar')

const user = ref({ authenticated: false, nickname: '' })
let _timer = null

async function refresh() {
  try {
    const res = await fetch('/api/admin/status')
    const data = await res.json()
    user.value = {
      authenticated: data.authenticated || data.loggedIn || false,
      nickname: data.nickname || '',
    }
  } catch {}
}

async function handleLogout() {
  await fetch('/api/admin/logout', { method: 'POST' })
  user.value = { authenticated: false, nickname: '' }
}

onMounted(() => { refresh(); _timer = setInterval(refresh, 30000) })
onUnmounted(() => { if (_timer) clearInterval(_timer) })
</script>

<template>
  <header class="flex items-center justify-between h-12 px-5 bg-bg-primary border-b border-border-light">
    <button
      class="border-none bg-none cursor-pointer text-xs text-text-muted px-2 py-1 rounded-sm hover:bg-bg-hover"
      @click="toggleSidebar"
    >
      {{ collapsed ? '▶' : '◀' }}
    </button>
    <div class="flex items-center gap-3">
      <span
        class="inline-flex items-center gap-1.5 text-xs"
        :class="user.authenticated ? 'text-success' : 'text-text-muted'"
      >
        <span
          class="inline-block w-2 h-2 rounded-full"
          :class="user.authenticated ? 'bg-success shadow-[0_0_6px_rgba(47,158,68,0.4)]' : 'bg-text-muted'"
        ></span>
        {{ user.authenticated ? user.nickname : '未登录' }}
      </span>
      <button
        v-if="user.authenticated"
        class="text-[11px] text-text-muted px-2.5 py-0.5 border border-border-base rounded-sm bg-bg-primary cursor-pointer hover:border-error hover:text-error"
        @click="handleLogout"
      >
        退出
      </button>
    </div>
  </header>
</template>
