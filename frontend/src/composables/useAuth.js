import { ref, readonly } from 'vue'

const user = ref({
  authenticated: false,
  nickname: '',
  fakeid: '',
  expireTime: 0,
})

const accounts = ref([])
const alertStatus = ref(null)

let _refreshTimer = null

export function useAuth() {
  async function refresh() {
    try {
      const res = await fetch('/api/admin/status')
      const data = await res.json()
      user.value = {
        authenticated: data.authenticated || data.loggedIn || false,
        nickname: data.nickname || '',
        fakeid: data.fakeid || '',
        expireTime: data.expireTime || 0,
      }
    } catch {
      // 静默失败，保留上一次状态
    }
  }

  async function loadAccounts() {
    try {
      const res = await fetch('/api/admin/accounts')
      const data = await res.json()
      if (data.success) accounts.value = data.data || []
    } catch {}
  }

  async function loadAlertStatus() {
    try {
      const res = await fetch('/api/admin/alert-status')
      const data = await res.json()
      if (data.success) alertStatus.value = data.data || null
    } catch {}
  }

  async function activateAccount(fakeid) {
    const res = await fetch(`/api/admin/accounts/${fakeid}/activate`, { method: 'POST' })
    const data = await res.json()
    if (data.success) await refresh()
    return data
  }

  async function deleteAccount(fakeid) {
    const res = await fetch(`/api/admin/accounts/${fakeid}`, { method: 'DELETE' })
    const data = await res.json()
    if (data.success) {
      await loadAccounts()
      await refresh()
    }
    return data
  }

  async function logout() {
    await fetch('/api/admin/logout', { method: 'POST' })
    user.value = { authenticated: false, nickname: '', fakeid: '', expireTime: 0 }
    await loadAccounts()
  }

  function startAutoRefresh(intervalMs = 30000) {
    stopAutoRefresh()
    _refreshTimer = setInterval(() => { refresh(); loadAlertStatus() }, intervalMs)
  }

  function stopAutoRefresh() {
    if (_refreshTimer) { clearInterval(_refreshTimer); _refreshTimer = null }
  }

  return {
    user: readonly(user),
    accounts: readonly(accounts),
    alertStatus: readonly(alertStatus),
    refresh,
    loadAccounts,
    loadAlertStatus,
    activateAccount,
    deleteAccount,
    logout,
    startAutoRefresh,
    stopAutoRefresh,
  }
}
