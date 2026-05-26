<script setup>
defineProps({
  type: { type: String, required: true },
})
</script>

<template>
  <span
    class="inline-flex px-1.5 py-px rounded-[4px] text-[11px] font-semibold whitespace-nowrap"
    :class="{
      'bg-[#f0faf2] text-success': type === 'success',
      'bg-[#fff2f0] text-error': type === 'failed' || type === 'error',
      'bg-[#fff7e6] text-warning': type === 'pending' || type === 'warning',
      'bg-accent-light text-accent': type === 'info' || type === 'poll',
      'bg-[#f9f0ff] text-[#7c3aed]': type === 'deep_fetch',
      'bg-[#e6f7ff] text-[#1890ff]': type === 'image_download',
    }"
  >
    <slot />
  </span>
</template>
