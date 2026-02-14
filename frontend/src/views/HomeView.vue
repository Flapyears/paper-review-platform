<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { request } from "../services/api";
import { authState } from "../stores/auth";
import { notifyError } from "../stores/notice";

const loading = ref(false);
const todos = ref([]);
const recentItems = ref([]);

const roleEntry = computed(() => {
  if (authState.role === "student") {
    return {
      title: "学生工作区",
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
      title: "管理员工作区",
      to: "/admin/overview",
      links: [
        { label: "评审看板", to: "/admin/overview" },
        { label: "论文列表", to: "/admin/thesis" },
        { label: "分配评阅", to: "/admin/assign" },
      ],
    };
  }
  return {
    title: "评阅教师工作区",
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
    todos.value = ["创建论文并填写标题", "上传终稿文件", "提交送审"];
    recentItems.value = ["当前暂无论文记录"];
    return;
  }

  if (thesis.status === "DRAFT") {
    todos.value = ["上传终稿并提交送审", "确认导师与标题信息", "等待管理员分配评阅"];
  } else if (thesis.status === "SUBMITTED") {
    todos.value = ["等待管理员分配评阅", "关注状态变化", "如被退回请根据原因修订"];
  } else if (thesis.status === "REVIEWING") {
    todos.value = ["等待评阅教师提交结果", "关注进度变化", "必要时联系管理员"];
  } else {
    todos.value = ["评阅已完成", "可联系管理员查看后续安排"];
  }

  recentItems.value = [
    `论文标题：${thesis.title}`,
    `当前状态：${thesis.status}`,
    `当前版本号：${thesis.current_version_no ? `V${thesis.current_version_no}` : "-"}`,
    `退回原因：${thesis.return_reason || "无"}`,
  ];
}

async function loadAdminWidget() {
  const submitted = await request("/api/admin/thesis?status=SUBMITTED");
  todos.value = [
    `待分配论文：${(submitted.items || []).length} 篇`,
    "进入分配评阅页面完成任务生成",
    "跟踪已分配任务完成度",
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
    "打开任务详情并下载绑定论文",
    "填写评阅表并提交",
  ];

  recentItems.value = tasks.slice(0, 5).map((task) => {
    return `任务#${task.task_id} ${task.thesis_title || "未命名论文"}（${task.status}）`;
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
    <h3>工作台</h3>
    <p class="muted">以下内容根据当前登录角色自动展示。</p>

    <div class="row-actions">
      <RouterLink class="entry-link" :to="roleEntry.to">进入{{ roleEntry.title }}</RouterLink>
      <button :disabled="loading" @click="loadWorkbench">
        {{ loading ? "刷新中..." : "刷新工作台" }}
      </button>
      <RouterLink class="entry-link" to="/help">查看流程帮助</RouterLink>
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
