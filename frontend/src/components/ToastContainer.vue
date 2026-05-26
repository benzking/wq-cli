<script setup>
import { useToast } from '@/composables/useToast'
const { toasts, remove } = useToast()
</script>

<template>
  <div class="z-[1000] fixed bottom-5 right-5 flex flex-col-reverse gap-2">
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="py-2.5 px-5 rounded-md text-[13px] cursor-pointer shadow-md max-w-[400px]"
        :class="{
          'bg-success text-white': t.type === 'success',
          'bg-error text-white': t.type === 'error',
          'bg-warning text-white': t.type === 'warning',
          'bg-accent text-white': t.type === 'info',
        }"
        @click="remove(t.id)"
      >
        {{ t.message }}
      </div>
    </TransitionGroup>
  </div>
</template>

<style>
.toast-enter-active { transition: all 0.3s ease; }
.toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from { opacity: 0; transform: translateY(20px); }
.toast-leave-to { opacity: 0; transform: translateX(40px); }
</style>
