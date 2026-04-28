<script setup>
import { computed, onMounted, ref } from "vue";
import { request } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";
import PaginationBar from "../../components/common/PaginationBar.vue";
import { formatThesisStatus } from "../../utils/status";

const summary = ref({ submittedCount: 0, inReviewCount: 0, doneCount: 0 });
const progressRows = ref([]);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(10);

const pagedProgressRows = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return progressRows.value.slice(start, start + pageSize.value);
});

async function refreshDashboard(showToast = true) {
  loading.value = true;
  try {
    const thesisResp = await request("/api/admin/thesis");
    const progressResp = await request("/api/admin/review-progress");

    const list = thesisResp.items || [];
    summary.value = {
      submittedCount: list.filter((x) => x.status === "SUBMITTED").length,
      inReviewCount: list.filter((x) => x.status === "REVIEWING").length,
      doneCount: list.filter((x) => x.status === "REVIEW_DONE").length,
    };
    progressRows.value = progressResp.items || [];
    page.value = 1;
    if (showToast) {
      notifySuccess("看板已更新");
    }
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  refreshDashboard(false);
});
</script>

<template>
  <section class="panel-card">
    <h4>评审看板</h4>
    <p class="muted">这里能快速看到论文进展和评阅完成情况。</p>

    <div class="row-actions">
      <button class="accent" :disabled="loading" @click="refreshDashboard">
        {{ loading ? "刷新中..." : "刷新数据" }}
      </button>
    </div>

    <div class="metric-grid">
      <article>
        <span>待分配</span>
        <b>{{ summary.submittedCount }}</b>
      </article>
      <article>
        <span>评阅中</span>
        <b>{{ summary.inReviewCount }}</b>
      </article>
      <article>
        <span>已完成</span>
        <b>{{ summary.doneCount }}</b>
      </article>
    </div>

    <table v-if="progressRows.length" class="data-table">
      <thead>
        <tr>
          <th>论文ID</th>
          <th>论文状态</th>
          <th>活跃任务</th>
          <th>已提交任务</th>
          <th>完成率</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in pagedProgressRows" :key="row.thesis_id">
          <td>{{ row.thesis_id }}</td>
          <td>{{ formatThesisStatus(row.thesis_status) }}</td>
          <td>{{ row.total_active_tasks }}</td>
          <td>{{ row.submitted_tasks }}</td>
          <td>{{ row.completion_percent }}%</td>
        </tr>
      </tbody>
    </table>
    <PaginationBar v-model:current="page" v-model:pageSize="pageSize" :total="progressRows.length" />
  </section>
</template>
