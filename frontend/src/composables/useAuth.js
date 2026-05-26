import { ref, readonly } from 'vue'

const user = ref({
  authenticated: false,
  nickname: '',
  fakeid: '',
  expireTime: 0,
})

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

  async function logout() {
    await fetch('/api/admin/logout', { method: 'POST' })
    user.value = { authenticated: false, nickname: '', fakeid: '', expireTime: 0 }
  }

  function startAutoRefresh(intervalMs = 30000) {
    stopAutoRefresh()
    _refreshTimer = setInterval(refresh, intervalMs)
  }

  function stopAutoRefresh() {
    if (_refreshTimer) { clearInterval(_refreshTimer); _refreshTimer = null }
  }

  return {
    user: readonly(user),
    refresh,
    logout,
    startAutoRefresh,
    stopAutoRefresh,
  }
}
