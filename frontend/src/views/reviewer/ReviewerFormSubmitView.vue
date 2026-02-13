<script setup>
import { ref, watchEffect } from "vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";
import { useRoute } from "vue-router";

const taskId = ref("");
const score = ref("");
const grade = ref("A");
const allowDefense = ref("YES");
const comments = ref("");
const internalComments = ref("");
const route = useRoute();

watchEffect(() => {
  const queryTaskId = route.query.taskId;
  if (queryTaskId) {
    taskId.value = String(queryTaskId);
  }
});

async function saveDraft() {
  try {
    const payload = {
      score: score.value === "" ? null : Number(score.value),
      grade: grade.value || null,
      allow_defense: allowDefense.value || null,
      comments: comments.value || null,
      internal_comments: internalComments.value || null,
    };
    await requestJson(`/api/reviewer/tasks/${Number(taskId.value)}/form`, "PUT", payload);
    notifySuccess("评阅草稿已保存");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function submitForm() {
  try {
    await request(`/api/reviewer/tasks/${Number(taskId.value)}/submit`, { method: "POST" });
    notifySuccess("评阅已提交");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}
</script>

<template>
  <section class="panel-card">
    <h4>评阅表填写与提交</h4>
    <p class="muted">支持先保存草稿，再提交最终评阅。</p>

    <div class="form-grid three">
      <label>
        任务ID
        <input v-model="taskId" type="number" />
      </label>
      <label>
        分数（0-100）
        <input v-model="score" type="number" min="0" max="100" />
      </label>
      <label>
        等级
        <input v-model="grade" />
      </label>
      <label>
        是否同意答辩
        <select v-model="allowDefense">
          <option value="YES">YES</option>
          <option value="NO">NO</option>
          <option value="REVISE">REVISE</option>
        </select>
      </label>
      <label class="wide">
        给学生评语
        <textarea v-model="comments" rows="4" />
      </label>
      <label class="wide">
        内部评语
        <textarea v-model="internalComments" rows="4" />
      </label>
    </div>

    <div class="row-actions">
      <button @click="saveDraft">保存草稿</button>
      <button class="warn" @click="submitForm">提交评阅</button>
    </div>
  </section>
</template>
