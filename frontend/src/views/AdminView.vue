<script setup>
import { ref } from "vue";
import { request, requestJson } from "../services/api";

const emit = defineEmits(["log", "error"]);

const thesisId = ref("");
const reviewerIds = ref("3,4");
const assignReason = ref("");
const taskId = ref("");
const newReviewerId = ref("");
const reason = ref("");

function emitLog(data) {
  emit("log", data);
}

function emitError(err) {
  emit("error", err.message || String(err));
}

async function listSubmitted() {
  try {
    emitLog(await request("/api/admin/thesis?status=SUBMITTED"));
  } catch (err) {
    emitError(err);
  }
}

async function listAll() {
  try {
    emitLog(await request("/api/admin/thesis"));
  } catch (err) {
    emitError(err);
  }
}

async function listProgress() {
  try {
    emitLog(await request("/api/admin/review-progress"));
  } catch (err) {
    emitError(err);
  }
}

async function assignTasks() {
  try {
    const ids = reviewerIds.value
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean)
      .map((x) => Number(x));
    const payload = {
      items: [
        {
          thesis_id: Number(thesisId.value),
          reviewer_ids: ids,
          reason: assignReason.value || null,
        },
      ],
    };
    emitLog(await requestJson("/api/admin/review-tasks/assign", "POST", payload));
  } catch (err) {
    emitError(err);
  }
}

async function returnThesis() {
  try {
    emitLog(
      await requestJson(`/api/admin/thesis/${Number(thesisId.value)}/return`, "POST", {
        reason: reason.value || "请补充后重新提交",
      })
    );
  } catch (err) {
    emitError(err);
  }
}

async function replaceTask() {
  try {
    emitLog(
      await requestJson(`/api/admin/review-tasks/${Number(taskId.value)}/replace`, "POST", {
        new_reviewer_id: Number(newReviewerId.value),
        reason: reason.value || null,
      })
    );
  } catch (err) {
    emitError(err);
  }
}

async function cancelTask() {
  try {
    emitLog(
      await requestJson(`/api/admin/review-tasks/${Number(taskId.value)}/cancel`, "POST", {
        reason: reason.value || null,
      })
    );
  } catch (err) {
    emitError(err);
  }
}

async function returnTask() {
  try {
    emitLog(
      await requestJson(`/api/admin/review-tasks/${Number(taskId.value)}/return`, "POST", {
        reason: reason.value || "请重评",
      })
    );
  } catch (err) {
    emitError(err);
  }
}
</script>

<template>
  <section class="panel-card">
    <h3>管理员端</h3>
    <p class="muted">待分配列表、任务分配与调整、进度跟踪。</p>

    <div class="row-actions">
      <button class="accent" @click="listSubmitted">SUBMITTED 列表</button>
      <button @click="listAll">全部论文</button>
      <button class="warn" @click="listProgress">评阅进度</button>
    </div>

    <div class="form-grid three">
      <label>
        论文ID
        <input v-model="thesisId" type="number" />
      </label>
      <label class="wide">
        评阅教师ID列表
        <input v-model="reviewerIds" placeholder="3,4" />
      </label>
      <label>
        分配原因
        <input v-model="assignReason" />
      </label>
    </div>

    <div class="row-actions">
      <button @click="assignTasks">分配评阅任务</button>
      <button @click="returnThesis">退回论文补交</button>
    </div>

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
        原因（替换/取消/退回）
        <input v-model="reason" />
      </label>
    </div>

    <div class="row-actions">
      <button @click="replaceTask">替换任务评阅教师</button>
      <button @click="cancelTask">取消任务</button>
      <button class="warn" @click="returnTask">退回重评</button>
    </div>
  </section>
</template>
