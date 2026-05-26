<script setup>
import { ref } from 'vue'

const articleUrl = ref('')

function openVerify() {
  const url = articleUrl.value.trim()
  if (!url) return
  if (!url.includes('mp.weixin.qq.com')) {
    alert('请输入有效的微信公众号文章链接')
    return
  }
  window.open(url, '_blank')
}
</script>

<template>
  <div class="verify-page">
    <h2 class="page-title">验证码处理</h2>

    <div class="bg-bg-primary border border-border-light rounded-lg p-[30px] max-w-[600px]">
      <div v-for="(step, idx) in [
        { title: '粘贴文章链接', desc: '在下方输入框中粘贴需要验证的微信公众号文章 URL' },
        { title: '在新窗口中打开', desc: '点击按钮在新窗口打开文章页面，浏览器会展示微信安全验证' },
        { title: '完成验证', desc: '在打开的页面中完成验证码输入，确认后可关闭该窗口' },
        { title: '等待恢复', desc: '验证通过后 Cookie 自动更新，建议等待 5-10 分钟后重新操作' },
      ]" :key="idx" class="flex gap-3.5 mb-5">
        <div class="w-7 h-7 rounded-full bg-accent text-white text-[13px] font-bold flex items-center justify-center shrink-0">
          {{ idx + 1 }}
        </div>
        <div>
          <div class="text-sm font-semibold mb-0.5">{{ step.title }}</div>
          <div class="text-[13px] text-text-muted leading-[1.5]">{{ step.desc }}</div>
        </div>
      </div>

      <div class="flex gap-2 mt-6">
        <input
          v-model="articleUrl"
          type="text"
          placeholder="粘贴微信公众号文章链接..."
          class="flex-1 py-2.5 px-3.5 border border-border-base rounded-md text-sm outline-none transition-colors duration-150 focus:border-accent focus:shadow-[0_0_0_2px_var(--accent-light)]"
          @keyup.enter="openVerify"
        />
        <button class="btn btn-primary" @click="openVerify">在新窗口中打开</button>
      </div>
    </div>
  </div>
</template>
