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
      class="skeleton mb-3"
      :style="{
        height: '12px',
        width: (92 - i * 10) + '%',
        opacity: 1 - i * 0.08,
      }"
    />
  </div>
</template>
