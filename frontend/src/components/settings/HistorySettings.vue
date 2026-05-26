<script setup>
import { ref, onMounted } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const subs = ref([])
const fakeid = ref('')
const count = ref(10)
const result = ref(null)
const loading = ref(false)
const fetching = ref(false)

async function load() {
  loading.value = true
  const res = await fetch('/api/rss/subscriptions')
  const data = await res.json()
  subs.value = data.subscriptions || data.data || []
  loading.value = false
}

async function fetchHistory() {
  if (!fakeid.value) return
  fetching.value = true; result.value = null
  const res = await fetch('/api/admin/history/fetch', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fakeid: fakeid.value, count: count.value }),
  })
  result.value = await res.json()
  fetching.value = false
}

onMounted(load)
</script>

<template>
  <div class="flex gap-5 max-sm:flex-col">
    <div class="w-[260px] max-h-[400px] overflow-y-auto border border-border-light rounded-md max-sm:w-full">
      <SkeletonLoader v-if="loading" :lines="5" />
      <EmptyState v-else-if="!subs.length" icon="📡" text="暂无订阅" />
      <div
        v-for="s in subs"
        :key="s.fakeid"
        class="flex justify-between py-2 px-3.5 border-b border-border-light cursor-pointer text-[13px] hover:bg-bg-hover"
        :class="{ 'bg-accent-light text-accent font-semibold': fakeid === s.fakeid }"
        @click="fakeid = s.fakeid"
      >
        {{ s.nickname || s.alias || s.fakeid }} <span class="text-[11px] text-text-muted">{{ s.article_count }}</span>
      </div>
    </div>
    <div class="flex-1">
      <div class="flex items-center gap-2 mb-2.5 text-[13px]">
        <label class="font-semibold">已选:</label> {{ fakeid || '请选择公众号' }}
      </div>
      <div class="flex items-center gap-2 mb-2.5 text-[13px]">
        <label class="font-semibold">数量:</label>
        <input v-model.number="count" type="number" min="1" max="100" class="py-1 px-2 border border-border-base rounded-sm text-[13px] w-20" />
      </div>
      <button class="btn btn-primary" @click="fetchHistory" :disabled="fetching || !fakeid">{{ fetching ? '获取中...' : '开始获取' }}</button>
      <div class="my-3 text-[11px] text-text-muted">
        <p>自动控频（2-4s 间隔），已有文章自动跳过</p>
        <p>触发验证码请到 <router-link to="/verify">验证码处理</router-link> 页面</p>
      </div>
      <div v-if="result" class="py-2.5 px-3.5 rounded-md text-[13px] mt-3" :class="result.success ? 'bg-[#f0faf2] text-success' : 'bg-[#fff2f0] text-error'">
        {{ result.message }}
      </div>
    </div>
  </div>
</template>
