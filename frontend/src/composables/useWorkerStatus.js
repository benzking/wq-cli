import { ref, readonly } from 'vue'

export function useWorkerStatus() {
  const worker = ref(null)
  const poller = ref(null)

  async function refresh() {
    const [wRes, pRes] = await Promise.all([
      fetch('/api/admin/ingestion/worker-status'),
      fetch('/api/rss/status'),
    ])
    if (wRes.ok) {
      const d = await wRes.json()
      if (d.success) worker.value = d.data
    }
    if (pRes.ok) {
      const d = await pRes.json()
      if (d.success) poller.value = d.data
    }
  }

  return { worker: readonly(worker), poller: readonly(poller), refresh }
}
