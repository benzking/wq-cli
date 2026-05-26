<script setup>
import SkeletonLoader from './SkeletonLoader.vue'
import EmptyState from './EmptyState.vue'

defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  emptyText: { type: String, default: '暂无数据' },
  rowClick: { type: Function, default: null },
})
</script>

<template>
  <div class="bg-bg-primary rounded-lg shadow-sm overflow-hidden border border-border-light">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            :style="{ width: col.width }"
            class="py-2.5 px-3.5 text-left text-xs font-semibold text-text-muted border-b-2 border-border-light bg-bg-secondary"
          >
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td :colspan="columns.length">
            <SkeletonLoader :lines="3" />
          </td>
        </tr>
        <tr v-else-if="rows.length === 0">
          <td :colspan="columns.length">
            <EmptyState :text="emptyText" />
          </td>
        </tr>
        <tr
          v-for="(row, idx) in rows"
          :key="row.id || idx"
          class="hover:bg-bg-hover"
          :class="{ 'cursor-pointer': !!rowClick }"
          @click="rowClick && rowClick(row)"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            class="py-2 px-3.5 text-[13px] border-b border-border-light align-middle"
          >
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
              {{ row[col.key] }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
