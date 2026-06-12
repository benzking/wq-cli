<script setup>
import { inject, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  LayoutDashboard, BookOpen, Rss, ArrowDownToLine,
  ScrollText, HardDrive, Settings, QrCode, ShieldCheck, Activity,
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
  status: Activity,
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
      { icon: 'rss', label: '公众号订阅', to: '/rss' },
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
      { icon: 'status', label: '服务状态', to: '/status' },
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
    class="fixed inset-y-0 left-0 z-[100] flex flex-col overflow-hidden transition-[width] duration-[280ms]"
    :class="collapsed ? 'w-14' : 'w-[230px]'"
    style="
      background: linear-gradient(180deg, #1e2128 0%, #1a1d23 100%);
      border-right: 1px solid rgba(255,255,255,0.06);
    "
  >
    <!-- Logo -->
    <div
      class="flex items-center gap-2.5 overflow-hidden whitespace-nowrap transition-all duration-[280ms]"
      :class="collapsed ? 'px-[14px] py-3.5 justify-center' : 'px-5 py-3.5'"
    >
      <div class="w-8 h-8 rounded-[10px] flex items-center justify-center shrink-0"
        style="background: linear-gradient(135deg, #5b6e8a 0%, #7a8fa8 100%); box-shadow: 0 2px 8px rgba(91,110,138,0.3);">
        <span class="text-white text-[15px] font-bold" style="font-family: var(--font-display);">W</span>
      </div>
      <span
        v-show="!collapsed"
        class="text-[13px] font-semibold tracking-[0.02em] opacity-100 transition-opacity duration-[280ms]"
        style="color: #e8eaed; font-family: var(--font-display);"
      >WeChat DAPI</span>
    </div>

    <!-- Nav -->
    <nav class="flex-1 overflow-y-auto overflow-x-hidden py-2">
      <div v-for="group in groups" :key="group.label">
        <!-- Group label -->
        <div
          v-show="!collapsed"
          class="px-5 pt-4 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] opacity-60 transition-opacity duration-[280ms]"
          style="color: #6b7280;"
        >{{ group.label }}</div>

        <router-link
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 whitespace-nowrap overflow-hidden mx-2 my-0.5 transition-all duration-[200ms] rounded-[8px]"
          :class="collapsed ? 'px-0 py-2.5 justify-center' : 'px-3.5 py-2.5'"
          :style="isActive(item.to) ? {
            background: 'rgba(91,110,138,0.18)',
            color: '#e8eaed',
            fontWeight: 600,
          } : {
            color: '#9ca3af',
          }"
          @mouseenter="(e) => {
            if (!isActive(item.to)) {
              e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
              e.currentTarget.style.color = '#d1d5db'
            }
          }"
          @mouseleave="(e) => {
            if (!isActive(item.to)) {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = '#9ca3af'
            }
          }"
        >
          <component
            :is="iconMap[item.icon]"
            :size="18"
            class="shrink-0 transition-transform duration-[200ms]"
            :style="{ opacity: isActive(item.to) ? 1 : 0.55 }"
          />
          <span
            v-show="!collapsed"
            class="text-[13px] leading-none"
          >{{ item.label }}</span>

          <!-- Active indicator -->
          <span
            v-if="isActive(item.to) && !collapsed"
            class="ml-auto w-1 h-1 rounded-full shrink-0"
            style="background: #8ba4c0;"
          ></span>
        </router-link>
      </div>
    </nav>

    <!-- Footer -->
    <div
      class="border-t px-4 py-3 overflow-hidden transition-all duration-[280ms]"
      style="border-color: rgba(255,255,255,0.06);"
    >
      <div
        class="flex items-center gap-2.5 overflow-hidden whitespace-nowrap"
        :class="collapsed ? 'justify-center' : ''"
      >
        <div
          class="w-6 h-6 rounded-full shrink-0 flex items-center justify-center"
          style="background: rgba(255,255,255,0.06);"
        >
          <span class="text-[10px] font-semibold" style="color: #6b7280;">v2</span>
        </div>
        <span
          v-show="!collapsed"
          class="text-[11px] opacity-50"
          style="color: #9ca3af;"
        >WeChat Download API</span>
      </div>
    </div>
  </aside>
</template>
