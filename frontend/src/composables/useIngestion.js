import { ref, readonly, computed } from 'vue'

export function useIngestion() {
  const stats = ref(null)
  const logs = ref([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(30)
  const status = ref('')
  const channel = ref('')
  const keyword = ref('')
  const loading = ref(false)
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage.value)))

  async function loadStats() {
    try {
      const res = await fetch('/api/admin/ingestion/stats')
      const data = await res.json()
      if (data.success) { stats.value = data.data }
    } catch {}
  }

  async function loadLogs() {
    loading.value = true
    try {
      const params = new URLSearchParams({ page: page.value, per_page: perPage.value })
      if (status.value) params.set('status', status.value)
      if (channel.value) params.set('channel', channel.value)
      if (keyword.value) params.set('keyword', keyword.value)
      const res = await fetch(`/api/admin/ingestion?${params}`)
      const data = await res.json()
      if (data.success) { logs.value = data.data.logs; total.value = data.data.total }
    } finally { loading.value = false }
  }

  function changePage(p) { page.value = p; loadLogs() }
  function reset() { status.value = ''; channel.value = ''; keyword.value = ''; page.value = 1; loadLogs() }

  return {
    stats: readonly(stats), logs: readonly(logs), total: readonly(total),
    page: readonly(page), totalPages, status, channel, keyword,
    loading: readonly(loading), loadStats, loadLogs, changePage, reset,
  }
}
