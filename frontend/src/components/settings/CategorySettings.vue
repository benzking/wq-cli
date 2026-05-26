<script setup>
import { ref, onMounted, inject } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'

const toast = inject('toast')
const baseUrl = window.location.origin

const items = ref([])
const name = ref('')
const desc = ref('')
const color = ref('blue')
const loading = ref(false)
const confirmDelId = ref(null)

const colorOptions = ['blue', 'green', 'orange', 'red', 'purple', 'cyan']

async function load() {
  loading.value = true
  const res = await fetch('/api/admin/categories')
  const data = await res.json()
  items.value = data.categories || []
  loading.value = false
}

async function create() {
  if (!name.value) return
  const res = await fetch('/api/admin/categories', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name.value, description: desc.value, color: color.value }),
  })
  const data = await res.json()
  toast[data.success ? 'success' : 'error'](data.message || '创建失败')
  name.value = ''; desc.value = ''
  load()
}

async function del(id) {
  await fetch(`/api/admin/categories/${id}`, { method: 'DELETE' })
  toast.success('已删除')
  confirmDelId.value = null
  load()
}

function copyRss(id) {
  navigator.clipboard.writeText(`${baseUrl}/api/rss/category/${id}`).then(() => toast.success('RSS 已复制'))
}

onMounted(load)
</script>

<template>
  <div class="flex gap-2 items-center mb-4 flex-wrap">
    <input v-model="name" placeholder="分类名称" class="py-1.5 px-2.5 border border-border-base rounded-sm text-[13px]" />
    <input v-model="desc" placeholder="描述" class="py-1.5 px-2.5 border border-border-base rounded-sm text-[13px]" />
    <div class="flex gap-1">
      <span
        v-for="c in colorOptions"
        :key="c"
        class="w-5 h-5 rounded-full cursor-pointer border-2 border-transparent transition-colors duration-150"
        :class="{
          'border-text-primary': color === c,
        }"
        :style="{ background: {
          blue: '#228be6', green: '#40c057', orange: '#fd7e14',
          red: '#e03131', purple: '#7950f2', cyan: '#15aabf',
        }[c] }"
        @click="color = c"
      ></span>
    </div>
    <button class="btn btn-primary" @click="create">创建</button>
  </div>
  <SkeletonLoader v-if="loading" :lines="3" />
  <EmptyState v-else-if="!items.length" icon="📁" text="暂无分类" />
  <div v-else class="flex flex-col gap-2">
    <div v-for="c in items" :key="c.id" class="bg-bg-primary border border-border-light rounded-md py-3 px-3.5">
      <div class="flex gap-2.5 items-center mb-2">
        <span class="w-1 h-8 rounded-sm shrink-0" :style="{ background: {
          blue: '#228be6', green: '#40c057', orange: '#fd7e14',
          red: '#e03131', purple: '#7950f2', cyan: '#15aabf',
        }[c.color] }"></span>
        <div>
          <div class="text-sm font-semibold">{{ c.name }}</div>
          <div class="text-xs text-text-muted">{{ c.description }}</div>
        </div>
      </div>
      <div class="flex gap-2 items-center">
        <span class="text-[11px] text-text-muted mr-auto">{{ c.subscription_count }} 个订阅</span>
        <button class="btn btn-sm" @click="copyRss(c.id)">复制 RSS</button>
        <button class="btn btn-sm !text-error" @click="confirmDelId = c.id">删除</button>
      </div>
    </div>
  </div>
  <ConfirmModal :show="!!confirmDelId" title="删除分类" message="订阅会自动解除关联" @confirm="del(confirmDelId)" @cancel="confirmDelId = null" />
</template>
