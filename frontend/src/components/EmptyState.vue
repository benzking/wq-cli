<script setup>
import { Inbox } from 'lucide-vue-next'

defineProps({
  icon: { type: String, default: '' },
  text: { type: String, default: '暂无数据' },
})
</script>

<template>
  <div class="flex flex-col items-center justify-center py-[60px] px-5 text-text-muted">
    <Inbox v-if="!icon" :size="48" class="mb-3 opacity-40" />
    <span v-else class="text-[48px] mb-3 opacity-50">{{ icon }}</span>
    <p class="text-sm">{{ text }}</p>
  </div>
</template>
