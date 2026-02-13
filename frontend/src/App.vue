<script setup>
import { RouterLink, RouterView, useRoute } from "vue-router";
import { ref } from "vue";
import AuthPanel from "./components/AuthPanel.vue";
import ApiLog from "./components/ApiLog.vue";

const route = useRoute();
const log = ref("前端已就绪。请选择角色页面并执行流程。");
const error = ref(false);

function updateLog(payload) {
  log.value = JSON.stringify(payload, null, 2);
  error.value = false;
}

function updateError(message) {
  log.value = message;
  error.value = true;
}
</script>

<template>
  <main class="app-shell">
    <header class="hero">
      <div>
        <h1>Paper Review Platform</h1>
        <p>Vue 前端工作台，覆盖学生、管理员、评阅教师端核心流程。</p>
      </div>
      <nav class="nav-tabs">
        <RouterLink to="/" :class="{ active: route.path === '/' }">总览</RouterLink>
        <RouterLink to="/student" :class="{ active: route.path.startsWith('/student') }">学生</RouterLink>
        <RouterLink to="/admin" :class="{ active: route.path.startsWith('/admin') }">管理员</RouterLink>
        <RouterLink to="/reviewer" :class="{ active: route.path.startsWith('/reviewer') }">评阅教师</RouterLink>
      </nav>
    </header>

    <AuthPanel @saved="updateLog" />

    <RouterView @log="updateLog" @error="updateError" />

    <ApiLog :value="log" :error="error" />
  </main>
</template>
