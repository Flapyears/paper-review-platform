<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { requestJson } from "../services/api";
import { setSession } from "../stores/auth";
import { notifyError, notifySuccess } from "../stores/notice";

const router = useRouter();
const loading = ref(false);
const form = ref({
  username: "",
  password: "",
});
const showDevQuickLogin =
  import.meta.env.DEV || String(import.meta.env.VITE_SHOW_DEV_LOGIN || "") === "true";

function defaultRolePath(role) {
  if (role === "student") return "/student/overview";
  if (role === "admin") return "/admin/overview";
  return "/reviewer/overview";
}

async function submit() {
  loading.value = true;
  try {
    const resp = await requestJson("/api/auth/login", "POST", form.value);
    setSession({ token: resp.data.token, user: resp.data.user });
    notifySuccess("登录成功");
    router.push(defaultRolePath(resp.data.user.role));
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}

async function quickLogin(username, password) {
  if (loading.value) return;
  form.value.username = username;
  form.value.password = password;
  await submit();
}
</script>

<template>
  <section class="panel-card narrow login-card">
    <div class="login-head">
      <h3>账号登录</h3>
      <span class="login-badge">欢迎回来</span>
    </div>
    <p class="muted login-subtitle">输入账号和密码即可进入。</p>
    <div class="form-grid single">
      <label>
        用户名
        <input v-model="form.username" placeholder="请输入用户名" />
      </label>
      <label>
        密码
        <input v-model="form.password" type="password" placeholder="请输入密码" />
      </label>
    </div>
    <div class="row-actions">
      <button class="accent login-submit" :disabled="loading" @click="submit">
        {{ loading ? "登录中..." : "登录" }}
      </button>
    </div>

    <div v-if="showDevQuickLogin" class="dev-quick-login">
      <p class="muted">演示入口</p>
      <div class="row-actions">
        <button class="quick-role" :disabled="loading" @click="quickLogin('admin', 'admin')">管理员</button>
      </div>
    </div>
  </section>
</template>
