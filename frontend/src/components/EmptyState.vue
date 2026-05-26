<script setup>
defineProps({
  icon: { type: String, default: '📭' },
  text: { type: String, default: '暂无数据' },
})
</script>

<template>
  <div class="flex flex-col items-center justify-center py-[60px] px-5 text-text-muted">
    <div class="text-[48px] mb-3 opacity-50">{{ icon }}</div>
    <p class="text-sm">{{ text }}</p>
  </div>
</template>
