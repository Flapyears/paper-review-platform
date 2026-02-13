<script setup>
import { computed } from "vue";

const props = defineProps({
  message: {
    type: String,
    default: "",
  },
  type: {
    type: String,
    default: "success",
  },
});

const shown = computed(() => props.message && props.message.length > 0);
</script>

<template>
  <div v-if="shown" class="notice" :class="type">
    {{ message }}
  </div>
</template>
