<script setup>
import { ref, computed } from 'vue'
import { ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-vue-next'
import SkeletonLoader from './SkeletonLoader.vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  emptyText: { type: String, default: '暂无数据' },
  rowClick: { type: Function, default: null },
  search: { type: String, default: '' },
  searchColumns: { type: Array, default: () => [] },
})

const sortKey = ref('')
const sortDir = ref('')  // 'asc' | 'desc' | ''

const colMap = computed(() => {
  const m = {}
  for (const c of props.columns) m[c.key] = c
  return m
})

// --- sorting ---
function toggleSort(colKey) {
  const col = colMap.value[colKey]
  if (!col || col.sortable === false) return
  if (sortKey.value !== colKey) {
    sortKey.value = colKey
    sortDir.value = 'asc'
  } else if (sortDir.value === 'asc') {
    sortDir.value = 'desc'
  } else {
    sortKey.value = ''
    sortDir.value = ''
  }
}

// --- filtering ---
const filteredRows = computed(() => {
  let list = [...props.rows]

  // keyword search
  const q = (props.search || '').trim().toLowerCase()
  if (q && props.searchColumns.length > 0) {
    list = list.filter(row =>
      props.searchColumns.some(key => {
        const v = row[key]
        return v != null && String(v).toLowerCase().includes(q)
      })
    )
  }

  // sort
  if (sortKey.value) {
    const col = colMap.value[sortKey.value]
    const dir = sortDir.value === 'desc' ? -1 : 1
    list.sort((a, b) => {
      let va = a[sortKey.value]
      let vb = b[sortKey.value]
      if (va == null) va = ''
      if (vb == null) vb = ''
      if (col?.sortFn) return col.sortFn(va, vb) * dir
      if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir
      return String(va).localeCompare(String(vb), 'zh-CN') * dir
    })
  }

  return list
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
            class="py-2.5 px-3.5 text-left text-xs font-semibold text-text-muted border-b-2 border-border-light bg-bg-secondary group"
            :class="{ 'cursor-pointer select-none hover:text-text-primary': col.sortable !== false }"
            @click="toggleSort(col.key)"
          >
            <span class="inline-flex items-center gap-1">
              {{ col.label }}
              <component
                v-if="col.sortable !== false"
                :is="sortKey === col.key ? (sortDir === 'asc' ? ArrowUp : ArrowDown) : ArrowUpDown"
                :size="10"
                class="opacity-40 group-hover:opacity-70"
                :class="{ 'opacity-100 !text-accent': sortKey === col.key }"
              />
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td :colspan="columns.length">
            <SkeletonLoader :lines="3" />
          </td>
        </tr>
        <tr v-else-if="filteredRows.length === 0">
          <td :colspan="columns.length">
            <EmptyState :text="emptyText" />
          </td>
        </tr>
        <tr
          v-for="(row, idx) in filteredRows"
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
