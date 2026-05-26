import { ref, readonly } from 'vue'

let _id = 0
const toasts = ref([])

export function useToast() {
  function show(message, type = 'info', duration = 3000) {
    const id = ++_id
    toasts.value = [...toasts.value, { id, message, type }]
    if (type !== 'error' && duration > 0) {
      setTimeout(() => remove(id), duration)
    }
  }

  function remove(id) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  function success(msg) { show(msg, 'success') }
  function error(msg) { show(msg, 'error', 0) }
  function warning(msg) { show(msg, 'warning') }
  function info(msg) { show(msg, 'info') }

  return { toasts: readonly(toasts), show, remove, success, error, warning, info }
}
