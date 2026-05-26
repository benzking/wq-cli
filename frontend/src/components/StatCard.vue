<script setup>
defineProps({
  label: String,
  value: [String, Number],
  sub: { type: String, default: '' },
  accent: { type: String, default: '' },
})
</script>

<template>
  <div
    class="bg-bg-primary rounded-lg p-[18px] shadow-sm border border-border-light border-l-[3px] border-l-solid transition-transform transition-shadow duration-150 hover:-translate-y-0.5 hover:shadow-md"
    :style="{ borderLeftColor: accent || 'transparent' }"
  >
    <div class="text-xs text-text-muted mb-2">{{ label }}</div>
    <div class="text-[28px] font-bold text-text-primary">{{ value }}</div>
    <div v-if="sub" class="text-xs text-text-muted mt-1 leading-[1.4]" v-html="sub"></div>
  </div>
</template>
