<script setup>
import { computed, ref, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { request } from "../../services/api";
import { authHeaders } from "../../stores/auth";
import { notifyError, notifySuccess } from "../../stores/notice";
import { formatReviewTaskStatus } from "../../utils/status";

const taskId = ref("");
const detail = ref(null);
const route = useRoute();
const router = useRouter(); 
const loading = ref(false);
const allTasks = ref([]); 

const canOperate = computed(() => Number(taskId.value) > 0);

async function loadAllTasks() {
  try {
    const resp = await request("/api/reviewer/tasks");
    allTasks.value = resp.items || [];
    // Auto-select first task if none selected
    if (allTasks.value.length > 0 && !taskId.value) {
      router.replace(`/reviewer/tasks?taskId=${allTasks.value[0].task_id}`);
    }
  } catch (err) {
    notifyError("获取任务列表失败");
  }
}

async function loadTaskDetail(showToast = true) {
  if (!canOperate.value) return;
  
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

// Watch for dropdown changes to update URL
function onTaskChange() {
  if (taskId.value) {
    router.push(`/reviewer/tasks?taskId=${taskId.value}`);
  }
}

watch(
  () => route.query.taskId,
  async (queryTaskId) => {
    if (!queryTaskId) {
      if (allTasks.value.length === 0) {
        await loadAllTasks();
      }
      return;
    }
    taskId.value = String(queryTaskId);
    await loadTaskDetail(false);
  },
  { immediate: true }
);

onMounted(async () => {
  if (allTasks.value.length === 0) {
    await loadAllTasks();
  }
});
</script>

<template>
  <section class="panel-card">
    <h4>任务详情与下载</h4>
    <p class="muted">可以直接切换任务，也可以先看详情再下载论文。</p>

    <div class="form-grid three">
      <label>
        当前选择的任务
        <select v-model="taskId" @change="onTaskChange">
          <option value="" disabled>请选择一个任务</option>
          <option v-for="t in allTasks" :key="t.task_id" :value="String(t.task_id)">
            ID: {{ t.task_id }} | {{ t.thesis_title || '无标题' }}
          </option>
        </select>
      </label>
    </div>

    <div class="row-actions">
      <button class="accent" :disabled="!canOperate || loading" @click="loadTaskDetail">
        {{ loading ? "加载中..." : "刷新详情" }}
      </button>
      <button :disabled="!canOperate" @click="downloadBoundFile">下载论文</button>
    </div>

    <div v-if="detail?.task" class="detail-grid">
      <div><span>任务状态</span><b>{{ formatReviewTaskStatus(detail.task.status) }}</b></div>
      <div><span>论文ID</span><b>{{ detail.task.thesis_id }}</b></div>
      <div><span>论文标题</span><b>{{ detail.task.thesis_title || '-' }}</b></div>
      <div><span>版本号</span><b>{{ detail.task.version_no ? `V${detail.task.version_no}` : "-" }}</b></div>
      <div><span>下载次数</span><b>{{ detail.task.download_count }}</b></div>
      <div><span>最后下载时间</span><b>{{ detail.task.last_downloaded_at || '-' }}</b></div>
      <div><span>退回原因</span><b>{{ detail.task.return_reason || '-' }}</b></div>
    </div>
    <div v-else-if="!loading" class="empty-state">
      暂未加载任务详情，请选择任务。
    </div>
  </section>
</template>

