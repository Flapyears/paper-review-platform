<script setup>
import { onMounted, ref } from "vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const submittedTheses = ref([]);
const thesisId = ref("");
const reviewerIds = ref("3,4");
const assignReason = ref("");
const assignResult = ref(null);

async function loadSubmitted() {
  try {
    const resp = await request("/api/admin/thesis?status=SUBMITTED");
    submittedTheses.value = resp.items || [];
    notifySuccess("待分配论文已加载");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function assignTasks() {
  try {
    const ids = reviewerIds.value
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)
      .map((v) => Number(v));
    const payload = {
      items: [
        {
          thesis_id: Number(thesisId.value),
          reviewer_ids: ids,
          reason: assignReason.value || null,
        },
      ],
    };
    const resp = await requestJson("/api/admin/review-tasks/assign", "POST", payload);
    notifySuccess(`分配成功，任务ID: ${(resp.data?.task_ids || []).join(", ")}`);
    const listResp = await request("/api/admin/thesis");
    const matched = (listResp.items || []).find((x) => x.id === Number(thesisId.value));
    assignResult.value = {
      taskIds: resp.data?.task_ids || [],
      thesis: matched || null,
    };
    await loadSubmitted();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

onMounted(loadSubmitted);
</script>

<template>
  <section class="panel-card">
    <h4>评阅分配</h4>
    <p class="muted">从待分配论文中选择并分配评阅教师。</p>

    <div class="row-actions">
      <button class="accent" @click="loadSubmitted">加载待分配论文</button>
    </div>

    <table v-if="submittedTheses.length" class="data-table">
      <thead>
        <tr>
          <th>论文ID</th>
          <th>标题</th>
          <th>学生ID</th>
          <th>版本ID</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in submittedTheses" :key="row.id">
          <td>{{ row.id }}</td>
          <td>{{ row.title }}</td>
          <td>{{ row.student_id }}</td>
          <td>{{ row.current_version_id }}</td>
          <td><button @click="thesisId = String(row.id)">选择</button></td>
        </tr>
      </tbody>
    </table>

    <div class="form-grid three" style="margin-top: 12px">
      <label>
        论文ID
        <input v-model="thesisId" type="number" />
      </label>
      <label class="wide">
        评阅教师ID列表（逗号分隔）
        <input v-model="reviewerIds" />
      </label>
      <label>
        分配原因
        <input v-model="assignReason" />
      </label>
    </div>

    <div class="row-actions">
      <button class="accent" @click="assignTasks">确认分配</button>
    </div>

    <div v-if="assignResult" class="detail-grid">
      <div><span>新建任务ID</span><b>{{ assignResult.taskIds.join(", ") || "-" }}</b></div>
      <div><span>论文ID</span><b>{{ assignResult.thesis?.id || thesisId }}</b></div>
      <div><span>论文状态</span><b>{{ assignResult.thesis?.status || "-" }}</b></div>
      <div><span>已分配任务数</span><b>{{ assignResult.thesis?.assigned_count ?? "-" }}</b></div>
    </div>
  </section>
</template>
