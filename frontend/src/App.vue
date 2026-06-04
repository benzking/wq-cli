<script setup>
import { provide, ref, readonly, onMounted, onUnmounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { useAuth } from '@/composables/useAuth'
import ToastContainer from '@/components/ToastContainer.vue'
import AlertBanner from '@/components/AlertBanner.vue'
import AppTopBar from '@/components/AppTopBar.vue'
import AppSidebar from '@/components/AppSidebar.vue'

const sidebarCollapsed = ref(false)
const toggleSidebar = () => { sidebarCollapsed.value = !sidebarCollapsed.value }
provide('sidebarCollapsed', readonly(sidebarCollapsed))
provide('toggleSidebar', toggleSidebar)

const { toasts, success, error, warning, info } = useToast()
provide('toast', { success, error, warning, info })

const { startAutoRefresh, stopAutoRefresh, loadAccounts, loadAlertStatus } = useAuth()
onMounted(() => {
  loadAccounts()
  loadAlertStatus()
  startAutoRefresh(30000)
})
onUnmounted(() => stopAutoRefresh())
</script>

<template>
  <div class="flex min-h-screen">
    <AppSidebar />
    <div class="flex-1 flex flex-col transition-[margin-left] duration-[250ms]" :class="sidebarCollapsed ? 'ml-14' : 'ml-[220px]'">
      <AppTopBar />
      <main class="flex-1 p-6 overflow-y-auto">
        <AlertBanner />
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
    <ToastContainer :toasts="toasts" />
  </div>
</template>
