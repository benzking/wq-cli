<script setup>
import { AlertTriangle, X } from 'lucide-vue-next'

defineProps({
  show: Boolean,
  title: { type: String, default: '确认' },
  message: { type: String, default: '' },
  danger: { type: Boolean, default: false },
  confirmText: { type: String, default: '确认' },
  cancelText: { type: String, default: '取消' },
})
const emit = defineEmits(['confirm', 'cancel'])
</script>

<template>
  <Teleport to="body">
    <transition name="scale">
      <div
        v-if="show"
        class="fixed inset-0 z-[999] flex items-center justify-center p-5"
        style="background: rgba(0,0,0,0.35); backdrop-filter: blur(4px);"
        @click.self="emit('cancel')"
      >
        <div class="w-full max-w-[340px] rounded-2xl p-6 shadow-lg"
          style="background: var(--bg-primary);"
        >
          <!-- Icon -->
          <div
            class="w-11 h-11 rounded-xl flex items-center justify-center mb-4"
            :style="danger
              ? 'background: var(--error-bg); color: var(--error);'
              : 'background: var(--warning-bg); color: var(--warning);'"
          >
            <AlertTriangle :size="20" />
          </div>

          <!-- Content -->
          <h3 class="text-[15px] font-semibold mb-1.5" style="color: var(--text-primary);">{{ title }}</h3>
          <p v-if="message" class="text-[13px] leading-relaxed mb-5" style="color: var(--text-secondary);">{{ message }}</p>

          <!-- Actions -->
          <div class="flex gap-2.5 justify-end">
            <button
              class="btn"
              @click="emit('cancel')"
            >{{ cancelText }}</button>
            <button
              :class="danger ? 'btn-danger' : 'btn-primary'"
              @click="emit('confirm')"
            >{{ confirmText }}</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>
