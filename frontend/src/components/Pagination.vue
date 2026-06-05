<script setup>
defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true },
})
const emit = defineEmits(['page-change'])
</script>

<template>
  <div v-if="totalPages > 1" class="flex items-center justify-center gap-3 py-4">
    <button
      class="btn btn-sm"
      :disabled="page <= 1"
      @click="emit('page-change', page - 1)"
    >
      ← 上一页
    </button>
    <span class="text-[12px] font-medium px-2" style="color: var(--text-muted);">{{ page }} / {{ totalPages }}</span>
    <button
      class="btn btn-sm"
      :disabled="page >= totalPages"
      @click="emit('page-change', page + 1)"
    >
      下一页 →
    </button>
  </div>
</template>
