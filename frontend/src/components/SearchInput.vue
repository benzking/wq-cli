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
    class="input"
    :placeholder="placeholder"
  />
</template>
