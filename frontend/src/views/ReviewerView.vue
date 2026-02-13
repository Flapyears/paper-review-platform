<script setup>
import { ref } from "vue";
import { request, requestJson } from "../services/api";
import { authHeaders } from "../stores/auth";

const emit = defineEmits(["log", "error"]);

const taskId = ref("");
const score = ref("");
const grade = ref("A");
const allowDefense = ref("YES");
const comments = ref("");
const internalComments = ref("");

function emitLog(data) {
  emit("log", data);
}

function emitError(err) {
  emit("error", err.message || String(err));
}

async function listMyTasks() {
  try {
    emitLog(await request("/api/reviewer/tasks"));
  } catch (err) {
    emitError(err);
  }
}

async function taskDetail() {
  try {
    emitLog(await request(`/api/reviewer/tasks/${Number(taskId.value)}`));
  } catch (err) {
    emitError(err);
  }
}

async function saveDraft() {
  try {
    const payload = {
      score: score.value === "" ? null : Number(score.value),
      grade: grade.value || null,
      allow_defense: allowDefense.value || null,
      comments: comments.value || null,
      internal_comments: internalComments.value || null,
    };
    emitLog(await requestJson(`/api/reviewer/tasks/${Number(taskId.value)}/form`, "PUT", payload));
  } catch (err) {
    emitError(err);
  }
}

async function submitReview() {
  try {
    emitLog(await request(`/api/reviewer/tasks/${Number(taskId.value)}/submit`, { method: "POST" }));
  } catch (err) {
    emitError(err);
  }
}

async function downloadBoundFile() {
  try {
    const response = await fetch(`/api/reviewer/tasks/${Number(taskId.value)}/download`, {
      method: "GET",
      headers: authHeaders(),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${text}`);
    }
    const blob = await response.blob();
    const cd = response.headers.get("content-disposition") || "";
    const m = cd.match(/filename=\"?([^\"]+)\"?/i);
    const fileName = m ? m[1] : `task-${taskId.value}.bin`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    emitLog({ message: "downloaded", taskId: Number(taskId.value), fileName });
  } catch (err) {
    emitError(err);
  }
}
</script>

<template>
  <section class="panel-card">
    <h3>评阅教师端</h3>
    <p class="muted">任务查询、绑定文件下载、评阅草稿与提交。</p>

    <div class="form-grid three">
      <label>
        任务ID
        <input v-model="taskId" type="number" />
      </label>
      <button class="accent" @click="listMyTasks">我的任务列表</button>
      <button @click="taskDetail">查看任务详情</button>
    </div>

    <div class="row-actions">
      <button @click="downloadBoundFile">下载绑定论文</button>
      <button class="warn" @click="submitReview">提交评阅</button>
    </div>

    <div class="form-grid three">
      <label>
        分数
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
      <button @click="saveDraft">保存评阅草稿</button>
    </div>
  </section>
</template>
