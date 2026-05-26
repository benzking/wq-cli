<script setup>
defineProps({
  lines: { type: Number, default: 4 },
})
</script>

<template>
  <div class="p-4">
    <div
      v-for="i in lines"
      :key="i"
      class="h-[14px] mb-3 rounded-[4px] animate-shimmer"
      :style="{
        width: (90 - i * 8) + '%',
        background: 'linear-gradient(90deg, var(--border-light) 25%, var(--bg-hover) 50%, var(--border-light) 75%)',
        backgroundSize: '200% 100%',
      }"
    />
  </div>
</template>

<style>
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.animate-shimmer { animation: shimmer 1.5s infinite; }
</style>
