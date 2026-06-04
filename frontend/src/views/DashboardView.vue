<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboard } from '@/composables/useDashboard'
import { useAuth } from '@/composables/useAuth'
import StatCard from '@/components/StatCard.vue'
import DataTable from '@/components/DataTable.vue'

const router = useRouter()
const { stats, loading, refresh } = useDashboard()
const { alertStatus } = useAuth()
onMounted(refresh)

const recentFailColumns = [
  { key: 'nickname', label: '公众号' },
  { key: 'article_link', label: '文章链接' },
  { key: 'error_msg', label: '原因' },
  { key: 'updated_at', label: '时间' },
]

function goLogin() {
  router.push('/login')
}

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="dashboard">
    <Teleport to="#topbar-title">
      <h1 class="text-[20px] font-bold text-text-primary">数据看板</h1>
    </Teleport>

    <div class="stats-grid">
      <div
        @click="(alertStatus?.credential_expired || alertStatus?.credential_expiring_soon) ? goLogin() : null"
        :class="{ 'cursor-pointer': alertStatus?.credential_expired || alertStatus?.credential_expiring_soon }"
        class="hover:-translate-y-0.5 hover:shadow-md transition-transform transition-shadow duration-150"
      >
        <StatCard
          label="在线状态"
          :value="alertStatus?.credential_expired ? '凭据已过期' : (alertStatus?.credential_expiring_soon ? '凭据即将过期' : (stats?.online ? '已认证' : '离线'))"
          :sub="alertStatus?.credential_expiring_soon ? (stats?.nickname + ' (还剩 ' + alertStatus.credential_hours_left + ' 小时)') : (stats?.nickname || '')"
          :accent="alertStatus?.credential_expired ? '#c92a2a' : (alertStatus?.credential_expiring_soon ? '#e67700' : (stats?.online ? '#2f9e44' : '#adb5bd'))"
        />
      </div>
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
