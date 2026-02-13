<script setup>
defineProps({
  value: {
    type: String,
    required: true,
  },
  error: {
    type: Boolean,
    default: false,
  },
});
</script>

<template>
  <section class="panel-card">
    <h3>响应日志</h3>
    <pre class="log" :class="{ error }">{{ value }}</pre>
  </section>
</template>
