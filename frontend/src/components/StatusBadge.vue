<script setup>
defineProps({
  type: { type: String, required: true },
})
</script>

<template>
  <span
    class="badge"
    :style="{
      background:
        type === 'success'                ? 'var(--success-bg)' :
        type === 'failed' || type === 'failed_retryable' || type === 'error' ? 'var(--error-bg)' :
        type === 'pending' || type === 'warning' ? 'var(--warning-bg)' :
        type === 'deep_fetch'             ? '#f5f0ff' :
        type === 'image_download'         ? '#e8f4fd' :
        type === 'info' || type === 'poll' ? 'var(--accent-light)' :
                                              'var(--bg-hover)',
      color:
        type === 'success'                ? 'var(--success)' :
        type === 'failed' || type === 'failed_retryable' || type === 'error' ? 'var(--error)' :
        type === 'pending' || type === 'warning' ? 'var(--warning)' :
        type === 'deep_fetch'             ? '#7c3aed' :
        type === 'image_download'         ? '#1890ff' :
        type === 'info' || type === 'poll' ? 'var(--accent)' :
                                              'var(--text-muted)',
    }"
  >
    <slot />
  </span>
</template>
