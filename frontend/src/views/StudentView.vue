<script setup>
import { ref } from "vue";
import { request, requestJson } from "../services/api";

const emit = defineEmits(["log", "error"]);

const thesisId = ref("");
const title = ref("");
const advisorId = ref("");
const uploadFile = ref(null);

function emitLog(data) {
  emit("log", data);
}

function emitError(err) {
  emit("error", err.message || String(err));
}

async function loadMyThesis() {
  try {
    const data = await request("/api/thesis/my");
    if (data?.thesis) {
      thesisId.value = data.thesis.id;
      title.value = data.thesis.title || "";
      advisorId.value = data.thesis.advisor_id ?? "";
    }
    emitLog(data);
  } catch (err) {
    emitError(err);
  }
}

async function createThesis() {
  try {
    const payload = { title: title.value.trim() };
    if (advisorId.value !== "") {
      payload.advisor_id = Number(advisorId.value);
    }
    const data = await requestJson("/api/thesis/my", "POST", payload);
    if (data?.data?.thesis_id) {
      thesisId.value = data.data.thesis_id;
    }
    emitLog(data);
  } catch (err) {
    emitError(err);
  }
}

async function updateTitle() {
  try {
    const data = await requestJson(`/api/thesis/${thesisId.value}`, "PUT", {
      title: title.value.trim(),
    });
    emitLog(data);
  } catch (err) {
    emitError(err);
  }
}

function onFileChange(event) {
  uploadFile.value = event.target.files?.[0] ?? null;
}

async function uploadFinal() {
  try {
    if (!uploadFile.value) {
      throw new Error("请先选择文件");
    }
    const form = new FormData();
    form.append("file", uploadFile.value);
    const data = await request(`/api/thesis/${thesisId.value}/upload-final`, {
      method: "POST",
      body: form,
    });
    emitLog(data);
  } catch (err) {
    emitError(err);
  }
}

async function submitFinal() {
  try {
    const data = await request(`/api/thesis/${thesisId.value}/submit-final`, {
      method: "POST",
    });
    emitLog(data);
  } catch (err) {
    emitError(err);
  }
}
</script>

<template>
  <section class="panel-card">
    <h3>学生端</h3>
    <p class="muted">创建论文、上传终稿、提交送审。</p>

    <div class="form-grid three">
      <label>
        论文ID
        <input v-model="thesisId" type="number" placeholder="自动填充" />
      </label>
      <label class="wide">
        标题
        <input v-model="title" placeholder="请输入论文标题" />
      </label>
      <label>
        导师ID（可选）
        <input v-model="advisorId" type="number" />
      </label>
    </div>

    <div class="row-actions">
      <button class="accent" @click="loadMyThesis">获取我的论文</button>
      <button @click="createThesis">创建论文</button>
      <button @click="updateTitle">更新标题</button>
      <button class="warn" @click="submitFinal">提交送审</button>
    </div>

    <div class="form-grid">
      <label class="wide">
        终稿文件（pdf/docx）
        <input type="file" accept=".pdf,.docx" @change="onFileChange" />
      </label>
      <button @click="uploadFinal">上传终稿</button>
    </div>
  </section>
</template>
