<script setup>
defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true },
})
const emit = defineEmits(['page-change'])
</script>

<template>
  <div v-if="totalPages > 1" class="flex items-center justify-center gap-3 py-3">
    <button
      class="py-1 px-2.5 border border-border-base rounded-sm bg-bg-primary text-xs cursor-pointer text-text-secondary hover:border-accent hover:text-accent disabled:opacity-40 disabled:cursor-not-allowed"
      :disabled="page <= 1"
      @click="emit('page-change', page - 1)"
    >
      ← 上一页
    </button>
    <span class="text-xs text-text-muted">{{ page }} / {{ totalPages }}</span>
    <button
      class="py-1 px-2.5 border border-border-base rounded-sm bg-bg-primary text-xs cursor-pointer text-text-secondary hover:border-accent hover:text-accent disabled:opacity-40 disabled:cursor-not-allowed"
      :disabled="page >= totalPages"
      @click="emit('page-change', page + 1)"
    >
      下一页 →
    </button>
  </div>
</template>
