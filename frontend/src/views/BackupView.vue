<script setup>
import { onMounted, ref, inject } from 'vue'
import { useBackup } from '@/composables/useBackup'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'

const toast = inject('toast')
const { backups, loading, exporting, importing, loadList, doExport, doImport, doDelete } = useBackup()

const showConfirm = ref(false)
const deleteTarget = ref(null)
const dragOver = ref(false)

onMounted(loadList)

async function handleExport() { await doExport(); toast.success('备份已创建') }

async function handleImport(e) {
  const file = e.target.files?.[0] || e.dataTransfer?.files?.[0]
  if (!file) return
  if (!file.name.endsWith('.zip')) { toast.error('仅支持 .zip 文件'); return }
  const data = await doImport(file)
  toast[data?.success ? 'success' : 'error'](data?.success ? '导入成功' : (data?.error || '导入失败'))
}

function promptDelete(path) { deleteTarget.value = path; showConfirm.value = true }
async function confirmDelete() { await doDelete(deleteTarget.value); toast.success('已删除'); showConfirm.value = false }

function onDragEnter(e) { e.preventDefault(); dragOver.value = true }
function onDragLeave() { dragOver.value = false }
function onDragOver(e) { e.preventDefault() }
function onDrop(e) { e.preventDefault(); dragOver.value = false; handleImport(e) }

function formatSize(bytes) { return bytes ? (bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`) : '-' }
function formatTime(ts) { return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-' }
</script>

<template>
  <div class="backup-page">
    <Teleport to="#topbar-title">
      <h1 class="text-[20px] font-bold text-text-primary">备份管理</h1>
    </Teleport>

    <div class="export-section">
      <button class="btn btn-primary" @click="handleExport" :disabled="exporting">{{ exporting ? '导出中...' : '导出备份' }}</button>
      <span class="hint">导出数据库及设置文件</span>
    </div>

    <div
      class="border-2 border-dashed border-border-base rounded-lg p-[30px] text-center mb-6 transition-colors duration-150 cursor-pointer"
      :class="{ '!border-accent !bg-accent-light': dragOver }"
      @dragenter="onDragEnter" @dragleave="onDragLeave" @dragover="onDragOver" @drop="onDrop"
    >
      <p class="text-[13px] text-text-muted mb-2">{{ importing ? '导入中...' : '拖拽 .zip 备份文件到此处' }}</p>
      <label class="text-[13px] text-accent cursor-pointer underline">
        <input type="file" accept=".zip" @change="handleImport" style="display:none" />
        选择文件
      </label>
    </div>

    <section class="section">
      <h3>备份历史</h3>
      <SkeletonLoader v-if="loading" :lines="3" />
      <EmptyState v-else-if="!backups.length" text="暂无备份记录" />
      <div v-else class="table-wrap">
        <table>
          <thead><tr><th>文件名</th><th>大小</th><th>日期</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="b in backups" :key="b.path || b.name">
              <td>{{ b.name || b.path }}</td>
              <td>{{ formatSize(b.size) }}</td>
              <td>{{ formatTime(b.created_at || b.mtime) }}</td>
              <td>
                <a :href="`/api/admin/backup/download?path=${encodeURIComponent(b.path || b.name)}`" class="btn btn-sm">下载</a>
                <button class="btn btn-sm !text-error" @click="promptDelete(b.path || b.name)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <ConfirmModal :show="showConfirm" title="确认删除" message="确定要删除此备份吗？此操作不可撤销。" @confirm="confirmDelete" @cancel="showConfirm = false" />
  </div>
</template>

<style scoped>
.export-section { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.hint { font-size: 12px; color: var(--text-muted); }
.section h3 { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
</style>
