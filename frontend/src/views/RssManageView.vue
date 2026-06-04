<script setup>
import { onMounted, inject, ref } from 'vue'
import { useRss } from '@/composables/useRss'
import SearchInput from '@/components/SearchInput.vue'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const toast = inject('toast')
const baseUrl = window.location.origin

const {
  subscriptions, searchResults, query, loading, searchLoading,
  pollerStatus, loadSubscriptions, loadStatus, searchBiz, subscribe,
  unsubscribe, setCategory, triggerPoll, exportUrl,
} = useRss()

const categories = ref([])
async function loadCategories() {
  const res = await fetch('/api/admin/categories')
  const data = await res.json()
  if (data.categories) categories.value = data.categories
}

onMounted(() => { loadSubscriptions(); loadStatus(); loadCategories() })

async function handleSearch() {
  const kw = query.value?.trim?.() || ''
  if (!kw) { toast.warning('请输入公众号名称'); return }
  await searchBiz(kw)
}

async function handleSubscribe(fakeid, nickname, alias, headImg) {
  const r = await subscribe(fakeid, nickname, alias, headImg)
  toast[r.success ? 'success' : 'error'](r.success ? '订阅成功' : (r.detail || '订阅失败'))
}

async function handleUnsubscribe(fakeid, name) {
  const r = await unsubscribe(fakeid)
  toast[r.success ? 'success' : 'error'](r.success ? `已取消订阅 ${name}` : (r.detail || '取消失败'))
}

async function handlePoll() {
  const r = await triggerPoll()
  toast[r.success ? 'success' : 'error'](r.success ? '轮询已触发' : (r.detail || '触发失败'))
}

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function openWindow(url) { window.open(url, '_blank') }

function copyRssLink(url) {
  const full = baseUrl + url
  const el = document.createElement('textarea')
  el.value = full
  el.style.position = 'fixed'
  el.style.left = '-9999px'
  document.body.appendChild(el)
  el.select()
  try {
    document.execCommand('copy')
    toast.success('RSS 链接已复制')
  } catch {
    toast.error('复制失败，请手动复制')
  }
  document.body.removeChild(el)
}

function onSearchKeydown(e) {
  if (e.key === 'Enter') handleSearch()
}
</script>

<template>
  <div class="rss-page">
    <Teleport to="#topbar-title">
      <h1 class="text-[20px] font-bold text-text-primary">RSS 订阅管理</h1>
    </Teleport>

    <div class="status-bar">
      <div class="status-dot" :class="{ running: pollerStatus.running }">
        <span class="dot"></span>
        {{ pollerStatus.running ? '轮询器运行中' : '轮询器已停止' }}
        <span v-if="pollerStatus.next_poll" class="next-poll">下次: {{ formatTime(pollerStatus.next_poll) }}</span>
      </div>
      <div v-if="pollerStatus.consecutive_failures > 0" class="poll-alert" :class="pollerStatus.consecutive_failures >= 3 ? 'poll-error' : 'poll-warn'">
        最近 {{ pollerStatus.consecutive_failures }} 次轮询失败
        <span v-if="pollerStatus.last_fail_msg" class="poll-fail-msg">: {{ pollerStatus.last_fail_msg }}</span>
      </div>
      <div class="status-actions">
        <button class="btn" @click="handlePoll">立即轮询</button>
        <input class="agg-rss" readonly :value="baseUrl + '/api/rss/all'" @focus="$event.target.select()" />
        <button class="btn btn-sm" @click="copyRssLink('/api/rss/all')">复制聚合 RSS</button>
      </div>
    </div>

    <div class="search-section">
      <h3>添加订阅</h3>
      <div class="search-row">
        <input
          v-model="query"
          type="text"
          class="search-input"
          placeholder="输入公众号名称搜索..."
          @keydown.enter="handleSearch"
        />
        <button class="btn btn-primary" @click="handleSearch" :disabled="searchLoading">搜索</button>
      </div>

      <div v-if="searchResults.length" class="search-results">
        <div v-for="r in searchResults" :key="r.fakeid" class="search-item">
          <img v-if="r.round_head_img" :src="r.round_head_img" class="sr-avatar" />
          <div v-else class="sr-avatar-placeholder">{{ (r.nickname || '').charAt(0) }}</div>
          <span class="sr-name">{{ r.nickname }}</span>
          <span class="sr-alias">{{ r.alias }}</span>
          <button class="btn btn-sm btn-primary" @click="handleSubscribe(r.fakeid, r.nickname, r.alias, r.round_head_img)">订阅</button>
        </div>
      </div>
    </div>

    <section class="section">
      <h3>已订阅 ({{ subscriptions.length }})</h3>
      <SkeletonLoader v-if="loading" :lines="4" />
      <EmptyState v-else-if="!subscriptions.length" text="暂无订阅，搜索公众号并添加订阅" />
      <div v-else class="sub-grid">
        <div v-for="s in subscriptions" :key="s.fakeid" class="sub-card">
          <div class="sub-card-top">
            <img v-if="s.head_img" :src="s.head_img" class="sub-avatar" />
            <span v-else class="sub-avatar-placeholder">{{ (s.nickname || s.fakeid || '').charAt(0) }}</span>
            <div class="sub-info">
              <div class="sub-name">{{ s.nickname || s.alias || s.fakeid }}</div>
              <div class="sub-meta">{{ s.article_count || 0 }} 篇 · 最后轮询 {{ formatTime(s.last_poll) }}</div>
            </div>
          </div>
          <div class="sub-card-bottom">
            <select class="cat-select" @change="setCategory(s.fakeid, Number($event.target.value) || null)">
              <option :value="s.category_id || null">{{ s.category_name || '未分类' }}</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
            <button class="btn btn-sm" @click="copyRssLink('/api/rss/all?fakeid=' + s.fakeid)">复制 RSS</button>
            <button class="btn btn-sm" @click="openWindow('/api/rss/' + s.fakeid + '/history')">历史 RSS</button>
            <button class="btn btn-sm btn-danger" @click="handleUnsubscribe(s.fakeid, s.nickname || s.alias)">取消订阅</button>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <h3>导出订阅</h3>
      <div class="export-row">
        <a :href="exportUrl('csv')" class="btn" target="_blank">导出 CSV</a>
        <a :href="exportUrl('opml')" class="btn" target="_blank">导出 OPML</a>
      </div>
    </section>
  </div>
</template>

<style scoped>
.status-bar {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--bg-primary); border: 1px solid var(--border-light);
  border-radius: var(--radius-lg); padding: 14px 18px; margin-bottom: 16px;
}
.status-dot { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-secondary); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); flex-shrink: 0; }
.running .dot { background: var(--success); box-shadow: 0 0 6px rgba(47,158,68,0.4); }
.next-poll { font-size: 11px; color: var(--text-muted); }
.poll-alert { font-size: 12px; padding: 4px 12px; border-radius: 12px; flex-shrink: 0; }
.poll-warn { background: #fff3bf; color: #e67700; }
.poll-error { background: #ffe3e3; color: #c92a2a; }
.poll-fail-msg { opacity: 0.7; font-size: 11px; }
.agg-rss { width: 220px; padding: 6px 10px; border: 1px solid var(--border-base); border-radius: var(--radius-sm); font-size: 11px; background: var(--bg-secondary); }

.search-section {
  background: var(--bg-primary); border: 1px solid var(--border-light);
  border-radius: var(--radius-lg); padding: 18px; margin-bottom: 24px;
}
.search-section h3 { font-size: 14px; font-weight: 600; margin-bottom: 12px; }
.search-row { display: flex; gap: 8px; }
.search-input {
  flex: 1; padding: 8px 14px; border: 1px solid var(--border-base); border-radius: var(--radius-md);
  font-size: 14px; outline: none; background: var(--bg-primary); color: var(--text-primary);
  transition: border-color 150ms;
}
.search-input:focus { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-light); }
.search-results { margin-top: 12px; border: 1px solid var(--border-light); border-radius: var(--radius-md); overflow: hidden; }
.search-item { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-bottom: 1px solid var(--border-light); }
.sr-avatar { width: 28px; height: 28px; border-radius: 50%; }
.sr-avatar-placeholder { width: 28px; height: 28px; border-radius: 50%; background: var(--accent-light); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: var(--accent); flex-shrink: 0; }
.sr-name { font-size: 13px; font-weight: 600; }
.sr-alias { font-size: 11px; color: var(--text-muted); margin-right: auto; }

.section { margin-bottom: 24px; }
.section h3 { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.sub-grid { display: flex; flex-direction: column; gap: 8px; }
.sub-card {
  background: var(--bg-primary); border: 1px solid var(--border-light);
  border-radius: var(--radius-md); padding: 14px 16px;
  display: flex; flex-direction: column; gap: 10px;
}
.sub-card-top { display: flex; align-items: center; gap: 10px; }
.sub-avatar { width: 32px; height: 32px; border-radius: 50%; }
.sub-avatar-placeholder {
  width: 32px; height: 32px; border-radius: 50%; background: var(--accent-light);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600; color: var(--accent); flex-shrink: 0;
}
.sub-name { font-size: 14px; font-weight: 600; }
.sub-meta { font-size: 12px; color: var(--text-muted); }
.sub-card-bottom { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.cat-select { padding: 4px 8px; border: 1px solid var(--border-base); border-radius: var(--radius-sm); font-size: 12px; }
.export-row { display: flex; gap: 8px; }
</style>
