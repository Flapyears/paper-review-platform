<script setup>
import { computed } from "vue";

const props = defineProps({
  total: { type: Number, required: true },
  current: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  pageSizeOptions: { type: Array, default: () => [10, 20, 50] },
});

const emit = defineEmits(["update:current", "update:pageSize"]);

const totalPages = computed(() => Math.max(1, Math.ceil((props.total || 0) / (props.pageSize || 1))));

function prevPage() {
  emit("update:current", Math.max(1, props.current - 1));
}

function nextPage() {
  emit("update:current", Math.min(totalPages.value, props.current + 1));
}

function onPageSizeChange(event) {
  emit("update:pageSize", Number(event.target.value) || 10);
  emit("update:current", 1);
}
</script>

<template>
  <div v-if="total > 0" class="pagination-bar">
    <span>共 {{ total }} 条</span>
    <span>第 {{ current }} / {{ totalPages }} 页</span>
    <label>
      每页
      <select :value="pageSize" @change="onPageSizeChange">
        <option v-for="size in pageSizeOptions" :key="size" :value="size">
          {{ size }}
        </option>
      </select>
    </label>
    <button class="ghost" :disabled="current <= 1" @click="prevPage">上一页</button>
    <button class="ghost" :disabled="current >= totalPages" @click="nextPage">下一页</button>
  </div>
</template>
