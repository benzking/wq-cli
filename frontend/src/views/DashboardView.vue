<script setup>
import { onMounted } from 'vue'
import { useDashboard } from '@/composables/useDashboard'
import StatCard from '@/components/StatCard.vue'
import DataTable from '@/components/DataTable.vue'

const { stats, loading, refresh } = useDashboard()
onMounted(refresh)

const recentFailColumns = [
  { key: 'nickname', label: '公众号' },
  { key: 'article_link', label: '文章链接' },
  { key: 'error_msg', label: '原因' },
  { key: 'updated_at', label: '时间' },
]

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="dashboard">
    <h2 class="page-title">数据看板</h2>

    <div class="stats-grid">
      <StatCard
        label="在线状态"
        :value="stats?.online ? '已认证' : '离线'"
        :sub="stats?.nickname || ''"
        :accent="stats?.online ? '#2f9e44' : '#adb5bd'"
      />
      <StatCard label="累计入库" :value="(stats?.total_articles ?? '-').toLocaleString()" sub="文章总数" />
      <StatCard
        label="今日入库"
        :value="stats?.today_ingested != null ? `+${stats.today_ingested}` : '-'"
        :sub="stats != null ? `成功 ${stats.today_ingested ?? 0} · 失败 ${stats.today_failed ?? 0} · 成功率 ${Math.round((stats.ingestion_rate ?? 0) * 100)}%` : ''"
      />
      <StatCard label="已订阅公众号" :value="stats?.subscription_count ?? '-'" sub="个公众号" />
      <StatCard label="待处理队列" :value="stats?.pending_count ?? '-'" sub="条待抓取" />
      <StatCard label="今日有更新" :value="stats?.today_active_accounts ?? '-'" sub="个公众号" />
    </div>

    <section class="section">
      <h3>最近失败</h3>
      <DataTable :columns="recentFailColumns" :rows="stats?.recent_failures || []" :loading="loading" empty-text="暂无失败记录">
        <template #cell-article_link="{ value }">
          <span class="link-ellipsis" :title="value">{{ value }}</span>
        </template>
        <template #cell-error_msg="{ value }">
          <span class="error-msg" :title="value">{{ value }}</span>
        </template>
        <template #cell-updated_at="{ value }">
          {{ formatTime(value) }}
        </template>
      </DataTable>
    </section>
  </div>
</template>

<style scoped>
.page-title { font-size: 20px; font-weight: 700; margin-bottom: 20px; }
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 28px;
}
.section h3 { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.link-ellipsis {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}
.error-msg {
  color: var(--error);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}
@media (max-width: 1024px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .stats-grid { grid-template-columns: 1fr; } }
</style>
