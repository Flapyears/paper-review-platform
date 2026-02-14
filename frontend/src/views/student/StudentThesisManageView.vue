<script setup>
import { onMounted, ref } from "vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const title = ref("");
const advisorId = ref("");
const thesisId = ref("");
const advisors = ref([]);
const loadingAdvisors = ref(false);

async function loadMyThesis() {
  try {
    const resp = await request("/api/thesis/my");
    const thesis = resp.thesis;
    if (!thesis) {
      thesisId.value = "";
      return;
    }
    thesisId.value = String(thesis.id || "");
    title.value = thesis.title || "";
    advisorId.value = thesis.advisor_id != null ? String(thesis.advisor_id) : "";
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function loadAdvisors() {
  loadingAdvisors.value = true;
  try {
    const resp = await request("/api/thesis/advisors");
    advisors.value = resp.items || [];
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loadingAdvisors.value = false;
  }
}

async function createThesis() {
  try {
    if (!advisorId.value) {
      throw new Error("请选择导师后再创建论文");
    }
    const payload = { title: title.value.trim() };
    payload.advisor_id = Number(advisorId.value);
    const data = await requestJson("/api/thesis/my", "POST", payload);
    thesisId.value = String(data?.data?.thesis_id || "");
    await loadMyThesis();
    notifySuccess(`论文创建成功，ID: ${thesisId.value}`);
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function updateTitle() {
  try {
    if (!advisorId.value) {
      throw new Error("请选择导师后再保存");
    }
    await requestJson(`/api/thesis/${Number(thesisId.value)}`, "PUT", {
      title: title.value.trim(),
      advisor_id: Number(advisorId.value),
    });
    notifySuccess("论文信息已更新");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

onMounted(async () => {
  await Promise.all([loadAdvisors(), loadMyThesis()]);
});
</script>

<template>
  <section class="panel-card">
    <h4>论文信息维护</h4>
    <p class="muted">用于创建论文与维护标题信息。</p>

    <div class="form-grid three">
      <label>
        论文ID
        <input :value="thesisId || '尚未创建'" readonly />
      </label>
      <label class="wide">
        论文标题
        <input v-model="title" placeholder="请输入论文标题" />
      </label>
      <label>
        导师
        <select v-model="advisorId" :disabled="loadingAdvisors">
          <option value="">请选择导师</option>
          <option v-for="advisor in advisors" :key="advisor.id" :value="String(advisor.id)">
            {{ advisor.name }} (#{{ advisor.id }}){{ advisor.department ? ` - ${advisor.department}` : "" }}
          </option>
        </select>
      </label>
    </div>

    <div class="row-actions">
      <button v-if="!thesisId" class="accent" :disabled="!advisorId" @click="createThesis">创建论文</button>
      <button v-else :disabled="!advisorId" @click="updateTitle">保存论文信息</button>
      <button @click="loadMyThesis">刷新我的论文</button>
      <button :disabled="loadingAdvisors" @click="loadAdvisors">
        {{ loadingAdvisors ? "加载中..." : "刷新导师列表" }}
      </button>
    </div>
  </section>
</template>
