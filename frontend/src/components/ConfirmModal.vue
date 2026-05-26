<script setup>
defineProps({
  show: Boolean,
  title: { type: String, default: '确认' },
  message: { type: String, default: '' },
})
const emit = defineEmits(['confirm', 'cancel'])
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-[999] bg-black/30 flex items-center justify-center" @click.self="emit('cancel')">
      <div class="bg-bg-primary rounded-lg p-6 min-w-[300px] shadow-lg">
        <h3 class="text-base mb-2">{{ title }}</h3>
        <p v-if="message" class="text-[13px] text-text-secondary mb-4">{{ message }}</p>
        <div class="flex gap-2 justify-end">
          <button class="py-1.5 px-4 rounded-sm text-[13px] cursor-pointer border border-border-base bg-bg-primary" @click="emit('cancel')">取消</button>
          <button class="py-1.5 px-4 rounded-sm text-[13px] cursor-pointer text-white bg-accent border-accent hover:bg-accent-hover" @click="emit('confirm')">确认</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
