<script setup>
import { onMounted, ref } from "vue";
import { request } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const loading = ref(false);
const thesis = ref(null);
const progressMap = {
  DRAFT: 25,
  SUBMITTED: 50,
  REVIEWING: 75,
  REVIEW_DONE: 100,
};

function statusLabel(status) {
  if (status === "DRAFT") return "草稿中";
  if (status === "SUBMITTED") return "已提交待分配";
  if (status === "REVIEWING") return "评阅中";
  if (status === "REVIEW_DONE") return "评阅完成";
  return status || "-";
}

async function fetchMyThesis() {
  loading.value = true;
  try {
    const data = await request("/api/thesis/my");
    thesis.value = data.thesis;
    notifySuccess("已刷新我的论文信息");
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}

onMounted(fetchMyThesis);
</script>

<template>
  <section class="panel-card">
    <h4>我的论文总览</h4>
    <p class="muted">展示当前账号关联论文的核心状态与版本信息。</p>

    <div class="row-actions">
      <button class="accent" :disabled="loading" @click="fetchMyThesis">
        {{ loading ? "刷新中..." : "刷新" }}
      </button>
    </div>

    <div v-if="thesis" class="progress-box">
      <div class="progress-meta">
        <span>流程进度</span>
        <b>{{ progressMap[thesis.status] || 0 }}%</b>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${progressMap[thesis.status] || 0}%` }"></div>
      </div>
      <p class="muted">当前阶段：{{ statusLabel(thesis.status) }}</p>
    </div>

    <div v-if="thesis" class="detail-grid">
      <div><span>论文ID</span><b>{{ thesis.id }}</b></div>
      <div><span>标题</span><b>{{ thesis.title }}</b></div>
      <div><span>状态</span><b>{{ statusLabel(thesis.status) }}</b></div>
      <div><span>当前版本号</span><b>{{ thesis.current_version_no ? `V${thesis.current_version_no}` : "-" }}</b></div>
      <div><span>导师ID</span><b>{{ thesis.advisor_id || "-" }}</b></div>
      <div><span>退回原因</span><b>{{ thesis.return_reason || "-" }}</b></div>
    </div>

    <div v-else class="empty-box">
      当前账号暂无论文，请在“论文信息”页面创建。
    </div>
  </section>
</template>
