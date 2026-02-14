import { createRouter, createWebHistory } from "vue-router";
import AuthLayout from "../layouts/AuthLayout.vue";
import MainLayout from "../layouts/MainLayout.vue";
import HomeView from "../views/HomeView.vue";
import HelpView from "../views/HelpView.vue";
import LoginView from "../views/LoginView.vue";
import StudentOverviewView from "../views/student/StudentOverviewView.vue";
import StudentThesisManageView from "../views/student/StudentThesisManageView.vue";
import StudentSubmitView from "../views/student/StudentSubmitView.vue";
import AdminOverviewView from "../views/admin/AdminOverviewView.vue";
import AdminThesisListView from "../views/admin/AdminThesisListView.vue";
import AdminAssignView from "../views/admin/AdminAssignView.vue";
import AdminTaskOpsView from "../views/admin/AdminTaskOpsView.vue";
import AdminReviewerManageView from "../views/admin/AdminReviewerManageView.vue";
import ReviewerOverviewView from "../views/reviewer/ReviewerOverviewView.vue";
import ReviewerTaskDetailView from "../views/reviewer/ReviewerTaskDetailView.vue";
import ReviewerFormSubmitView from "../views/reviewer/ReviewerFormSubmitView.vue";
import { authState } from "../stores/auth";

const defaultRolePath = {
  student: "/student/overview",
  admin: "/admin/overview",
  reviewer: "/reviewer/overview",
};

const isDevtoolsEnabled =
  import.meta.env.DEV || String(import.meta.env.VITE_ENABLE_DEVTOOLS || "") === "true";

const routes = [
  {
    path: "/login",
    component: AuthLayout,
    children: [{ path: "", component: LoginView }],
  },
  {
    path: "/",
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: "", component: HomeView },
      { path: "help", component: HelpView },
      {
        path: "student",
        meta: { requiresRole: "student" },
        children: [
          { path: "", redirect: "/student/overview" },
          { path: "overview", component: StudentOverviewView },
          { path: "thesis", component: StudentThesisManageView },
          { path: "submit", component: StudentSubmitView },
        ],
      },
      {
        path: "admin",
        meta: { requiresRole: "admin" },
        children: [
          { path: "", redirect: "/admin/overview" },
          { path: "overview", component: AdminOverviewView },
          { path: "thesis", component: AdminThesisListView },
          { path: "assign", component: AdminAssignView },
          { path: "tasks", component: AdminTaskOpsView },
          { path: "reviewers", component: AdminReviewerManageView },
        ],
      },
      {
        path: "reviewer",
        meta: { requiresRole: "reviewer" },
        children: [
          { path: "", redirect: "/reviewer/overview" },
          { path: "overview", component: ReviewerOverviewView },
          { path: "tasks", component: ReviewerTaskDetailView },
          { path: "form", component: ReviewerFormSubmitView },
        ],
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const isAuth = authState.isAuthenticated || (isDevtoolsEnabled && authState.role && authState.userId);
  const requiresAuth = to.matched.some((record) => record.meta?.requiresAuth);
  if (requiresAuth && !isAuth) {
    return "/login";
  }

  if (to.path === "/login" && isAuth) {
    return defaultRolePath[authState.role] || "/";
  }

  const requiredRole = to.matched.find((record) => record.meta?.requiresRole)?.meta?.requiresRole;
  if (requiredRole && authState.role !== requiredRole) {
    return defaultRolePath[authState.role] || "/";
  }
  return true;
});

export default router;
