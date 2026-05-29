import { ref, readonly, computed } from 'vue'

export function useIngestion() {
  const stats = ref(null)
  const workerStatus = ref(null)
  const logs = ref([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(30)
  const status = ref('')
  const channel = ref('')
  const keyword = ref('')
  const fakeid = ref('')
  const loading = ref(false)
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage.value)))

  async function loadStats() {
    try {
      const [sRes, wRes] = await Promise.all([
        fetch('/api/admin/ingestion/stats'),
        fetch('/api/admin/ingestion/worker-status'),
      ])
      const sData = await sRes.json()
      if (sData.success) stats.value = sData.data
      const wData = await wRes.json()
      if (wData.success) workerStatus.value = wData.data
    } catch {}
  }

  async function loadLogs() {
    loading.value = true
    try {
      const params = new URLSearchParams({ page: page.value, per_page: perPage.value })
      if (status.value) params.set('status', status.value)
      if (channel.value) params.set('channel', channel.value)
      if (keyword.value) params.set('keyword', keyword.value)
      if (fakeid.value) params.set('fakeid', fakeid.value)
      const res = await fetch(`/api/admin/ingestion?${params}`)
      const data = await res.json()
      if (data.success) { logs.value = data.data.logs; total.value = data.data.total }
    } finally { loading.value = false }
  }

  function changePage(p) { page.value = p; loadLogs() }
  function reset() { page.value = 1; loadLogs() }

  async function retryArticle(fakeid, link) {
    const res = await fetch('/api/admin/ingestion/retry', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fakeid, article_links: [link], limit: 1 }),
    })
    return (await res.json()).success
  }

  async function banArticle(fakeid, link) {
    const res = await fetch('/api/admin/ingestion/ban', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fakeid, article_link: link }),
    })
    return (await res.json()).success
  }

  async function unbanArticle(fakeid, link) {
    const res = await fetch('/api/admin/ingestion/unban', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fakeid, article_link: link }),
    })
    return (await res.json()).success
  }

  return {
    stats: readonly(stats), workerStatus: readonly(workerStatus),
    logs: readonly(logs), total: readonly(total),
    page: readonly(page), totalPages,
    status, channel, keyword, fakeid,
    loading: readonly(loading),
    loadStats, loadLogs, changePage, reset,
    retryArticle, banArticle, unbanArticle,
  }
}
