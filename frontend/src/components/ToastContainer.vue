<script setup>
import { useToast } from '@/composables/useToast'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-vue-next'
const { toasts, remove } = useToast()

const iconMap = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const bgMap = {
  success: 'var(--success-bg)',
  error: 'var(--error-bg)',
  warning: 'var(--warning-bg)',
  info: 'var(--accent-light)',
}

const colorMap = {
  success: 'var(--success)',
  error: 'var(--error)',
  warning: 'var(--warning)',
  info: 'var(--accent)',
}
</script>

<template>
  <div class="z-[1000] fixed bottom-6 right-6 flex flex-col-reverse gap-2.5">
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="flex items-center gap-2.5 py-3 px-4 rounded-[10px] text-[13px] cursor-pointer shadow-md max-w-[380px] border backdrop-blur-sm transition-shadow duration-200 hover:shadow-lg"
        :style="{
          background: bgMap[t.type] || 'var(--bg-primary)',
          color: colorMap[t.type] || 'var(--text-primary)',
          borderColor: colorMap[t.type] ? (colorMap[t.type] + '30') : 'var(--border-light)',
        }"
        @click="remove(t.id)"
      >
        <component :is="iconMap[t.type] || iconMap.info" :size="16" class="shrink-0" />
        <span class="flex-1 leading-snug">{{ t.message }}</span>
        <X :size="14" class="shrink-0 opacity-40 hover:opacity-80 cursor-pointer" />
      </div>
    </TransitionGroup>
  </div>
</template>

<style>
.toast-enter-active { transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1); }
.toast-leave-active { transition: all 0.2s ease-in; }
.toast-enter-from { opacity: 0; transform: translateX(60px) scale(0.95); }
.toast-leave-to { opacity: 0; transform: translateX(40px) scale(0.9); }
</style>
