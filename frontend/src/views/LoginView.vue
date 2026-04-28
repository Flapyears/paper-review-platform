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
  if (!form.value.username || !form.value.password) {
    notifyError("请输入用户名和密码");
    return;
  }
  loading.value = true;
  try {
    const resp = await requestJson("/api/auth/login", "POST", form.value);
    setSession({ token: resp.data.token, user: resp.data.user });
    notifySuccess("欢迎回来");
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
  <div class="login-container">
    <header class="login-header">
      <h2 class="title">账号登录</h2>
      <p class="subtitle">请使用您的学术账号访问系统</p>
    </header>

    <main class="login-form">
      <div class="input-group">
        <label for="username">用户名</label>
        <div class="input-wrapper">
          <span class="icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
          </span>
          <input
            id="username"
            v-model="form.username"
            type="text"
            placeholder="输入用户名"
            :disabled="loading"
            @keyup.enter="submit"
          />
        </div>
      </div>

      <div class="input-group">
        <label for="password">密码</label>
        <div class="input-wrapper">
          <span class="icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
          </span>
          <input
            id="password"
            v-model="form.password"
            type="password"
            placeholder="输入密码"
            :disabled="loading"
            @keyup.enter="submit"
          />
        </div>
      </div>

      <button class="accent login-submit-btn" :disabled="loading" @click="submit">
        <span v-if="!loading">立即登录</span>
        <span v-else class="loading-spinner"></span>
      </button>
    </main>

    <footer v-if="showDevQuickLogin" class="dev-footer">
      <div class="divider">
        <span>演示快捷入口</span>
      </div>
      <div class="quick-login-grid">
        <button class="ghost mini" @click="quickLogin('admin', 'admin')">
          管理员
        </button>
        <button class="ghost mini" @click="quickLogin('reviewer', 'reviewer')">
          评阅人
        </button>
        <button class="ghost mini" @click="quickLogin('student', 'student')">
          学生
        </button>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.login-container {
  width: 100%;
  max-width: 420px;
  background: var(--card);
  padding: 40px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--line);
}

.login-header {
  margin-bottom: 32px;
  text-align: center;
}

.title {
  font-size: 28px;
  font-weight: 700;
  color: var(--ink);
  margin: 0 0 8px;
  font-family: "Noto Serif SC", serif;
}

.subtitle {
  color: var(--muted);
  font-size: 15px;
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-group label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrapper .icon {
  position: absolute;
  left: 14px;
  color: var(--muted);
  display: flex;
  pointer-events: none;
}

.input-wrapper input {
  padding-left: 44px;
  height: 50px;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 15px;
  transition: all 0.2s ease;
}

.input-wrapper input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px var(--accent-glow);
  background: #fff;
}

.login-submit-btn {
  margin-top: 10px;
  height: 50px;
  font-size: 16px;
  border-radius: 12px;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.dev-footer {
  margin-top: 32px;
}

.divider {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.divider::before,
.divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--line);
}

.divider span {
  padding: 0 12px;
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.quick-login-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.mini {
  padding: 8px 4px;
  font-size: 13px;
  border-radius: 8px;
}

@media (max-width: 480px) {
  .login-container {
    padding: 30px 20px;
    box-shadow: none;
    border: none;
    background: transparent;
  }
}
</style>
