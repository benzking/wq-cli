import { ref, readonly } from 'vue'

export function useDashboard() {
  const stats = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function refresh() {
    loading.value = true
    error.value = null
    try {
      const res = await fetch('/api/admin/dashboard')
      const data = await res.json()
      if (data.success) {
        stats.value = data.data
      } else {
        error.value = data.error || '加载失败'
      }
    } catch (e) {
      error.value = '网络异常'
    } finally {
      loading.value = false
    }
  }

  return { stats: readonly(stats), loading: readonly(loading), error: readonly(error), refresh }
}
