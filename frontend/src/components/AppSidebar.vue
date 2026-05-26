<script setup>
import { inject, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  LayoutDashboard, BookOpen, Rss, ArrowDownToLine,
  ScrollText, HardDrive, Settings, QrCode, ShieldCheck,
} from 'lucide-vue-next'

const collapsed = inject('sidebarCollapsed')
const route = useRoute()

const iconMap = {
  dashboard: LayoutDashboard,
  browse: BookOpen,
  rss: Rss,
  ingestion: ArrowDownToLine,
  logs: ScrollText,
  backup: HardDrive,
  settings: Settings,
  login: QrCode,
  verify: ShieldCheck,
}

const groups = [
  {
    label: '概览',
    items: [
      { icon: 'dashboard', label: '数据看板', to: '/' },
    ],
  },
  {
    label: '内容',
    items: [
      { icon: 'browse', label: '文章浏览', to: '/browse' },
      { icon: 'rss', label: 'RSS 订阅', to: '/rss' },
    ],
  },
  {
    label: '管理',
    items: [
      { icon: 'ingestion', label: '入库管理', to: '/ingestion' },
      { icon: 'logs', label: '系统日志', to: '/logs' },
      { icon: 'backup', label: '备份管理', to: '/backup' },
      { icon: 'settings', label: '设置', to: '/settings' },
    ],
  },
  {
    label: '系统',
    items: [
      { icon: 'login', label: '扫码登录', to: '/login' },
      { icon: 'verify', label: '验证码处理', to: '/verify' },
    ],
  },
]

const isActive = (path) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<template>
  <aside
    class="fixed inset-y-0 left-0 z-[100] flex flex-col overflow-hidden border-r border-border-light bg-bg-primary transition-[width] duration-[250ms]"
    :class="collapsed ? 'w-14' : 'w-[220px]'"
  >
    <div class="whitespace-nowrap overflow-hidden border-b border-border-light px-[18px] py-4 text-sm font-bold text-text-primary">
      WeChat API
    </div>
    <nav class="flex-1">
      <div v-for="group in groups" :key="group.label">
        <div class="mt-2 border-t-2 border-border-light pt-4 pb-1 px-4 text-[10px] font-semibold uppercase tracking-[0.5px] text-text-muted">
          {{ group.label }}
        </div>
        <router-link
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-2.5 whitespace-nowrap overflow-hidden my-0.5 mx-2 py-2 px-4 rounded-sm text-[13px] text-text-secondary no-underline transition duration-150 hover:bg-accent-light hover:text-accent"
          :class="{ 'bg-accent-light text-accent font-semibold': isActive(item.to) }"
        >
          <component :is="iconMap[item.icon]" :size="16" class="shrink-0" />
          <span>{{ item.label }}</span>
        </router-link>
      </div>
    </nav>
  </aside>
</template>
