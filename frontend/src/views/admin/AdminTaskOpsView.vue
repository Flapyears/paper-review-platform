<script setup>
import { computed, onMounted, ref } from "vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";
import PaginationBar from "../../components/common/PaginationBar.vue";
import { formatReviewTaskStatus } from "../../utils/status";

const loading = ref(false);
const tasks = ref([]);
const selectedTaskId = ref("");
const reason = ref("");
const statusFilter = ref("ALL");
const thesisFilter = ref("");
const reviewerFilter = ref("");

const candidates = ref([]);
const loadingCandidates = ref(false);
const newReviewerId = ref("");
const page = ref(1);
const pageSize = ref(10);

const pagedTasks = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return tasks.value.slice(start, start + pageSize.value);
});

const selectedTask = computed(() => tasks.value.find((x) => x.task_id === Number(selectedTaskId.value)) || null);

const canReplace = computed(
  () => selectedTask.value && ["ASSIGNED", "DRAFTING", "RETURNED"].includes(selectedTask.value.status)
);
const canCancel = computed(
  () => selectedTask.value && !["SUBMITTED", "CANCELLED"].includes(selectedTask.value.status)
);
const canReturn = computed(() => selectedTask.value && selectedTask.value.status === "SUBMITTED");

function fmtDate(iso) {
  if (!iso) return "-";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  return dt.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function loadTasks() {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    if (statusFilter.value !== "ALL") params.set("status", statusFilter.value);
    if (thesisFilter.value) params.set("thesis_id", String(Number(thesisFilter.value)));
    if (reviewerFilter.value) params.set("reviewer_id", String(Number(reviewerFilter.value)));
    const path = params.size ? `/api/admin/review-tasks?${params.toString()}` : "/api/admin/review-tasks";
    const resp = await request(path);
    tasks.value = resp.items || [];
    page.value = 1;
    if (selectedTaskId.value) {
      const exists = tasks.value.some((x) => x.task_id === Number(selectedTaskId.value));
      if (!exists) {
        selectedTaskId.value = "";
        candidates.value = [];
        newReviewerId.value = "";
      }
    }
    notifySuccess("任务列表已刷新");
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}

async function loadCandidates() {
  if (!selectedTask.value) {
    candidates.value = [];
    newReviewerId.value = "";
    return;
  }
  loadingCandidates.value = true;
  try {
    const resp = await request(`/api/admin/reviewers?thesis_id=${selectedTask.value.thesis_id}`);
    candidates.value = (resp.items || []).filter((x) => x.id !== selectedTask.value.reviewer_id);
    const valid = candidates.value.some((x) => x.id === Number(newReviewerId.value));
    if (!valid) newReviewerId.value = "";
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loadingCandidates.value = false;
  }
}

async function selectTask(task) {
  selectedTaskId.value = String(task.task_id);
  reason.value = "";
  await loadCandidates();
}

async function replaceTask() {
  try {
    if (!selectedTask.value) throw new Error("请先选择任务");
    if (!newReviewerId.value) throw new Error("请选择新评阅教师");
    await requestJson(`/api/admin/review-tasks/${selectedTask.value.task_id}/replace`, "POST", {
      new_reviewer_id: Number(newReviewerId.value),
      reason: reason.value || null,
    });
    notifySuccess("任务替换成功");
    await loadTasks();
    await loadCandidates();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function cancelTask() {
  try {
    if (!selectedTask.value) throw new Error("请先选择任务");
    await requestJson(`/api/admin/review-tasks/${selectedTask.value.task_id}/cancel`, "POST", {
      reason: reason.value || null,
    });
    notifySuccess("任务已取消");
    await loadTasks();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function returnTask() {
  try {
    if (!selectedTask.value) throw new Error("请先选择任务");
    await requestJson(`/api/admin/review-tasks/${selectedTask.value.task_id}/return`, "POST", {
      reason: reason.value || "请根据意见重评",
    });
    notifySuccess("任务已退回重评");
    await loadTasks();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

onMounted(loadTasks);
</script>

<template>
  <section class="panel-card">
    <h4>任务操作</h4>
    <p class="muted">先在任务列表中选中目标任务，再执行替换、取消或退回重评。</p>

    <div class="form-grid">
      <label>
        状态筛选
        <select v-model="statusFilter">
          <option value="ALL">全部</option>
          <option value="ASSIGNED">待处理</option>
          <option value="DRAFTING">填写中</option>
          <option value="SUBMITTED">已提交</option>
          <option value="RETURNED">退回修改</option>
          <option value="CANCELLED">已取消</option>
        </select>
      </label>
      <label>
        论文ID
        <input v-model="thesisFilter" type="number" />
      </label>
      <label>
        教师ID
        <input v-model="reviewerFilter" type="number" />
      </label>
      <button class="accent" :disabled="loading" @click="loadTasks">
        {{ loading ? "加载中..." : "刷新任务列表" }}
      </button>
    </div>

    <table v-if="tasks.length" class="data-table">
      <thead>
        <tr>
          <th>任务ID</th>
          <th>论文</th>
          <th>当前评阅教师</th>
          <th>状态</th>
          <th>更新时间</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in pagedTasks" :key="row.task_id" :class="{ active: selectedTaskId === String(row.task_id) }">
          <td>#{{ row.task_id }}</td>
          <td>{{ row.thesis_title || "-" }} (#{{ row.thesis_id }})</td>
          <td>
            {{ row.reviewer_name || "-" }} (#{{ row.reviewer_id }})
            <div class="muted-inline">{{ row.reviewer_department }}</div>
          </td>
          <td>{{ formatReviewTaskStatus(row.status) }}</td>
          <td>{{ fmtDate(row.updated_at) }}</td>
          <td><button @click="selectTask(row)">选择</button></td>
        </tr>
      </tbody>
    </table>
    <PaginationBar v-model:current="page" v-model:pageSize="pageSize" :total="tasks.length" />
    <div v-if="!tasks.length" class="empty-box">暂无任务，请调整筛选条件后重试。</div>

    <div v-if="selectedTask" class="detail-grid">
      <div><span>当前任务</span><b>#{{ selectedTask.task_id }}</b></div>
      <div><span>当前状态</span><b>{{ formatReviewTaskStatus(selectedTask.status) }}</b></div>
      <div><span>论文</span><b>{{ selectedTask.thesis_title }} (#{{ selectedTask.thesis_id }})</b></div>
      <div><span>当前教师</span><b>{{ selectedTask.reviewer_name }} (#{{ selectedTask.reviewer_id }})</b></div>
      <div><span>分配说明</span><b>{{ selectedTask.assigned_reason || "-" }}</b></div>
      <div><span>退回原因</span><b>{{ selectedTask.return_reason || "-" }}</b></div>
    </div>

    <div v-if="selectedTask" class="form-grid three" style="margin-top: 12px">
      <label>
        新评阅教师
        <select v-model="newReviewerId" :disabled="loadingCandidates || !canReplace">
          <option value="">请选择</option>
          <option
            v-for="item in candidates"
            :key="item.id"
            :value="String(item.id)"
            :disabled="item.is_conflicted || item.department_will_exceed_quota"
          >
            {{ item.name }} (#{{ item.id }}) - {{ item.department }} - 活跃{{ item.active_task_count }}
          </option>
        </select>
      </label>
      <label class="wide">
        操作原因
        <input v-model="reason" placeholder="替换/取消/退回时可填写原因" />
      </label>
    </div>

    <div class="row-actions">
      <button :disabled="!canReplace || !newReviewerId" @click="replaceTask">替换评阅教师</button>
      <button :disabled="!canCancel" @click="cancelTask">取消任务</button>
      <button class="warn" :disabled="!canReturn" @click="returnTask">退回重评</button>
    </div>
  </section>
</template>
