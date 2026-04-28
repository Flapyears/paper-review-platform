<script setup>
import { computed, ref, watch } from "vue";
import BaseModal from "./BaseModal.vue";
import HelpTip from "./HelpTip.vue";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    required: true,
  },
  fields: {
    type: Array,
    default: () => [],
  },
  tip: {
    type: String,
    default: "",
  },
  uploading: {
    type: Boolean,
    default: false,
  },
  downloading: {
    type: Boolean,
    default: false,
  },
  result: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["update:modelValue", "download-template", "upload-file"]);
const selectedFile = ref(null);
const defaultPassword = ref("");

const canUpload = computed(() => Boolean(selectedFile.value) && !props.uploading);

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) {
      selectedFile.value = null;
      defaultPassword.value = "";
    }
  }
);

function close() {
  emit("update:modelValue", false);
}

function onFileChange(event) {
  selectedFile.value = event.target.files?.[0] ?? null;
}

function upload() {
  if (!selectedFile.value) return;
  emit("upload-file", {
    file: selectedFile.value,
    defaultPassword: defaultPassword.value.trim(),
  });
}
</script>

<template>
  <BaseModal :model-value="props.modelValue" :title="props.title" width="720px" @update:modelValue="close">
    <div class="modal-stack">
      <div class="title-inline">
        <strong>导入说明</strong>
        <HelpTip :text="props.tip" />
      </div>
      <div class="tag-list">
        <span v-for="field in props.fields" :key="field" class="soft-tag">{{ field }}</span>
      </div>

      <label>
        选择 Excel 文件
        <input type="file" accept=".xlsx" @change="onFileChange" />
      </label>

      <label>
        默认初始密码
        <input v-model="defaultPassword" type="password" placeholder="留空则使用系统默认值" />
      </label>

      <p v-if="selectedFile" class="muted-inline">已选择：{{ selectedFile.name }}</p>

      <div class="row-actions">
        <button class="ghost" :disabled="props.downloading" @click="$emit('download-template')">
          {{ props.downloading ? "下载中..." : "下载模板" }}
        </button>
        <button class="accent" :disabled="!canUpload" @click="upload">
          {{ props.uploading ? "导入中..." : "导入 Excel" }}
        </button>
      </div>

      <div v-if="props.result" class="import-result">
        <div class="detail-grid">
          <div><span>成功</span><b>{{ props.result.created_count }}</b></div>
          <div><span>失败</span><b>{{ props.result.failed_count }}</b></div>
          <div><span>默认初始密码</span><b>{{ props.result.default_password || "-" }}</b></div>
        </div>

        <div v-if="props.result.failures?.length" class="empty-box import-failures">
          <p>以下行导入失败：</p>
          <ul class="steps">
            <li v-for="item in props.result.failures" :key="`${item.row}-${item.reason}`">
              第 {{ item.row }} 行：{{ item.reason }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </BaseModal>
</template>
