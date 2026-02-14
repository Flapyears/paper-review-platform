<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { request, requestJson } from "../../services/api";
import { setDevIdentity } from "../../stores/auth";
import { notifyError, notifySuccess } from "../../stores/notice";

const router = useRouter();
const opened = ref(false);
const seeding = ref(false);
const accounts = ref([]);

const form = ref({
  userId: "1",
  role: "student",
  userName: "dev-user",
});

const seedForm = ref({
  students: 10,
  reviewers: 10,
  theses: 10,
});

const staticPresets = [
  { label: "学生#1", userId: "1", role: "student", userName: "student-1" },
  { label: "管理员#2", userId: "2", role: "admin", userName: "admin-2" },
  { label: "评阅教师#3", userId: "3", role: "reviewer", userName: "reviewer-3" },
  { label: "评阅教师#4", userId: "4", role: "reviewer", userName: "reviewer-4" },
];

const accountPresets = computed(() =>
  accounts.value.map((item) => ({
    label: `${item.role} #${item.user_id} (${item.username})`,
    userId: String(item.user_id),
    role: item.role,
    userName: item.name,
  }))
);

const groupedAccountPresets = computed(() => {
  const groups = {
    admin: accountPresets.value.filter((x) => x.role === "admin"),
    student: accountPresets.value.filter((x) => x.role === "student"),
    reviewer: accountPresets.value.filter((x) => x.role === "reviewer"),
  };
  return groups;
});

function applyPreset(preset) {
  form.value = { ...preset };
}

function quickSwitch(preset) {
  applyPreset(preset);
  saveAndJump();
}

function saveAndJump() {
  setDevIdentity(form.value);
  if (form.value.role === "student") router.push("/student/overview");
  else if (form.value.role === "admin") router.push("/admin/overview");
  else router.push("/reviewer/overview");
  notifySuccess("DevTools 身份已切换");
}

async function loadAccounts() {
  try {
    const resp = await request("/api/dev/accounts");
    accounts.value = resp.items || [];
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function seedUsers() {
  seeding.value = true;
  try {
    const resp = await requestJson("/api/dev/seed/users", "POST", {
      students: Number(seedForm.value.students) || 0,
      reviewers: Number(seedForm.value.reviewers) || 0,
      admins: 0,
    });
    notifySuccess(`已生成账号 ${resp.data?.created_count || 0} 个`);
    await loadAccounts();
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    seeding.value = false;
  }
}

async function seedWorkflow() {
  seeding.value = true;
  try {
    const resp = await requestJson("/api/dev/seed/workflow", "POST", {
      students: Number(seedForm.value.students) || 1,
      reviewers: Number(seedForm.value.reviewers) || 2,
      theses: Number(seedForm.value.theses) || 1,
      assign_per_thesis: 2,
      submit_thesis: true,
    });
    notifySuccess(`已生成论文 ${resp.data?.theses || 0} 篇，任务 ${resp.data?.tasks || 0} 条`);
    await loadAccounts();
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    seeding.value = false;
  }
}

async function resetDevData() {
  seeding.value = true;
  try {
    await requestJson("/api/dev/reset", "POST", { reseed_defaults: true });
    notifySuccess("开发数据已重置并恢复默认账号");
    await loadAccounts();
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    seeding.value = false;
  }
}

onMounted(loadAccounts);
</script>

<template>
  <aside class="devtools" :class="{ opened }">
    <button class="devtools-toggle" @click="opened = !opened">
      {{ opened ? "关闭 DevTools" : "DevTools" }}
    </button>
    <div class="devtools-panel">
      <h4>Mock 身份切换</h4>
      <div class="devtools-presets">
        <button v-for="item in staticPresets" :key="item.label" @click="quickSwitch(item)">
          {{ item.label }}
        </button>
      </div>

      <h4>真实账号快速切换</h4>
      <div class="devtools-groups">
        <div v-if="groupedAccountPresets.admin.length" class="devtools-group">
          <p class="devtools-group-title">管理员</p>
          <div class="devtools-presets">
            <button v-for="item in groupedAccountPresets.admin" :key="item.label" @click="quickSwitch(item)">
              {{ item.label }}
            </button>
          </div>
        </div>
        <div v-if="groupedAccountPresets.student.length" class="devtools-group">
          <p class="devtools-group-title">学生</p>
          <div class="devtools-presets">
            <button v-for="item in groupedAccountPresets.student" :key="item.label" @click="quickSwitch(item)">
              {{ item.label }}
            </button>
          </div>
        </div>
        <div v-if="groupedAccountPresets.reviewer.length" class="devtools-group">
          <p class="devtools-group-title">评阅教师</p>
          <div class="devtools-presets">
            <button v-for="item in groupedAccountPresets.reviewer" :key="item.label" @click="quickSwitch(item)">
              {{ item.label }}
            </button>
          </div>
        </div>
      </div>

      <h4>开发数据一键生成</h4>
      <div class="form-grid single">
        <label>
          学生数
          <input v-model.number="seedForm.students" type="number" min="1" />
        </label>
        <label>
          评阅教师数
          <input v-model.number="seedForm.reviewers" type="number" min="2" />
        </label>
        <label>
          论文数
          <input v-model.number="seedForm.theses" type="number" min="1" />
        </label>
      </div>
      <div class="row-actions">
        <button :disabled="seeding" @click="seedUsers">生成账号</button>
        <button :disabled="seeding" @click="seedWorkflow">生成流程数据</button>
        <button class="warn" :disabled="seeding" @click="resetDevData">重置数据</button>
        <button :disabled="seeding" @click="loadAccounts">刷新账号</button>
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
