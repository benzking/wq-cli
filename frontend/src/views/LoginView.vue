<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { inject } from 'vue'

const toast = inject('toast')
const router = useRouter()

const qrcodeUrl = ref('')
const statusText = ref('正在获取二维码...')
const loading = ref(true)
let sessionId = null
let pollTimer = null
let qrcodeBlobUrl = null

function generateSessionId() {
  return 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
}

async function initLogin() {
  try {
    sessionId = generateSessionId()
    await fetch(`/api/login/session/${sessionId}`, { method: 'POST' })
    await loadQrcode()
    startPoll()
  } catch (e) {
    statusText.value = '初始化登录失败: ' + e.message
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
    statusText.value = '请使用微信扫描二维码'
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
        toast.success('登录成功')
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

function startPoll() {
  stopPoll()
  pollTimer = setInterval(checkScan, 2000)
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function handleRefresh() {
  if (loading.value) return
  loading.value = true
  if (qrcodeBlobUrl) { URL.revokeObjectURL(qrcodeBlobUrl); qrcodeBlobUrl = null }
  qrcodeUrl.value = ''
  initLogin()
}

function onVisibilityChange() {
  if (document.hidden) { stopPoll() }
  else { checkScan(); startPoll() }
}

onMounted(() => { initLogin(); document.addEventListener('visibilitychange', onVisibilityChange) })
onUnmounted(() => { stopPoll(); document.removeEventListener('visibilitychange', onVisibilityChange); if (qrcodeBlobUrl) URL.revokeObjectURL(qrcodeBlobUrl) })
</script>

<template>
  <div class="flex items-center justify-center min-h-[70vh]">
    <div class="bg-bg-primary border border-border-light rounded-lg shadow-lg p-10 text-center max-w-[360px] w-full">
      <h2 class="text-[22px] mb-2">扫码登录</h2>
      <p class="text-[13px] text-text-muted mb-6">使用微信扫描二维码登录微信公众号后台</p>
      <div class="w-[220px] h-[220px] mx-auto mb-5 border border-border-light rounded-md flex items-center justify-center overflow-hidden">
        <img v-if="qrcodeUrl" :src="qrcodeUrl" alt="登录二维码" class="w-full h-full object-contain" />
        <div v-else class="text-[13px] text-text-muted">{{ loading ? '加载中...' : '二维码加载失败' }}</div>
      </div>
      <p class="text-[13px] text-text-secondary mb-4 min-h-5">{{ statusText }}</p>
      <button class="py-2 px-5 border border-border-base rounded-sm bg-bg-primary text-[13px] cursor-pointer text-text-secondary hover:border-accent hover:text-accent" @click="handleRefresh">刷新二维码</button>
    </div>
  </div>
</template>
