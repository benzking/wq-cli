<script setup>
import { onMounted, computed, inject, ref } from 'vue'
import { useArticles } from '@/composables/useArticles'
import { List, Star, StarOff, RefreshCw, ExternalLink, FileText, FileDown } from 'lucide-vue-next'
import SearchInput from '@/components/SearchInput.vue'
import Pagination from '@/components/Pagination.vue'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const toast = inject('toast')
const localKeyword = ref('')

const {
  subscriptions, selectedFakeid, articles, currentArticle,
  totalPages, page, total, loading, detailLoading,
  loadSubscriptions, loadArticles, loadArticleDetail, toggleStar,
  selectFakeid, changePage, search,
} = useArticles()

onMounted(() => {
  loadSubscriptions()
  loadArticles()
})

const groupedSubs = computed(() => {
  const cats = {}
  for (const s of subscriptions.value) {
    const cat = s.category_name || '未分类'
    if (!cats[cat]) cats[cat] = []
    cats[cat].push(s)
  }
  return cats
})

const selectedSubName = computed(() => {
  if (!selectedFakeid.value) return '全部文章'
  const s = subscriptions.value.find(s => s.fakeid === selectedFakeid.value)
  return s ? (s.nickname || s.alias || s.fakeid) : '全部文章'
})

function onSearch() {
  search(localKeyword.value)
}

function handleRefetch() {
  if (!currentArticle.value) return
  fetch(`/api/browse/article/${currentArticle.value.id}/refetch`, { method: 'POST' })
    .then(r => r.json())
    .then(d => { toast.success(d.success ? '已加入重抓队列' : (d.error || '重抓失败')) })
}

function handleExportMD() {
  if (!currentArticle.value) return
  window.open(`/api/browse/article/${currentArticle.value.id}/export`, '_blank')
}

function handleExportPDF() {
  window.print()
}

function handleOpenOriginal() {
  if (!currentArticle.value?.link) return
  window.open(currentArticle.value.link, '_blank')
}

function formatArticleDate(ts) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleDateString('zh-CN')
}

function formatFullDate(ts) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="flex overflow-hidden -m-6" style="height: calc(100vh - 48px)">
    <!-- 第一栏：订阅源 -->
    <aside class="w-[220px] bg-bg-primary border-r border-border-light flex flex-col shrink-0">
      <div class="flex items-center justify-between py-3 px-4 text-[13px] font-semibold border-b border-border-light">
        订阅源 <span class="text-[10px] text-text-muted bg-bg-hover py-px px-1.5 rounded-lg">{{ subscriptions.length }}</span>
      </div>
      <div class="flex-1 overflow-y-auto py-1">
        <div
          class="flex items-center gap-2 py-1.5 px-4 cursor-pointer text-[13px] font-semibold transition-colors duration-150"
          :class="!selectedFakeid ? 'bg-accent-light text-accent' : 'hover:bg-accent-light'"
          @click="selectFakeid('')"
        >
          <List :size="16" class="shrink-0 w-5 text-text-muted" />
          <span class="flex-1 overflow-hidden text-ellipsis whitespace-nowrap">全部文章</span>
          <span class="text-[11px] text-text-muted">{{ total }}</span>
        </div>
        <template v-for="(subs, catName) in groupedSubs" :key="catName">
          <div class="text-[10px] font-semibold text-text-muted uppercase tracking-[0.5px] pt-3 pb-1 px-4 border-t-2 border-border-light mt-1 mx-3">{{ catName }}</div>
          <div
            v-for="s in subs"
            :key="s.fakeid"
            class="flex items-center gap-2 py-1.5 px-4 cursor-pointer text-[13px] transition-colors duration-150"
            :class="selectedFakeid === s.fakeid ? 'bg-accent-light text-accent font-semibold' : 'hover:bg-accent-light'"
            @click="selectFakeid(s.fakeid)"
          >
            <span class="text-base shrink-0 w-5 text-center text-text-muted font-semibold">{{ (s.nickname || s.fakeid).charAt(0) }}</span>
            <span class="flex-1 overflow-hidden text-ellipsis whitespace-nowrap">{{ s.nickname || s.alias || s.fakeid }}</span>
            <span class="text-[11px] text-text-muted">{{ s.article_count }}</span>
          </div>
        </template>
      </div>
    </aside>

    <!-- 第二栏：文章列表 -->
    <section class="w-[320px] bg-bg-primary border-r border-border-light flex flex-col shrink-0">
      <div class="flex items-center justify-between py-3 px-4 text-[13px] font-semibold border-b border-border-light">
        <span>{{ selectedSubName }}</span>
        <span class="text-[11px] text-text-muted font-normal">{{ total }}</span>
      </div>
      <div class="py-2 px-3 border-b border-border-light">
        <SearchInput v-model="localKeyword" placeholder="搜索文章标题..." class="!w-full" @keyup.enter="onSearch" />
      </div>
      <div class="flex-1 overflow-y-auto">
        <SkeletonLoader v-if="loading" :lines="6" />
        <EmptyState v-else-if="articles.length === 0" text="暂无文章" />
        <div
          v-for="a in articles"
          :key="a.id"
          class="py-3 px-4 border-b border-border-light cursor-pointer transition-colors duration-150"
          :class="currentArticle?.id === a.id ? 'bg-accent-light border-l-[3px] border-l-accent' : 'hover:bg-bg-hover'"
          @click="loadArticleDetail(a.id)"
        >
          <div class="text-[13px] leading-[1.4] mb-1 line-clamp-2" :class="{ 'text-accent': currentArticle?.id === a.id }">{{ a.title }}</div>
          <div class="text-[11px] text-text-muted">{{ a.nickname || a.fakeid }} · {{ formatArticleDate(a.publish_time) }}</div>
        </div>
      </div>
      <Pagination :page="page" :total-pages="totalPages" @page-change="changePage" />
    </section>

    <!-- 第三栏：文章内容 -->
    <section class="flex-1 flex flex-col min-w-0 bg-bg-reading">
      <template v-if="currentArticle">
        <div class="relative px-7 py-5 border-b border-border-light bg-bg-primary">
          <h2 class="font-body text-[22px] leading-[1.4] mb-2 text-text-primary">{{ currentArticle.title }}</h2>
          <div class="flex items-center gap-2 text-xs text-text-muted">
            <span>{{ currentArticle.nickname || currentArticle.fakeid }}</span>
            <span>·</span>
            <span>{{ formatFullDate(currentArticle.publish_time) }}</span>
            <span>·</span>
            <span class="bg-bg-secondary py-0.5 px-2 rounded text-[11px]">已抓取</span>
          </div>
          <div class="absolute top-4 right-5 flex gap-1">
            <button class="w-8 h-8 border border-border-light rounded-sm bg-bg-primary cursor-pointer text-sm flex items-center justify-center transition-colors duration-150 hover:bg-bg-hover" :class="currentArticle.starred ? 'text-accent' : 'text-text-secondary'" :title="currentArticle.starred ? '取消收藏' : '收藏'" @click="toggleStar(currentArticle.id)">
              <component :is="currentArticle.starred ? Star : StarOff" :size="14" />
            </button>
            <button class="w-8 h-8 border border-border-light rounded-sm bg-bg-primary cursor-pointer text-sm flex items-center justify-center text-text-secondary transition-colors duration-150 hover:bg-bg-hover hover:text-accent" title="重新抓取" @click="handleRefetch">
              <RefreshCw :size="14" />
            </button>
            <span class="w-px bg-border-light mx-1"></span>
            <button class="w-8 h-8 border border-border-light rounded-sm bg-bg-primary cursor-pointer text-sm flex items-center justify-center text-text-secondary transition-colors duration-150 hover:bg-bg-hover hover:text-accent" title="原文" @click="handleOpenOriginal">
              <ExternalLink :size="14" />
            </button>
            <button class="w-8 h-8 border border-border-light rounded-sm bg-bg-primary cursor-pointer text-sm flex items-center justify-center text-text-secondary transition-colors duration-150 hover:bg-bg-hover hover:text-accent" title="导出 PDF" @click="handleExportPDF">
              <FileText :size="14" />
            </button>
            <button class="w-8 h-8 border border-border-light rounded-sm bg-bg-primary cursor-pointer text-sm flex items-center justify-center text-text-secondary transition-colors duration-150 hover:bg-bg-hover hover:text-accent" title="导出 Markdown" @click="handleExportMD">
              <FileDown :size="14" />
            </button>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto py-6 px-7">
          <SkeletonLoader v-if="detailLoading" :lines="8" />
          <div v-else class="article-content" v-html="currentArticle.content"></div>
        </div>
      </template>
      <EmptyState v-else text="选择一篇文章开始阅读" />
    </section>
  </div>
</template>

<style scoped>
.article-content {
  font-family: var(--font-body);
  font-size: 17px;
  line-height: 1.8;
  color: var(--text-primary);
  max-width: 680px;
  margin: 0 auto;
  word-wrap: break-word;
}
.article-content :deep(img) { max-width: 100%; border-radius: 8px; margin: 12px 0; height: auto; }
.article-content :deep(p) { margin-bottom: 16px; }
.article-content :deep(blockquote) {
  border-left: 3px solid var(--accent);
  padding-left: 16px;
  color: var(--text-secondary);
  margin: 16px 0;
}
.article-content :deep(pre) {
  background: var(--bg-secondary);
  padding: 14px;
  border-radius: var(--radius-md);
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: 14px;
}
.article-content :deep(a) { color: var(--accent); }
.article-content :deep(h1), .article-content :deep(h2), .article-content :deep(h3) {
  margin: 24px 0 12px;
  font-weight: 700;
  line-height: 1.3;
}
.article-content :deep(ul), .article-content :deep(ol) { padding-left: 24px; margin: 12px 0; }
.article-content :deep(li) { margin-bottom: 4px; }
</style>
