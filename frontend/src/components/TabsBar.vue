<script setup>
defineProps({
  tabs: { type: Array, required: true },
  modelValue: { type: String, required: true },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <div class="flex gap-1 p-1 rounded-[var(--radius-md)] mb-5" style="background: var(--bg-hover);">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      class="relative py-2 px-4 border-none text-[13px] font-medium cursor-pointer rounded-[7px] transition-all duration-[200ms]"
      :style="modelValue === tab.key
        ? {
            background: 'var(--bg-primary)',
            color: 'var(--text-primary)',
            boxShadow: 'var(--shadow-xs)',
          }
        : {
            background: 'transparent',
            color: 'var(--text-muted)',
          }"
      @click="emit('update:modelValue', tab.key)"
      @mouseenter="(e) => {
        if (modelValue !== tab.key) {
          e.currentTarget.style.color = 'var(--text-secondary)'
        }
      }"
      @mouseleave="(e) => {
        if (modelValue !== tab.key) {
          e.currentTarget.style.color = 'var(--text-muted)'
        }
      }"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
