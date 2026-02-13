<script setup>
import { onMounted, ref } from "vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const statusFilter = ref("ALL");
const theses = ref([]);
const selectedId = ref("");
const reason = ref("");

async function loadList() {
  try {
    const path = statusFilter.value === "ALL" ? "/api/admin/thesis" : `/api/admin/thesis?status=${statusFilter.value}`;
    const resp = await request(path);
    theses.value = resp.items || [];
    notifySuccess("论文列表已刷新");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

function pick(row) {
  selectedId.value = String(row.id);
}

async function returnForResubmit() {
  try {
    await requestJson(`/api/admin/thesis/${Number(selectedId.value)}/return`, "POST", {
      reason: reason.value || "请根据意见补交终稿",
    });
    notifySuccess("论文已退回补交");
    await loadList();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

onMounted(loadList);
</script>

<template>
  <section class="panel-card">
    <h4>论文列表</h4>
    <p class="muted">筛选论文状态并执行退回补交操作。</p>

    <div class="row-actions">
      <select v-model="statusFilter">
        <option value="ALL">全部状态</option>
        <option value="SUBMITTED">SUBMITTED</option>
        <option value="REVIEWING">REVIEWING</option>
        <option value="REVIEW_DONE">REVIEW_DONE</option>
        <option value="DRAFT">DRAFT</option>
      </select>
      <button class="accent" @click="loadList">加载列表</button>
    </div>

    <table v-if="theses.length" class="data-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>标题</th>
          <th>学生ID</th>
          <th>状态</th>
          <th>版本ID</th>
          <th>已分配任务数</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in theses" :key="row.id">
          <td>{{ row.id }}</td>
          <td>{{ row.title }}</td>
          <td>{{ row.student_id }}</td>
          <td>{{ row.status }}</td>
          <td>{{ row.current_version_id || '-' }}</td>
          <td>{{ row.assigned_count }}</td>
          <td><button @click="pick(row)">选择</button></td>
        </tr>
      </tbody>
    </table>

    <div class="form-grid three" style="margin-top: 12px">
      <label>
        选中论文ID
        <input v-model="selectedId" type="number" />
      </label>
      <label class="wide">
        退回原因
        <input v-model="reason" />
      </label>
      <button class="warn" @click="returnForResubmit">退回补交</button>
    </div>
  </section>
</template>
