<script setup>
import { computed, ref, watch } from "vue";
import { request } from "../../services/api";
import { authHeaders } from "../../stores/auth";
import { notifyError, notifySuccess } from "../../stores/notice";
import { useRoute } from "vue-router";

const taskId = ref("");
const detail = ref(null);
const route = useRoute();
const loading = ref(false);

const canOperate = computed(() => Number(taskId.value) > 0);

async function loadTaskDetail(showToast = true) {
  if (!canOperate.value) {
    notifyError("请先从任务列表进入，或输入有效任务ID");
    return;
  }
  loading.value = true;
  try {
    const resp = await request(`/api/reviewer/tasks/${Number(taskId.value)}`);
    detail.value = resp;
    if (showToast) {
      notifySuccess("任务详情已加载");
    }
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}

async function downloadBoundFile() {
  if (!canOperate.value) {
    notifyError("请先加载任务详情");
    return;
  }
  try {
    const response = await fetch(`/api/reviewer/tasks/${Number(taskId.value)}/download`, {
      method: "GET",
      headers: authHeaders(),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const blob = await response.blob();
    const contentDisposition = response.headers.get("content-disposition") || "";
    const matched = contentDisposition.match(/filename=\"?([^\"]+)\"?/i);
    const fileName = matched ? matched[1] : `task-${taskId.value}.bin`;

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    notifySuccess(`下载成功：${fileName}`);
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

watch(
  () => route.query.taskId,
  async (queryTaskId) => {
    if (!queryTaskId) {
      return;
    }
    taskId.value = String(queryTaskId);
    await loadTaskDetail(false);
  },
  { immediate: true }
);
</script>

<template>
  <section class="panel-card">
    <h4>任务详情与下载</h4>
    <p class="muted">建议从“我的任务列表”点击“打开详情”进入，本页会自动加载任务信息。</p>

    <div class="form-grid three">
      <label>
        任务ID
        <input v-model="taskId" type="number" />
      </label>
    </div>

    <div class="row-actions">
      <button class="accent" :disabled="!canOperate || loading" @click="loadTaskDetail">
        {{ loading ? "加载中..." : "查看详情" }}
      </button>
      <button :disabled="!canOperate" @click="downloadBoundFile">下载论文</button>
    </div>

    <div v-if="detail?.task" class="detail-grid">
      <div><span>任务状态</span><b>{{ detail.task.status }}</b></div>
      <div><span>论文ID</span><b>{{ detail.task.thesis_id }}</b></div>
      <div><span>论文标题</span><b>{{ detail.task.thesis_title || '-' }}</b></div>
      <div><span>版本号</span><b>{{ detail.task.version_no ? `V${detail.task.version_no}` : "-" }}</b></div>
      <div><span>下载次数</span><b>{{ detail.task.download_count }}</b></div>
      <div><span>最后下载时间</span><b>{{ detail.task.last_downloaded_at || '-' }}</b></div>
      <div><span>退回原因</span><b>{{ detail.task.return_reason || '-' }}</b></div>
    </div>
  </section>
</template>
