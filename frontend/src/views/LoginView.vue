<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { inject } from 'vue'
import { useAuth } from '@/composables/useAuth'

const toast = inject('toast')
const router = useRouter()
const { accounts, loadAccounts, activateAccount, deleteAccount } = useAuth()

const accountList = computed(() => accounts.value || [])

const qrcodeUrl = ref('')
const statusText = ref('')
const loading = ref(false)
const scanningFor = ref(null)

let sessionId = null
let pollTimer = null
let qrcodeBlobUrl = null

function generateSessionId() {
  return 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
}

async function startQrScan(fakeid = null, nickname = null) {
  stopPoll()
  loading.value = true
  scanningFor.value = fakeid ? { fakeid, nickname } : null
  statusText.value = '正在获取二维码...'
  qrcodeUrl.value = ''
  try {
    sessionId = generateSessionId()
    const body = fakeid ? JSON.stringify({ fakeid }) : undefined
    await fetch(`/api/login/session/${sessionId}`, {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body,
    })
    await loadQrcode()
    startPoll()
  } catch (e) {
    statusText.value = '初始化失败: ' + e.message
    loading.value = false
  }
}

async function loadQrcode() {
  try {
    const res = await fetch('/api/login/getqrcode')
    if (!res.ok) throw new Error('获取二维码失败')
    const blob = await res.blob()
    if (qrcodeBlobUrl) URL.revokeObjectURL(qrcodeBlobUrl)
    qrcodeBlobUrl = URL.createObjectURL(blob)
    qrcodeUrl.value = qrcodeBlobUrl
    statusText.value = scanningFor.value
      ? `请使用微信扫描二维码（更新 ${scanningFor.value.nickname}）`
      : '请使用微信扫描二维码'
    loading.value = false
  } catch (e) {
    statusText.value = '加载二维码失败，请刷新重试'
    loading.value = false
  }
}

async function checkScan() {
  try {
    const res = await fetch('/api/login/scan')
    const data = await res.json()
    if (data.status === 1) {
      statusText.value = '已扫码，正在登录...'
      stopPoll()
      const bizRes = await fetch('/api/login/bizlogin', { method: 'POST' })
      const bizData = await bizRes.json()
      if (bizData.success || bizData.base_resp?.ret === 0) {
        toast.success(scanningFor.value ? '凭据已更新' : '登录成功')
        await loadAccounts()
        setTimeout(() => router.push('/'), 500)
      } else {
        statusText.value = '登录失败，请重试'
        toast.error('登录失败')
        startPoll()
      }
    } else if (data.status === 2) {
      statusText.value = '二维码已过期，点击刷新'
      stopPoll()
    } else if (data.status === 3) {
      statusText.value = '登录失败，请重试'
    } else if (data.status === 4 || data.status === 6) {
      statusText.value = '请在手机上确认登录'
    }
  } catch {
    // 轮询失败，继续尝试
  }
}

function startPoll() { stopPoll(); pollTimer = setInterval(checkScan, 2000) }
function stopPoll() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

function handleRefresh() {
  if (loading.value) return
  loading.value = true
  if (qrcodeBlobUrl) { URL.revokeObjectURL(qrcodeBlobUrl); qrcodeBlobUrl = null }
  qrcodeUrl.value = ''
  startQrScan(scanningFor.value?.fakeid, scanningFor.value?.nickname)
}

function handleRescan(account) { startQrScan(account.fakeid, account.nickname) }
function handleNewLogin() { startQrScan(null, null) }

async function handleActivate(account) {
  const r = await activateAccount(account.fakeid)
  toast[r.success ? 'success' : 'error'](r.success ? `已切换到 ${account.nickname}` : (r.error || '切换失败'))
}

async function handleDelete(account) {
  if (!confirm(`确定删除 ${account.nickname} 的登录记录吗？`)) return
  const r = await deleteAccount(account.fakeid)
  toast[r.success ? 'success' : 'error'](r.success ? '已删除' : (r.error || '删除失败'))
}

function statusLabel(account) {
  if (account.is_expired) return { text: '已过期', cls: 'status-expired' }
  const now = Date.now()
  const expireMs = account.expire_time
  if (expireMs > 0) {
    const hoursLeft = (expireMs - now) / 3600000
    if (hoursLeft <= 24) return { text: '即将过期', cls: 'status-warning' }
  }
  return { text: '正常', cls: 'status-ok' }
}

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function onVisibilityChange() {
  if (document.hidden) stopPoll()
  else { checkScan(); startPoll() }
}

onMounted(() => {
  loadAccounts()
  startQrScan(null, null)
  document.addEventListener('visibilitychange', onVisibilityChange)
})
onUnmounted(() => {
  stopPoll()
  document.removeEventListener('visibilitychange', onVisibilityChange)
  if (qrcodeBlobUrl) URL.revokeObjectURL(qrcodeBlobUrl)
})
</script>

<template>
  <div class="login-page">
    <div class="login-layout">
      <div class="account-panel">
        <div class="panel-header">
          <h2>已登录的公众号</h2>
          <button class="btn-new" @click="handleNewLogin">+ 登录新公众号</button>
        </div>
        <div v-if="!accountList.length" class="empty-hint">暂无登录记录，请扫描二维码登录</div>
        <div v-else class="account-list">
          <div v-for="a in accountList" :key="a.fakeid" class="account-item" :class="{ 'is-active': a.is_active }">
            <div class="acct-avatar">
              <img v-if="a.head_img" :src="a.head_img" class="avatar-img" />
              <span v-else class="avatar-placeholder">{{ (a.nickname || a.alias || '').charAt(0) }}</span>
            </div>
            <div class="acct-info">
              <div class="acct-name">
                {{ a.nickname || a.alias || '未知' }}
                <span v-if="a.is_active" class="active-tag">当前</span>
              </div>
              <div class="acct-meta">
                <span class="acct-fakeid">{{ (a.fakeid || '').slice(0, 16) }}...</span>
                <span class="acct-time">上次登录 {{ formatTime(a.login_time) }}</span>
              </div>
            </div>
            <span class="status-tag" :class="statusLabel(a).cls">{{ statusLabel(a).text }}</span>
            <div class="acct-actions">
              <button v-if="!a.is_active" class="btn-sm" @click="handleActivate(a)">切换</button>
              <button class="btn-sm" @click="handleRescan(a)">重新扫码</button>
              <button class="btn-sm btn-danger-text" @click="handleDelete(a)">删除</button>
            </div>
          </div>
        </div>
      </div>

      <div class="qr-panel">
        <div class="qr-card">
          <h2 v-if="scanningFor" class="qr-title">更新 {{ scanningFor.nickname }} 凭据</h2>
          <h2 v-else class="qr-title">登录新公众号</h2>
          <p class="qr-hint">使用微信扫描二维码登录微信公众号后台</p>
          <div class="qr-img-wrapper">
            <img v-if="qrcodeUrl" :src="qrcodeUrl" alt="登录二维码" class="qr-img" />
            <div v-else class="qr-placeholder">{{ loading ? '加载中...' : '二维码加载失败' }}</div>
          </div>
          <p class="qr-status">{{ statusText }}</p>
          <button class="btn-refresh" @click="handleRefresh">刷新二维码</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page { max-width: 1040px; margin: 0 auto; padding: 24px; }
.login-layout { display: flex; gap: 24px; align-items: flex-start; }

.account-panel { flex: 1; min-width: 0; background: var(--bg-primary); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 20px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.panel-header h2 { font-size: 16px; font-weight: 600; }
.btn-new { padding: 6px 14px; background: var(--accent); color: #fff; border: none; border-radius: var(--radius-sm); font-size: 13px; cursor: pointer; }
.btn-new:hover { opacity: 0.85; }
.empty-hint { color: var(--text-muted); font-size: 13px; text-align: center; padding: 32px 0; }
.account-list { display: flex; flex-direction: column; gap: 8px; }
.account-item { display: flex; align-items: center; gap: 12px; padding: 12px; border: 1px solid var(--border-light); border-radius: var(--radius-md); }
.account-item.is-active { border-color: var(--accent); background: var(--accent-light); }
.acct-avatar { width: 36px; height: 36px; flex-shrink: 0; }
.avatar-img { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; }
.avatar-placeholder { width: 36px; height: 36px; border-radius: 50%; background: var(--accent-light); display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; color: var(--accent); }
.acct-info { flex: 1; min-width: 0; }
.acct-name { font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.active-tag { font-size: 10px; padding: 1px 6px; background: var(--accent); color: #fff; border-radius: 10px; }
.acct-meta { font-size: 11px; color: var(--text-muted); margin-top: 2px; display: flex; gap: 10px; }
.status-tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; flex-shrink: 0; }
.status-ok { background: #d3f9d8; color: #2f9e44; }
.status-warning { background: #fff3bf; color: #e67700; }
.status-expired { background: #ffe3e3; color: #c92a2a; }
.acct-actions { display: flex; gap: 4px; flex-shrink: 0; }
.btn-sm { padding: 4px 10px; border: 1px solid var(--border-base); background: var(--bg-primary); border-radius: var(--radius-sm); font-size: 11px; cursor: pointer; color: var(--text-secondary); }
.btn-sm:hover { border-color: var(--accent); color: var(--accent); }
.btn-danger-text { border-color: transparent; color: var(--error); }
.btn-danger-text:hover { background: #ffe3e3; }

.qr-panel { width: 340px; flex-shrink: 0; }
.qr-card { background: var(--bg-primary); border: 1px solid var(--border-light); border-radius: var(--radius-lg); padding: 30px 20px; text-align: center; }
.qr-title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.qr-hint { font-size: 12px; color: var(--text-muted); margin-bottom: 16px; }
.qr-img-wrapper { width: 200px; height: 200px; margin: 0 auto 16px; border: 1px solid var(--border-light); border-radius: var(--radius-md); overflow: hidden; display: flex; align-items: center; justify-content: center; }
.qr-img { width: 100%; height: 100%; object-fit: contain; }
.qr-placeholder { font-size: 12px; color: var(--text-muted); }
.qr-status { font-size: 12px; color: var(--text-secondary); min-height: 18px; margin-bottom: 12px; }
.btn-refresh { padding: 6px 18px; border: 1px solid var(--border-base); background: var(--bg-primary); border-radius: var(--radius-sm); font-size: 12px; cursor: pointer; color: var(--text-secondary); }
.btn-refresh:hover { border-color: var(--accent); color: var(--accent); }

@media (max-width: 768px) {
  .login-layout { flex-direction: column-reverse; }
  .qr-panel { width: 100%; }
}
</style>
