import { ref, readonly } from 'vue'

export function useRss() {
  const subscriptions = ref([])
  const searchResults = ref([])
  const query = ref('')
  const loading = ref(false)
  const searchLoading = ref(false)
  const pollerStatus = ref({ running: false, next_poll: null })

  async function loadSubscriptions() {
    loading.value = true
    try {
      const res = await fetch('/api/rss/subscriptions')
      const data = await res.json()
      if (data.success) { subscriptions.value = data.data || [] }
    } finally { loading.value = false }
  }

  async function loadStatus() {
    try {
      const res = await fetch('/api/rss/status')
      const data = await res.json()
      if (data.success) { pollerStatus.value = data.data || {} }
    } catch {}
  }

  async function searchBiz(nickname) {
    if (!nickname) { searchResults.value = []; return }
    searchLoading.value = true
    try {
      const res = await fetch(`/api/public/searchbiz?query=${encodeURIComponent(nickname)}`)
      const data = await res.json()
      searchResults.value = data.data?.list || []
    } finally { searchLoading.value = false }
  }

  async function subscribe(fakeid, nickname = '', alias = '', headImg = '') {
    const res = await fetch('/api/rss/subscribe', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fakeid, nickname, alias, head_img: headImg }),
    })
    const data = await res.json()
    if (data.success) { await loadSubscriptions() }
    return data
  }

  async function unsubscribe(fakeid) {
    const res = await fetch(`/api/rss/subscribe/${fakeid}`, { method: 'DELETE' })
    const data = await res.json()
    if (data.success) { await loadSubscriptions() }
    return data
  }

  async function setCategory(fakeid, categoryId) {
    await fetch(`/api/admin/subscriptions/${fakeid}/category`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category_id: categoryId }),
    })
  }

  async function triggerPoll() {
    const res = await fetch('/api/rss/poll', { method: 'POST' })
    return res.json()
  }

  function exportUrl(format) { return `/api/rss/export?format=${format}` }

  return {
    subscriptions: readonly(subscriptions), searchResults: readonly(searchResults),
    query, loading: readonly(loading), searchLoading: readonly(searchLoading),
    pollerStatus: readonly(pollerStatus),
    loadSubscriptions, loadStatus, searchBiz, subscribe, unsubscribe, setCategory, triggerPoll, exportUrl,
  }
}
