<script setup>
import { ref, watch } from 'vue'
import { X, Check } from 'lucide-vue-next'

const props = defineProps({
  visible: Boolean,
  categories: { type: Array, default: () => [] },
  currentCategoryId: { type: Number, default: null },
})

const emit = defineEmits(['select', 'close'])

const selected = ref(null)

watch(() => props.visible, (v) => {
  if (v) selected.value = props.currentCategoryId
})

const colorMap = {
  blue: '#3b82f6', green: '#22c55e', red: '#ef4444',
  purple: '#a855f7', yellow: '#eab308', teal: '#0d9488',
  orange: '#f97316', pink: '#ec4899',
}

function selectAndClose(id) {
  emit('select', id)
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <transition name="scale">
      <div
        v-if="visible"
        class="fixed inset-0 z-[999] flex items-center justify-center p-5"
        style="background: rgba(0,0,0,0.35); backdrop-filter: blur(4px);"
        @click.self="emit('close')"
      >
        <div
          class="w-full max-w-[300px] rounded-2xl shadow-lg overflow-hidden"
          style="background: var(--bg-primary); animation: slideUp 0.3s cubic-bezier(0.16,1,0.3,1);"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-5 py-4" style="border-bottom: 1px solid var(--border-light);">
            <h3 class="text-[15px] font-semibold" style="color: var(--text-primary);">更改分类</h3>
            <button
              class="flex items-center justify-center w-7 h-7 rounded-lg border-none cursor-pointer transition-colors hover:bg-[var(--bg-hover)]"
              style="background: transparent; color: var(--text-muted);"
              @click="emit('close')"
            ><X :size="16" /></button>
          </div>

          <!-- List -->
          <div class="py-1 max-h-[240px] overflow-y-auto">
            <!-- 未分类选项 -->
            <div
              class="flex items-center gap-3 px-5 py-2.5 cursor-pointer transition-colors hover:bg-[var(--bg-hover)]"
              :style="{ background: selected === null ? 'var(--bg-active)' : 'transparent' }"
              @click="selectAndClose(null)"
            >
              <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background: #9ca3af;"></span>
              <span class="text-[13px] flex-1" style="color: var(--text-secondary);">未分类</span>
              <Check v-if="selected === null" :size="14" style="color: var(--accent);" />
            </div>

            <!-- 分类列表 -->
            <div
              v-for="cat in categories"
              :key="cat.id"
              class="flex items-center gap-3 px-5 py-2.5 cursor-pointer transition-colors hover:bg-[var(--bg-hover)]"
              :style="{ background: selected === cat.id ? 'var(--bg-active)' : 'transparent' }"
              @click="selectAndClose(cat.id)"
            >
              <span
                class="w-2.5 h-2.5 rounded-full shrink-0"
                :style="{ background: colorMap[cat.color] || '#9ca3af' }"
              ></span>
              <span class="text-[13px] flex-1" style="color: var(--text-secondary);">{{ cat.name }}</span>
              <Check v-if="selected === cat.id" :size="14" style="color: var(--accent);" />
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
</style>
