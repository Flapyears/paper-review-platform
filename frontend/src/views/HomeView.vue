<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { request } from "../services/api";
import { authState } from "../stores/auth";
import { notifyError } from "../stores/notice";
import { formatReviewTaskStatus, formatThesisStatus } from "../utils/status";

const loading = ref(false);
const todos = ref([]);
const recentItems = ref([]);

const roleEntry = computed(() => {
  if (authState.role === "student") {
    return {
      title: "学生首页",
      to: "/student/overview",
      links: [
        { label: "论文总览", to: "/student/overview" },
        { label: "论文信息", to: "/student/thesis" },
        { label: "上传与送审", to: "/student/submit" },
      ],
    };
  }
  if (authState.role === "admin") {
    return {
      title: "管理员首页",
      to: "/admin/overview",
      links: [
        { label: "评审看板", to: "/admin/overview" },
        { label: "论文列表", to: "/admin/thesis" },
        { label: "分配评阅", to: "/admin/assign" },
      ],
    };
  }
  return {
    title: "评阅教师首页",
    to: "/reviewer/overview",
    links: [
      { label: "任务列表", to: "/reviewer/overview" },
      { label: "任务详情", to: "/reviewer/tasks" },
      { label: "评阅提交", to: "/reviewer/form" },
    ],
  };
});

async function loadStudentWidget() {
  const resp = await request("/api/thesis/my");
  const thesis = resp.thesis;
  if (!thesis) {
    todos.value = ["填写论文信息", "上传终稿", "提交送审"];
    recentItems.value = ["当前暂无论文记录"];
    return;
  }

  if (thesis.status === "DRAFT") {
    todos.value = ["上传终稿", "核对论文标题和导师", "提交送审"];
  } else if (thesis.status === "SUBMITTED") {
    todos.value = ["等待安排评阅", "留意最新进展", "如被退回按提示修改"];
  } else if (thesis.status === "REVIEWING") {
    todos.value = ["等待评阅结果", "留意最新进展", "如有需要联系管理员"];
  } else {
    todos.value = ["评阅已完成", "留意后续通知"];
  }

  recentItems.value = [
    `论文标题：${thesis.title}`,
    `当前状态：${formatThesisStatus(thesis.status)}`,
    `当前版本号：${thesis.current_version_no ? `V${thesis.current_version_no}` : "-"}`,
    `退回原因：${thesis.return_reason || "无"}`,
  ];
}

async function loadAdminWidget() {
  const submitted = await request("/api/admin/thesis?status=SUBMITTED");
  todos.value = [
    `待安排论文：${(submitted.items || []).length} 篇`,
    "尽快安排评阅老师",
    "留意正在进行中的任务",
  ];

  recentItems.value = (submitted.items || []).slice(0, 5).map((row) => {
    return `论文#${row.id} ${row.title}（学生#${row.student_id}）`;
  });
  if (recentItems.value.length === 0) {
    recentItems.value = ["当前没有待分配论文"];
  }
}

async function loadReviewerWidget() {
  const tasksResp = await request("/api/reviewer/tasks");
  const tasks = tasksResp.items || [];
  const pending = tasks.filter((t) => t.status !== "SUBMITTED" && t.status !== "CANCELLED");
  todos.value = [
    `待处理任务：${pending.length} 个`,
    "先查看论文和任务要求",
    "完成后提交评阅意见",
  ];

  recentItems.value = tasks.slice(0, 5).map((task) => {
    return `任务#${task.task_id} ${task.thesis_title || "未命名论文"}（${formatReviewTaskStatus(task.status)}）`;
  });
  if (recentItems.value.length === 0) {
    recentItems.value = ["当前没有分配到任务"];
  }
}

async function loadWorkbench() {
  loading.value = true;
  try {
    if (authState.role === "student") {
      await loadStudentWidget();
    } else if (authState.role === "admin") {
      await loadAdminWidget();
    } else {
      await loadReviewerWidget();
    }
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}

watch(
  () => authState.role,
  () => {
    loadWorkbench();
  }
);

onMounted(loadWorkbench);
</script>

<template>
  <section class="panel-card">
    <h3>待办概览</h3>
    <p class="muted">先看待办，再进入对应页面处理。</p>

    <div class="row-actions">
      <RouterLink class="entry-link" :to="roleEntry.to">进入{{ roleEntry.title }}</RouterLink>
      <button :disabled="loading" @click="loadWorkbench">
        {{ loading ? "刷新中..." : "刷新内容" }}
      </button>
      <RouterLink class="entry-link" to="/help">查看操作说明</RouterLink>
    </div>

    <div class="dashboard-grid">
      <article class="dash-card">
        <h4>我的待办</h4>
        <ul>
          <li v-for="(item, idx) in todos" :key="idx">{{ item }}</li>
        </ul>
      </article>

      <article class="dash-card">
        <h4>快捷入口</h4>
        <div class="quick-links">
          <RouterLink v-for="link in roleEntry.links" :key="link.to" class="mini-link" :to="link.to">
            {{ link.label }}
          </RouterLink>
        </div>
      </article>

      <article class="dash-card">
        <h4>最近事项</h4>
        <ul>
          <li v-for="(item, idx) in recentItems" :key="idx">{{ item }}</li>
        </ul>
      </article>
    </div>
  </section>
</template>
