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
  <div class="home-container">
    <section class="panel-card">
      <header class="home-header">
        <div class="header-main">
          <h3>待办概览</h3>
          <p class="muted">欢迎回来，以下是您当前需要关注的事项。</p>
        </div>
        <div class="header-actions">
          <button class="ghost refresh-btn" :disabled="loading" @click="loadWorkbench">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            {{ loading ? "刷新中..." : "刷新数据" }}
          </button>
        </div>
      </header>

      <div class="action-banner">
        <RouterLink class="entry-link major-btn" :to="roleEntry.to">
          <span>进入{{ roleEntry.title }}</span>
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </RouterLink>
        <RouterLink class="mini-link" to="/help">操作指南</RouterLink>
      </div>

      <div class="dashboard-grid">
        <article class="dash-card">
          <div class="card-icon todo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </div>
          <h4>我的待办</h4>
          <ul>
            <li v-for="(item, idx) in todos" :key="idx">{{ item }}</li>
          </ul>
        </article>

        <article class="dash-card">
          <div class="card-icon link-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
          </div>
          <h4>快捷入口</h4>
          <div class="quick-links">
            <RouterLink v-for="link in roleEntry.links" :key="link.to" class="mini-link" :to="link.to">
              {{ link.label }}
            </RouterLink>
          </div>
        </article>

        <article class="dash-card">
          <div class="card-icon event-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h4>最近事项</h4>
          <ul>
            <li v-for="(item, idx) in recentItems" :key="idx">{{ item }}</li>
          </ul>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-container {
  animation: fade-in 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.home-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-main h3 {
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 4px;
  color: var(--ink);
}

.action-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: var(--bg-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 12px;
}

.major-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  font-size: 15px;
}

.icon {
  width: 18px;
  height: 18px;
}

.card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.card-icon svg {
  width: 20px;
  height: 20px;
}

.todo-icon { background: var(--success-soft); color: var(--success); }
.link-icon { background: var(--primary-soft); color: var(--primary); }
.event-icon { background: var(--accent-soft); color: var(--accent); }

.refresh-btn {
  padding: 8px 16px;
  font-size: 14px;
  gap: 6px;
}

.refresh-btn .icon {
  width: 14px;
  height: 14px;
}

@media (max-width: 768px) {
  .home-header {
    flex-direction: column;
    gap: 16px;
  }
  .header-actions {
    width: 100%;
  }
  .refresh-btn {
    width: 100%;
  }
}
</style>
