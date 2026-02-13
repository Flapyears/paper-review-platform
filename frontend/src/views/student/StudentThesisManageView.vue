<script setup>
import { ref } from "vue";
import { requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const title = ref("");
const advisorId = ref("");
const thesisId = ref("");

async function createThesis() {
  try {
    const payload = { title: title.value.trim() };
    if (advisorId.value !== "") payload.advisor_id = Number(advisorId.value);
    const data = await requestJson("/api/thesis/my", "POST", payload);
    thesisId.value = String(data?.data?.thesis_id || "");
    notifySuccess(`论文创建成功，ID: ${thesisId.value}`);
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function updateTitle() {
  try {
    await requestJson(`/api/thesis/${Number(thesisId.value)}`, "PUT", { title: title.value.trim() });
    notifySuccess("论文标题已更新");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}
</script>

<template>
  <section class="panel-card">
    <h4>论文信息维护</h4>
    <p class="muted">用于创建论文与维护标题信息。</p>

    <div class="form-grid three">
      <label>
        论文ID
        <input v-model="thesisId" type="number" placeholder="创建后自动回填" />
      </label>
      <label class="wide">
        论文标题
        <input v-model="title" placeholder="请输入论文标题" />
      </label>
      <label>
        导师ID（可选）
        <input v-model="advisorId" type="number" />
      </label>
    </div>

    <div class="row-actions">
      <button class="accent" @click="createThesis">创建论文</button>
      <button @click="updateTitle">更新标题</button>
    </div>
  </section>
</template>
