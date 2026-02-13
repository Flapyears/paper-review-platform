<script setup>
import { authState, saveAuth } from "../stores/auth";

const emit = defineEmits(["saved"]);

function onSave() {
  saveAuth();
  emit("saved", {
    userId: authState.userId,
    role: authState.role,
    userName: authState.userName,
  });
}
</script>

<template>
  <section class="panel-card">
    <h3>请求身份</h3>
    <p class="muted">所有 API 请求都使用以下 Header。</p>
    <div class="form-grid">
      <label>
        用户ID
        <input v-model="authState.userId" type="number" min="1" />
      </label>
      <label>
        角色
        <select v-model="authState.role">
          <option value="student">student</option>
          <option value="admin">admin</option>
          <option value="reviewer">reviewer</option>
        </select>
      </label>
      <label class="wide">
        用户名
        <input v-model="authState.userName" />
      </label>
      <button type="button" class="accent" @click="onSave">保存身份</button>
    </div>
  </section>
</template>
