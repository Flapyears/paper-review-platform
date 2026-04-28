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
    <div class="pagination-info">
      <span class="total-count">共 <b>{{ total }}</b> 条</span>
      <span class="page-meta">第 {{ current }} / {{ totalPages }} 页</span>
    </div>
    
    <div class="pagination-controls">
      <div class="page-size-selector">
        <span class="selector-label">每页显示</span>
        <select :value="pageSize" @change="onPageSizeChange" class="size-select">
          <option v-for="size in pageSizeOptions" :key="size" :value="size">
            {{ size }}
          </option>
        </select>
      </div>
      
      <div class="page-buttons">
        <button class="nav-btn" :disabled="current <= 1" @click="prevPage" title="上一页">
          <span class="arrow">←</span> 上一页
        </button>
        <button class="nav-btn" :disabled="current >= totalPages" @click="nextPage" title="下一页">
          下一页 <span class="arrow">→</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
  padding: 8px 0;
  font-size: 14px;
  color: var(--muted);
}

.pagination-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.total-count b {
  color: var(--ink);
  font-weight: 600;
}

.page-meta {
  padding-left: 16px;
  border-left: 1px solid var(--line);
  color: var(--muted);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 24px;
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector-label {
  font-size: 13px;
  white-space: nowrap;
}

.size-select {
  height: 32px;
  padding: 0 8px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  transition: border-color 0.2s;
}

.size-select:focus {
  border-color: var(--accent);
  outline: none;
}

.page-buttons {
  display: flex;
  gap: 8px;
}

.nav-btn {
  height: 36px;
  padding: 0 16px;
  border-radius: 10px;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
  font-size: 13px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.nav-btn:hover:not(:disabled) {
  background: #dbeafe;
  transform: translateY(-1px);
}

.nav-btn:active:not(:disabled) {
  transform: translateY(0);
}

.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: #f1f5f9;
  color: #94a3b8;
}

.arrow {
  font-family: system-ui;
  font-weight: 400;
}
</style>
