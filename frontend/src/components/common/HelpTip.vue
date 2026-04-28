<script setup>
const props = defineProps({
  text: {
    type: String,
    required: true,
  },
});
</script>

<template>
  <span class="help-tip" tabindex="0">
    <button type="button" class="help-tip-button" aria-label="查看说明">?</button>
    <span class="help-tip-bubble">{{ props.text }}</span>
  </span>
</template>
