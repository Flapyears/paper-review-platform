<script setup>
import { onMounted, ref } from "vue";
import { request } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const thesisId = ref("");
const fileRef = ref(null);
const current = ref(null);

function onFileChange(event) {
  fileRef.value = event.target.files?.[0] ?? null;
}

async function uploadFinal() {
  try {
    if (!fileRef.value) {
      throw new Error("请先选择文件");
    }
    const form = new FormData();
    form.append("file", fileRef.value);
    const data = await request(`/api/thesis/${Number(thesisId.value)}/upload-final`, {
      method: "POST",
      body: form,
    });
    notifySuccess(`终稿上传成功，版本ID: ${data?.data?.version_id || "-"}`);
    await loadCurrent();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function submitFinal() {
  try {
    const data = await request(`/api/thesis/${Number(thesisId.value)}/submit-final`, {
      method: "POST",
    });
    notifySuccess(`送审提交成功，当前状态: ${data?.data?.thesis_status || "SUBMITTED"}`);
    await loadCurrent();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function loadCurrent() {
  try {
    const data = await request("/api/thesis/my");
    current.value = data.thesis;
    if (current.value?.id) thesisId.value = String(current.value.id);
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

onMounted(loadCurrent);
</script>

<template>
  <section class="panel-card">
    <h4>终稿上传与送审提交</h4>
    <p class="muted">上传终稿后再提交送审，系统会锁定送审版本。</p>

    <div class="form-grid three">
      <label>
        论文ID
        <input v-model="thesisId" type="number" />
      </label>
      <label class="wide">
        终稿文件（pdf/docx）
        <input type="file" accept=".pdf,.docx" @change="onFileChange" />
      </label>
    </div>

    <div class="row-actions">
      <button class="accent" @click="uploadFinal">上传终稿</button>
      <button class="warn" @click="submitFinal">提交送审</button>
      <button @click="loadCurrent">刷新当前状态</button>
    </div>

    <div v-if="current" class="detail-grid">
      <div><span>论文ID</span><b>{{ current.id }}</b></div>
      <div><span>状态</span><b>{{ current.status }}</b></div>
      <div><span>当前版本ID</span><b>{{ current.current_version_id || "-" }}</b></div>
      <div><span>退回原因</span><b>{{ current.return_reason || "-" }}</b></div>
    </div>
  </section>
</template>
