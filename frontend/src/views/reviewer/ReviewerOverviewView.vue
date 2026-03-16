<script setup>
import { onMounted, ref } from "vue";
import { request } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";
import { useRouter } from "vue-router";

const tasks = ref([]);
const router = useRouter();

async function loadTasks() {
  try {
    const resp = await request("/api/reviewer/tasks");
    tasks.value = resp.items || [];
    notifySuccess("任务列表已刷新");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

onMounted(loadTasks);
</script>

<template>
  <section class="panel-card">
    <h4>我的任务列表</h4>
    <p class="muted">查看当前评阅教师分配到的全部任务。</p>

    <div class="row-actions">
      <button class="accent" @click="loadTasks">加载任务</button>
    </div>

    <table v-if="tasks.length" class="data-table">
      <thead>
        <tr>
          <th>任务ID</th>
          <th>论文ID</th>
          <th>标题</th>
          <th>状态</th>
          <th>截止时间</th>
          <th>逾期</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in tasks" :key="row.task_id">
          <td>{{ row.task_id }}</td>
          <td>{{ row.thesis_id }}</td>
          <td>
            <a 
              href="javascript:void(0)" 
              class="link-text" 
              @click="router.push(`/reviewer/tasks?taskId=${row.task_id}`)"
            >
              {{ row.thesis_title || '-' }}
            </a>
          </td>
          <td>{{ row.status }}</td>
          <td>{{ row.due_at || '-' }}</td>
          <td>{{ row.is_overdue ? '是' : '否' }}</td>
          <td>
            <div class="row-actions" style="margin: 0">
              <button class="accent" @click="router.push(`/reviewer/tasks?taskId=${row.task_id}`)">打开详情</button>
              <button class="warn" @click="router.push(`/reviewer/form?taskId=${row.task_id}`)">填写评阅</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
