<script setup>
import { ref } from 'vue'
import { Search, X } from 'lucide-vue-next'
import EmptyState from './EmptyState.vue'
import { useRss } from '@/composables/useRss'

const props = defineProps({
  visible: Boolean,
  subscriptionIds: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'subscribed'])

const { searchBiz } = useRss()
const query = ref('')
const results = ref([])
const loading = ref(false)
const subscribing = ref(new Set())

const subscribedSet = new Set(props.subscriptionIds)

async function handleSearch() {
  const kw = query.value?.trim() || ''
  if (!kw) return
  loading.value = true
  try {
    const res = await fetch(`/api/public/searchbiz?query=${encodeURIComponent(kw)}`)
    const data = await res.json()
    results.value = (data.data?.list || []).map(r => ({
      ...r,
      subscribed: subscribedSet.has(r.fakeid),
    }))
  } finally { loading.value = false }
}

async function handleSubscribe(item) {
  if (item.subscribed || subscribing.value.has(item.fakeid)) return
  subscribing.value.add(item.fakeid)
  try {
    const res = await fetch('/api/rss/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fakeid: item.fakeid,
        nickname: item.nickname,
        alias: item.alias,
        head_img: item.round_head_img,
      }),
    })
    const data = await res.json()
    if (data.success) {
      item.subscribed = true
      emit('subscribed')
    }
  } finally { subscribing.value.delete(item.fakeid) }
}

function onSearchKeydown(e) {
  if (e.key === 'Enter') handleSearch()
}

function getInitial(name) {
  return (name || '?').charAt(0)
}

function avatarBg(i) {
  const colors = ['#dbeafe', '#fce7f3', '#fef3c7', '#dcfce7', '#ede9fe', '#fee2e2']
  const textColors = ['#2563eb', '#be185d', '#b45309', '#16a34a', '#7c3aed', '#dc2626']
  const idx = i % colors.length
  return { bg: colors[idx], color: textColors[idx] }
}
</script>

<template>
  <Teleport to="body">
    <transition name="scale">
      <div
        v-if="visible"
        class="fixed inset-0 z-[998] flex items-start justify-center pt-[15vh] p-5"
        style="background: rgba(0,0,0,0.35); backdrop-filter: blur(4px);"
        @click.self="emit('close')"
      >
        <div
          class="w-full max-w-[460px] rounded-2xl shadow-lg overflow-hidden flex flex-col"
          style="background: var(--bg-primary); animation: slideUp 0.3s cubic-bezier(0.16,1,0.3,1);"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-5 py-4" style="border-bottom: 1px solid var(--border-light);">
            <h3 class="text-[16px] font-semibold" style="color: var(--text-primary);">添加订阅</h3>
            <button
              class="flex items-center justify-center w-8 h-8 rounded-lg border-none cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)]"
              style="background: transparent; color: var(--text-muted);"
              @click="emit('close')"
            ><X :size="18" /></button>
          </div>

          <!-- Search -->
          <div class="px-5 py-4" style="border-bottom: 1px solid var(--border-light);">
            <div class="flex gap-2.5">
              <div class="flex-1 relative">
                <Search :size="15" class="absolute left-3.5 top-1/2 -translate-y-1/2 opacity-40" style="color: var(--text-muted);" />
                <input
                  v-model="query"
                  type="text"
                  class="input w-full !pl-9"
                  placeholder="输入公众号名称搜索..."
                  @keydown="onSearchKeydown"
                />
              </div>
              <button class="btn btn-primary" :disabled="loading" @click="handleSearch">
                {{ loading ? '搜索中...' : '搜索' }}
              </button>
            </div>
          </div>

          <!-- Results -->
          <div class="flex-1 overflow-y-auto" style="max-height: 340px;">
            <EmptyState v-if="!loading && results.length === 0 && query" text="未找到匹配的公众号" />

            <div
              v-for="(item, i) in results"
              :key="item.fakeid"
              class="flex items-center gap-3.5 px-5 py-3.5 transition-colors duration-150 hover:bg-[var(--bg-hover)]"
              :style="{ borderBottom: '1px solid var(--border-light)' }"
            >
              <!-- Avatar -->
              <img
                v-if="item.round_head_img"
                :src="item.round_head_img"
                class="w-9 h-9 rounded-full shrink-0"
                style="object-fit: cover;"
              />
              <div
                v-else
                class="w-9 h-9 rounded-full shrink-0 flex items-center justify-center text-[14px] font-semibold"
                :style="{ background: avatarBg(i).bg, color: avatarBg(i).color }"
              >{{ getInitial(item.nickname) }}</div>

              <!-- Info -->
              <div class="flex-1 min-w-0">
                <div class="text-[13px] font-semibold leading-snug" style="color: var(--text-primary);">{{ item.nickname }}</div>
                <div v-if="item.alias" class="text-[11px] leading-snug" style="color: var(--text-muted);">{{ item.alias }}</div>
              </div>

              <!-- Button -->
              <button
                v-if="item.subscribed"
                disabled
                class="btn btn-sm opacity-50 cursor-not-allowed"
                style="background: var(--bg-hover); color: var(--text-muted); border-color: var(--border-light);"
              >已订阅</button>
              <button
                v-else
                class="btn btn-primary btn-sm"
                :disabled="subscribing.has(item.fakeid)"
                @click="handleSubscribe(item)"
              >{{ subscribing.has(item.fakeid) ? '订阅中...' : '订阅' }}</button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
</style>
