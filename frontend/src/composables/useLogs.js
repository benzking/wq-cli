import { ref, readonly, computed } from 'vue'

export function useLogs() {
  const logs = ref([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(50)
  const level = ref('')
  const module = ref('')
  const keyword = ref('')
  const since = ref(null)
  const until = ref(null)
  const loading = ref(false)
  const modules = ref([])
  const autoRefresh = ref(false)
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage.value)))

  let _timer = null

  async function loadLogs() {
    loading.value = true
    try {
      const params = new URLSearchParams({ page: page.value, per_page: perPage.value })
      if (level.value) params.set('level', level.value)
      if (module.value) params.set('module', module.value)
      if (keyword.value) params.set('keyword', keyword.value)
      if (since.value) params.set('since', since.value)
      if (until.value) params.set('until', until.value)
      const res = await fetch(`/api/admin/logs?${params}`)
      const data = await res.json()
      if (data.success) { logs.value = data.data.logs; total.value = data.data.total }
    } finally { loading.value = false }
  }

  async function loadModules() {
    const res = await fetch('/api/admin/logs/modules')
    const data = await res.json()
    if (data.success) modules.value = data.data.modules || []
  }

  function changePage(p) { page.value = p; loadLogs() }
  function reset() { level.value = ''; module.value = ''; keyword.value = ''; since.value = null; until.value = null; page.value = 1; loadLogs() }

  function toggleAutoRefresh(val) {
    autoRefresh.value = val
    if (val) { _timer = setInterval(loadLogs, 10000) }
    else { if (_timer) clearInterval(_timer); _timer = null }
  }

  async function cleanupDays(days) {
    await fetch(`/api/admin/logs/cleanup?retain_days=${days}`, { method: 'POST' })
    loadLogs()
  }

  return {
    logs: readonly(logs), total: readonly(total), page: readonly(page), totalPages,
    level, module, keyword, since, until, loading: readonly(loading), modules: readonly(modules),
    autoRefresh, loadLogs, loadModules, changePage, reset, toggleAutoRefresh, cleanupDays,
  }
}
