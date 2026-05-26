<script setup>
const model = defineModel({ type: String, default: '' })
defineProps({
  placeholder: { type: String, default: '搜索...' },
})
</script>

<template>
  <input
    v-model="model"
    v-bind="$attrs"
    type="text"
    class="py-1.5 px-3 border border-border-base rounded-md text-[13px] outline-none bg-bg-primary text-text-primary transition-colors duration-150 focus:border-accent"
    :placeholder="placeholder"
  />
</template>
