<script setup>
import { inject, ref, onMounted, onUnmounted } from 'vue'
import { PanelLeftOpen, PanelLeftClose, LogOut } from 'lucide-vue-next'

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
  <header
    class="flex items-center justify-between h-[52px] px-5 transition-all duration-[280ms]"
    style="
      background: rgba(255,255,255,0.72);
      backdrop-filter: blur(16px) saturate(180%);
      -webkit-backdrop-filter: blur(16px) saturate(180%);
      border-bottom: 1px solid rgba(0,0,0,0.06);
    "
  >
    <div class="flex items-center gap-3">
      <button
        class="flex items-center justify-center w-8 h-8 rounded-lg border-none cursor-pointer transition-all duration-[200ms] hover:bg-[rgba(0,0,0,0.04)]"
        style="color: var(--text-muted); background: transparent;"
        @click="toggleSidebar"
      >
        <component :is="collapsed ? PanelLeftOpen : PanelLeftClose" :size="17" />
      </button>
      <div id="topbar-title"></div>
    </div>

    <div class="flex items-center gap-4">
      <!-- Status -->
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
        :style="user.authenticated
          ? 'background: var(--success-bg); color: var(--success);'
          : 'background: var(--bg-hover); color: var(--text-muted);'"
      >
        <span
          class="inline-block w-[7px] h-[7px] rounded-full"
          :style="user.authenticated
            ? 'background: var(--success); box-shadow: 0 0 6px rgba(59,140,94,0.4);'
            : 'background: var(--text-muted);'"
        ></span>
        {{ user.authenticated ? user.nickname : '未登录' }}
      </div>

      <!-- Logout -->
      <button
        v-if="user.authenticated"
        class="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium rounded-lg border cursor-pointer transition-all duration-[200ms]"
        style="
          background: transparent;
          border-color: transparent;
          color: var(--text-muted);
        "
        @mouseenter="(e) => {
          e.currentTarget.style.background = 'var(--error-bg)';
          e.currentTarget.style.color = 'var(--error)';
          e.currentTarget.style.borderColor = 'transparent';
        }"
        @mouseleave="(e) => {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = 'var(--text-muted)';
          e.currentTarget.style.borderColor = 'transparent';
        }"
        @click="handleLogout"
      >
        <LogOut :size="13" />
        退出
      </button>
    </div>
  </header>
</template>
