import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
  { path: '/browse', name: 'browse', component: () => import('@/views/BrowseView.vue') },
  { path: '/rss', name: 'rss', component: () => import('@/views/RssManageView.vue') },
  { path: '/ingestion', name: 'ingestion', component: () => import('@/views/IngestionView.vue') },
  { path: '/logs', name: 'logs', component: () => import('@/views/LogsView.vue') },
  { path: '/backup', name: 'backup', component: () => import('@/views/BackupView.vue') },
  { path: '/settings/:tab?', name: 'settings', component: () => import('@/views/SettingsView.vue') },
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
  { path: '/verify', name: 'verify', component: () => import('@/views/VerifyView.vue') },
  { path: '/status', name: 'status', component: () => import('@/views/StatusView.vue') },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
