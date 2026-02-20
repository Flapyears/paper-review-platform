<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const route = useRoute();
const router = useRouter();

const taskId = ref("");
const score = ref("");
const grade = ref("A");
const allowDefense = ref("YES");
const comments = ref("");
const internalComments = ref("");
const quickTasks = ref([]);
const detail = ref(null);
const loadingDetail = ref(false);
const loadingQuickTasks = ref(false);

const gradeOptions = ["A", "B", "C", "D"];

const canOperate = computed(() => Number(taskId.value) > 0 && !loadingDetail.value);
const currentTaskIdNum = computed(() => Number(taskId.value) || 0);

function resetFormToDefault() {
  score.value = "";
  grade.value = "A";
  allowDefense.value = "YES";
  comments.value = "";
  internalComments.value = "";
}

function fillFormFromResponse(form) {
  if (!form) {
    resetFormToDefault();
    return;
  }
  score.value = form.score == null ? "" : String(form.score);
  grade.value = form.grade || "A";
  allowDefense.value = form.allow_defense || "YES";
  comments.value = form.comments || "";
  internalComments.value = form.internal_comments || "";
}

async function loadQuickTasks(showToast = false) {
  loadingQuickTasks.value = true;
  try {
    const resp = await request("/api/reviewer/tasks");
    quickTasks.value = resp.items || [];
    if (showToast) {
      notifySuccess("任务快捷列表已刷新");
    }
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loadingQuickTasks.value = false;
  }
}

async function loadTaskDetailById(id, showToast = true) {
  if (!id || id <= 0) {
    notifyError("请先从任务列表进入");
    return;
  }
  loadingDetail.value = true;
  try {
    const resp = await request(`/api/reviewer/tasks/${id}`);
    detail.value = resp;
    fillFormFromResponse(resp.form);
    if (showToast) {
      notifySuccess("任务详情已加载");
    }
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loadingDetail.value = false;
  }
}

function switchTask(id) {
  if (!id) return;
  router.push({ path: "/reviewer/form", query: { taskId: String(id) } });
}

async function saveDraft() {
  if (!canOperate.value) {
    notifyError("请先从“我的任务列表”进入并选择任务");
    return;
  }
  try {
    const payload = {
      score: score.value === "" ? null : Number(score.value),
      grade: grade.value || null,
      allow_defense: allowDefense.value || null,
      comments: comments.value || null,
      internal_comments: internalComments.value || null,
    };
    await requestJson(`/api/reviewer/tasks/${currentTaskIdNum.value}/form`, "PUT", payload);
    notifySuccess("评阅草稿已保存");
    await loadTaskDetailById(currentTaskIdNum.value, false);
    await loadQuickTasks(false);
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function submitForm() {
  if (!canOperate.value) {
    notifyError("请先从“我的任务列表”进入并选择任务");
    return;
  }
  try {
    await request(`/api/reviewer/tasks/${currentTaskIdNum.value}/submit`, { method: "POST" });
    notifySuccess("评阅已提交");
    await loadTaskDetailById(currentTaskIdNum.value, false);
    await loadQuickTasks(false);
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

watch(
  () => route.query.taskId,
  async (queryTaskId) => {
    if (!queryTaskId) {
      taskId.value = "";
      detail.value = null;
      resetFormToDefault();
      await loadQuickTasks(false);
      return;
    }
    taskId.value = String(queryTaskId);
    await loadTaskDetailById(Number(taskId.value), false);
    await loadQuickTasks(false);
  },
  { immediate: true }
);
</script>

<template>
  <section class="review-form-layout">
    <div class="panel-card">
      <h4>评阅表填写与提交</h4>
      <p class="muted">从“我的任务列表”点击“填写评阅”进入后会自动加载任务；无任务时不可提交。</p>

      <div class="form-grid three">
        <label>
          任务ID
          <input v-model="taskId" type="number" readonly />
        </label>
        <label>
          分数（0-100）
          <input v-model="score" type="number" min="0" max="100" :disabled="!canOperate" />
        </label>
        <label>
          等级
          <select v-model="grade" :disabled="!canOperate">
            <option v-for="item in gradeOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          是否同意答辩
          <select v-model="allowDefense" :disabled="!canOperate">
            <option value="YES">YES</option>
            <option value="NO">NO</option>
            <option value="REVISE">REVISE</option>
          </select>
        </label>
        <label class="wide">
          给学生评语
          <textarea v-model="comments" rows="4" :disabled="!canOperate" />
        </label>
        <label class="wide">
          内部评语
          <textarea v-model="internalComments" rows="4" :disabled="!canOperate" />
        </label>
      </div>

      <div class="row-actions">
        <button :disabled="!canOperate" @click="saveDraft">保存草稿</button>
        <button class="warn" :disabled="!canOperate" @click="submitForm">提交评阅</button>
      </div>

      <div v-if="!taskId" class="empty-box">请从“我的任务列表”点击“填写评阅”进入本页。</div>
      <div v-if="detail?.task" class="detail-grid">
        <div><span>任务状态</span><b>{{ detail.task.status }}</b></div>
        <div><span>论文</span><b>{{ detail.task.thesis_title || "-" }} (#{{ detail.task.thesis_id }})</b></div>
        <div><span>当前版本</span><b>{{ detail.task.version_no ? `V${detail.task.version_no}` : "-" }}</b></div>
        <div><span>退回原因</span><b>{{ detail.task.return_reason || "-" }}</b></div>
      </div>
    </div>

    <aside class="panel-card quick-task-panel">
      <h4>我的任务快捷列表</h4>
      <p class="muted">点击任务可快速切换。</p>
      <div class="row-actions" style="margin-top: 0">
        <button class="ghost" :disabled="loadingQuickTasks" @click="loadQuickTasks(true)">
          {{ loadingQuickTasks ? "刷新中..." : "刷新任务" }}
        </button>
      </div>
      <div v-if="quickTasks.length" class="quick-task-list">
        <button
          v-for="item in quickTasks"
          :key="item.task_id"
          class="quick-task-btn"
          :class="{ active: currentTaskIdNum === item.task_id }"
          @click="switchTask(item.task_id)"
        >
          <span>#{{ item.task_id }} · {{ item.status }}</span>
          <b>{{ item.thesis_title || "未命名论文" }}</b>
        </button>
      </div>
      <div v-else class="empty-box">暂无任务数据。</div>
    </aside>
  </section>
</template>

<style scoped>
.review-form-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 12px;
  align-items: start;
}

.quick-task-panel {
  position: sticky;
  top: 10px;
}

.quick-task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-task-btn {
  width: 100%;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 3px;
  border: 1px solid var(--line);
  background: #f7f9fc;
  color: var(--ink);
}

.quick-task-btn.active {
  border-color: #1e3a8a;
  background: #e9efff;
}

.quick-task-btn span {
  font-size: 12px;
  color: var(--muted);
}

.quick-task-btn b {
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 980px) {
  .review-form-layout {
    grid-template-columns: 1fr;
  }

  .quick-task-panel {
    position: static;
  }
}
</style>
