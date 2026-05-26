<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TabsBar from '@/components/TabsBar.vue'
import ProxySettings from '@/components/settings/ProxySettings.vue'
import BlacklistSettings from '@/components/settings/BlacklistSettings.vue'
import CategorySettings from '@/components/settings/CategorySettings.vue'
import HistorySettings from '@/components/settings/HistorySettings.vue'

const route = useRoute()
const router = useRouter()

const tabs = [
  { key: 'proxy', label: '回落配置' },
  { key: 'blacklist', label: '黑名单' },
  { key: 'categories', label: '分类管理' },
  { key: 'history', label: '历史获取' },
]

const activeTab = ref(route.params.tab || 'proxy')
watch(() => route.params.tab, (v) => { if (v) activeTab.value = v })

function switchTab(key) {
  activeTab.value = key
  router.replace(`/settings/${key}`)
}
</script>

<template>
  <div class="settings-page">
    <h2 class="page-title">设置</h2>
    <TabsBar :tabs="tabs" :model-value="activeTab" @update:model-value="switchTab" />

    <div class="mt-2">
      <ProxySettings v-if="activeTab === 'proxy'" />
      <BlacklistSettings v-if="activeTab === 'blacklist'" />
      <CategorySettings v-if="activeTab === 'categories'" />
      <HistorySettings v-if="activeTab === 'history'" />
    </div>
  </div>
</template>

