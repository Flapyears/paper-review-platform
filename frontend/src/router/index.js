import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import StudentView from "../views/StudentView.vue";
import AdminView from "../views/AdminView.vue";
import ReviewerView from "../views/ReviewerView.vue";

const routes = [
  { path: "/", component: HomeView },
  { path: "/student", component: StudentView },
  { path: "/admin", component: AdminView },
  { path: "/reviewer", component: ReviewerView },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
