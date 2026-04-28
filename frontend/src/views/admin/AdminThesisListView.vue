<script setup>
import { computed, onMounted, ref } from "vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";
import PaginationBar from "../../components/common/PaginationBar.vue";
import { formatThesisStatus } from "../../utils/status";

const statusFilter = ref("ALL");
const theses = ref([]);
const selectedId = ref("");
const reason = ref("");
const page = ref(1);
const pageSize = ref(10);

const pagedTheses = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return theses.value.slice(start, start + pageSize.value);
});

async function loadList() {
  try {
    const path = statusFilter.value === "ALL" ? "/api/admin/thesis" : `/api/admin/thesis?status=${statusFilter.value}`;
    const resp = await request(path);
    theses.value = resp.items || [];
    page.value = 1;
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
    <p class="muted">查看论文进展，也可以在这里退回补交。</p>

    <div class="row-actions">
      <select v-model="statusFilter">
        <option value="ALL">全部状态</option>
        <option value="SUBMITTED">已提交待分配</option>
        <option value="REVIEWING">评阅中</option>
        <option value="REVIEW_DONE">评阅完成</option>
        <option value="DRAFT">草稿中</option>
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
          <th>版本号</th>
          <th>已分配任务数</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in pagedTheses" :key="row.id">
          <td>{{ row.id }}</td>
          <td>{{ row.title }}</td>
          <td>{{ row.student_id }}</td>
          <td>{{ formatThesisStatus(row.status) }}</td>
          <td>{{ row.current_version_no ? `V${row.current_version_no}` : '-' }}</td>
          <td>{{ row.assigned_count }}</td>
          <td><button @click="pick(row)">选择</button></td>
        </tr>
      </tbody>
    </table>
    <PaginationBar v-model:current="page" v-model:pageSize="pageSize" :total="theses.length" />

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
