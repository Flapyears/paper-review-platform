<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { setDevIdentity } from "../../stores/auth";
import { notifySuccess } from "../../stores/notice";

const router = useRouter();
const opened = ref(false);

const form = ref({
  userId: "1",
  role: "student",
  userName: "dev-user",
});

const presets = [
  { label: "学生#1", userId: "1", role: "student", userName: "student-1" },
  { label: "管理员#2", userId: "2", role: "admin", userName: "admin-2" },
  { label: "评阅教师#3", userId: "3", role: "reviewer", userName: "reviewer-3" },
  { label: "评阅教师#4", userId: "4", role: "reviewer", userName: "reviewer-4" },
];

function applyPreset(preset) {
  form.value = { ...preset };
}

function saveAndJump() {
  setDevIdentity(form.value);
  if (form.value.role === "student") router.push("/student/overview");
  else if (form.value.role === "admin") router.push("/admin/overview");
  else router.push("/reviewer/overview");
  notifySuccess("DevTools 身份已切换");
}
</script>

<template>
  <aside class="devtools" :class="{ opened }">
    <button class="devtools-toggle" @click="opened = !opened">
      {{ opened ? "关闭 DevTools" : "DevTools" }}
    </button>
    <div class="devtools-panel">
      <h4>Mock 身份切换</h4>
      <div class="devtools-presets">
        <button v-for="item in presets" :key="item.label" @click="applyPreset(item)">
          {{ item.label }}
        </button>
      </div>
      <div class="form-grid single">
        <label>
          用户ID
          <input v-model="form.userId" type="number" min="1" />
        </label>
        <label>
          角色
          <select v-model="form.role">
            <option value="student">student</option>
            <option value="admin">admin</option>
            <option value="reviewer">reviewer</option>
          </select>
        </label>
        <label>
          用户名
          <input v-model="form.userName" />
        </label>
      </div>
      <div class="row-actions">
        <button class="accent" @click="saveAndJump">保存并进入</button>
      </div>
    </div>
  </aside>
</template>
