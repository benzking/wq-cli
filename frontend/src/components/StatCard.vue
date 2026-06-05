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
    class="rounded-[var(--radius-md)] p-5 transition-all duration-[250ms] hover:-translate-y-0.5 hover:shadow-md"
    style="
      background: var(--bg-primary);
      border: 1px solid var(--border-light);
      box-shadow: var(--shadow-xs);
      border-left: 3px solid;
      border-left-color: accent || var(--border-base);
    "
    :style="{ borderLeftColor: accent || 'var(--border-base)' }"
  >
    <div class="text-[11px] font-semibold uppercase tracking-[0.05em] mb-2" style="color: var(--text-muted);">{{ label }}</div>
    <div class="text-[30px] font-bold tracking-[-0.02em] leading-none" style="color: var(--text-primary);">{{ value }}</div>
    <div v-if="sub" class="text-[12px] mt-1.5 leading-[1.5]" style="color: var(--text-muted);" v-html="sub"></div>
  </div>
</template>
