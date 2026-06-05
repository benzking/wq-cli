<script setup>
import { Inbox } from 'lucide-vue-next'

defineProps({
  icon: { type: String, default: '' },
  text: { type: String, default: '暂无数据' },
})
</script>

<template>
  <div class="flex flex-col items-center justify-center py-20 px-5">
    <div
      v-if="!icon"
      class="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
      style="background: var(--bg-hover);"
    >
      <Inbox :size="28" style="color: var(--text-muted); opacity: 0.5;" />
    </div>
    <span v-else class="text-[48px] mb-4 opacity-40">{{ icon }}</span>
    <p class="text-[13px] font-medium" style="color: var(--text-muted);">{{ text }}</p>
  </div>
</template>
