<script setup>
import { ref } from "vue";
import { requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const taskId = ref("");
const newReviewerId = ref("");
const reason = ref("");

async function replaceTask() {
  try {
    await requestJson(`/api/admin/review-tasks/${Number(taskId.value)}/replace`, "POST", {
      new_reviewer_id: Number(newReviewerId.value),
      reason: reason.value || null,
    });
    notifySuccess("任务替换成功");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function cancelTask() {
  try {
    await requestJson(`/api/admin/review-tasks/${Number(taskId.value)}/cancel`, "POST", {
      reason: reason.value || null,
    });
    notifySuccess("任务已取消");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function returnTask() {
  try {
    await requestJson(`/api/admin/review-tasks/${Number(taskId.value)}/return`, "POST", {
      reason: reason.value || "请根据意见重评",
    });
    notifySuccess("任务已退回重评");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}
</script>

<template>
  <section class="panel-card">
    <h4>任务操作</h4>
    <p class="muted">对评阅任务执行替换、取消或退回重评。</p>

    <div class="form-grid three">
      <label>
        任务ID
        <input v-model="taskId" type="number" />
      </label>
      <label>
        新评阅教师ID
        <input v-model="newReviewerId" type="number" />
      </label>
      <label class="wide">
        原因
        <input v-model="reason" />
      </label>
    </div>

    <div class="row-actions">
      <button @click="replaceTask">替换评阅教师</button>
      <button @click="cancelTask">取消任务</button>
      <button class="warn" @click="returnTask">退回重评</button>
    </div>
  </section>
</template>
