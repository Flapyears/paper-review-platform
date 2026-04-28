<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { authState, clearSession, syncSessionUser } from "../stores/auth";
import { request } from "../services/api";
import { clearNotice, noticeState, notifyError, notifySuccess } from "../stores/notice";
import BaseModal from "../components/common/BaseModal.vue";
import NoticeBanner from "../components/common/NoticeBanner.vue";
import PasswordChangeForm from "../components/common/PasswordChangeForm.vue";
import DevToolsDrawer from "../components/devtools/DevToolsDrawer.vue";

const route = useRoute();
const router = useRouter();
const syncingProfile = ref(false);

const showDevTools =
  import.meta.env.DEV || String(import.meta.env.VITE_ENABLE_DEVTOOLS || "") === "true";

const roleLabel = computed(() => {
  if (authState.role === "student") return "学生";
  if (authState.role === "admin") return "管理员";
  if (authState.role === "reviewer") return "评阅教师";
  return "未登录";
});

const sideMenu = computed(() => {
  if (authState.role === "student") {
    return [
      { to: "/", label: "工作台" },
      { to: "/student/overview", label: "论文总览" },
      { to: "/student/thesis", label: "论文信息" },
      { to: "/student/submit", label: "上传与送审" },
      { to: "/account/password", label: "修改密码" },
      { to: "/help", label: "帮助" },
    ];
  }
  if (authState.role === "admin") {
    return [
      { to: "/", label: "工作台" },
      { to: "/admin/overview", label: "评审看板" },
      { to: "/admin/thesis", label: "论文列表" },
      { to: "/admin/assign", label: "分配评阅" },
      { to: "/admin/tasks", label: "任务操作" },
      { to: "/admin/reviewers", label: "教师管理" },
      { to: "/admin/students", label: "学生管理" },
      { to: "/account/password", label: "修改密码" },
      { to: "/help", label: "帮助" },
    ];
  }
  return [
    { to: "/", label: "工作台" },
    { to: "/reviewer/overview", label: "任务列表" },
    { to: "/reviewer/tasks", label: "任务详情" },
    { to: "/reviewer/form", label: "评阅提交" },
    { to: "/account/password", label: "修改密码" },
    { to: "/help", label: "帮助" },
  ];
});

function isMenuActive(to) {
  return route.path === to || route.path.startsWith(`${to}/`);
}

async function logout() {
  try {
    if (authState.token) {
      await request("/api/auth/logout", { method: "POST" });
    }
  } finally {
    clearSession();
    notifySuccess("已退出登录");
    router.push("/login");
  }
}

async function syncProfile() {
  if (!authState.token || syncingProfile.value) return;
  syncingProfile.value = true;
  try {
    const resp = await request("/api/auth/me");
    if (resp?.data?.user) {
      syncSessionUser(resp.data.user);
    }
  } catch (err) {
    clearSession();
    notifyError(err.message || "登录状态已失效，请重新登录");
    router.push("/login");
  } finally {
    syncingProfile.value = false;
  }
}

function handlePasswordChanged() {
  if (route.path !== "/account/password") {
    router.push("/");
  }
}

onMounted(syncProfile);
</script>

<template>
  <div class="main-layout">
    <header class="main-topbar">
      <div class="brand">毕业论文评审平台</div>
      <div class="top-actions">
        <span class="role-badge">{{ roleLabel }}</span>
        <span class="user-badge">#{{ authState.userId }} / {{ authState.userName }}</span>
        <button class="ghost" @click="logout">退出登录</button>
      </div>
    </header>

    <div class="main-body">
      <aside class="main-sidebar">
        <nav class="side-nav">
          <div class="side-nav-title">导航菜单</div>
          <RouterLink
            v-for="item in sideMenu"
            :key="item.to"
            :to="item.to"
            :class="{ active: isMenuActive(item.to) }"
          >
            {{ item.label }}
          </RouterLink>
        </nav>
      </aside>

      <section class="main-content">
        <div v-if="noticeState.message" class="content-toolbar">
          <NoticeBanner :message="noticeState.message" :type="noticeState.type" />
          <button class="ghost" @click="clearNotice">清除提示</button>
        </div>
        <RouterView />
      </section>
    </div>

    <BaseModal
      v-model="authState.mustChangePassword"
      title="修改密码"
      width="520px"
      :closable="false"
      :closeOnBackdrop="false"
    >
      <PasswordChangeForm force-mode @success="handlePasswordChanged" />
    </BaseModal>

    <DevToolsDrawer v-if="showDevTools" />
  </div>
</template>
