import { ref, readonly } from 'vue'

export function useBackup() {
  const backups = ref([])
  const loading = ref(false)
  const exporting = ref(false)
  const importing = ref(false)

  async function loadList() {
    loading.value = true
    try {
      const res = await fetch('/api/admin/backup/list')
      const data = await res.json()
      if (data.success) { backups.value = data.data || [] }
    } finally { loading.value = false }
  }

  async function doExport() {
    exporting.value = true
    try {
      const res = await fetch('/api/admin/backup/export', { method: 'POST' })
      if (!res.ok) throw new Error('导出失败')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = 'backup.zip'; a.click()
      URL.revokeObjectURL(url)
    } finally { exporting.value = false }
  }

  async function doImport(file) {
    importing.value = true
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/admin/backup/import/upload', { method: 'POST', body: form })
      const data = await res.json()
      return data
    } finally { importing.value = false; loadList() }
  }

  async function doDelete(path) {
    await fetch(`/api/admin/backup/delete?path=${encodeURIComponent(path)}`, { method: 'DELETE' })
    loadList()
  }

  return { backups: readonly(backups), loading: readonly(loading), exporting: readonly(exporting), importing: readonly(importing), loadList, doExport, doImport, doDelete }
}
