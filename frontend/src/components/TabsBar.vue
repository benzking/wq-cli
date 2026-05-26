<script setup>
defineProps({
  tabs: { type: Array, required: true },
  modelValue: { type: String, required: true },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <div class="flex gap-0 border-b-2 border-border-light mb-5">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      class="py-2.5 px-5 border-none bg-none text-[13px] cursor-pointer border-b-2 border-transparent -mb-0.5 transition-colors duration-150"
      :class="modelValue === tab.key
        ? 'text-accent font-semibold border-b-accent'
        : 'text-text-muted hover:text-text-primary'"
      @click="emit('update:modelValue', tab.key)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
