<script setup>
import { computed, onMounted, ref } from "vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";
import PaginationBar from "../../components/common/PaginationBar.vue";

const reviewers = ref([]);
const loading = ref(false);
const keyword = ref("");
const activeFilter = ref("ALL");
const selectedId = ref("");
const resetPassword = ref("");
const page = ref(1);
const pageSize = ref(10);

const createForm = ref({
  username: "",
  password: "",
  name: "",
  email: "",
  department: "",
});

const editForm = ref({
  name: "",
  email: "",
  department: "",
});

const selectedReviewer = computed(() => reviewers.value.find((x) => x.id === Number(selectedId.value)) || null);
const pagedReviewers = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return reviewers.value.slice(start, start + pageSize.value);
});

async function loadReviewers() {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    if (keyword.value.trim()) params.set("q", keyword.value.trim());
    if (activeFilter.value === "ACTIVE") params.set("is_active", "true");
    if (activeFilter.value === "INACTIVE") params.set("is_active", "false");
    const path = params.size ? `/api/admin/reviewers/manage?${params.toString()}` : "/api/admin/reviewers/manage";
    const resp = await request(path);
    reviewers.value = resp.items || [];
    page.value = 1;
    if (selectedId.value) {
      const target = reviewers.value.find((x) => x.id === Number(selectedId.value));
      if (target) {
        editForm.value = {
          name: target.name || "",
          email: target.email || "",
          department: target.department === "未设置科室" ? "" : target.department || "",
        };
      }
    }
    notifySuccess("评阅教师列表已刷新");
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}

function selectReviewer(row) {
  selectedId.value = String(row.id);
  editForm.value = {
    name: row.name || "",
    email: row.email || "",
    department: row.department === "未设置科室" ? "" : row.department || "",
  };
  resetPassword.value = "";
}

async function createReviewer() {
  try {
    await requestJson("/api/admin/reviewers", "POST", {
      username: createForm.value.username.trim(),
      password: createForm.value.password,
      name: createForm.value.name.trim(),
      email: createForm.value.email.trim() || null,
      department: createForm.value.department.trim() || null,
    });
    notifySuccess("评阅教师创建成功");
    createForm.value = { username: "", password: "", name: "", email: "", department: "" };
    await loadReviewers();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function updateReviewer() {
  try {
    if (!selectedReviewer.value) throw new Error("请先选择评阅教师");
    await requestJson(`/api/admin/reviewers/${selectedReviewer.value.id}`, "PATCH", {
      name: editForm.value.name.trim(),
      email: editForm.value.email.trim() || null,
      department: editForm.value.department.trim() || null,
    });
    notifySuccess("教师信息已更新");
    await loadReviewers();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function toggleActive() {
  try {
    if (!selectedReviewer.value) throw new Error("请先选择评阅教师");
    await requestJson(`/api/admin/reviewers/${selectedReviewer.value.id}/toggle-active`, "POST", {});
    notifySuccess("账号状态已切换");
    await loadReviewers();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function resetReviewerPassword() {
  try {
    if (!selectedReviewer.value) throw new Error("请先选择评阅教师");
    if (!resetPassword.value) throw new Error("请输入新密码");
    await requestJson(`/api/admin/reviewers/${selectedReviewer.value.id}/reset-password`, "POST", {
      password: resetPassword.value,
    });
    notifySuccess("密码已重置");
    resetPassword.value = "";
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

onMounted(loadReviewers);
</script>

<template>
  <section class="panel-card">
    <h4>评阅教师管理</h4>
    <p class="muted">管理员可查看教师负载，创建教师账号，编辑信息并执行启停用或密码重置。</p>

    <div class="form-grid">
      <label>
        关键词
        <input v-model="keyword" placeholder="姓名 / ID / 用户名" />
      </label>
      <label>
        账号状态
        <select v-model="activeFilter">
          <option value="ALL">全部</option>
          <option value="ACTIVE">仅启用</option>
          <option value="INACTIVE">仅停用</option>
        </select>
      </label>
      <div></div>
      <button class="accent" :disabled="loading" @click="loadReviewers">
        {{ loading ? "加载中..." : "刷新教师列表" }}
      </button>
    </div>

    <table v-if="reviewers.length" class="data-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>姓名</th>
          <th>用户名</th>
          <th>科室</th>
          <th>状态</th>
          <th>活跃任务</th>
          <th>已提交</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in pagedReviewers" :key="row.id" :class="{ active: selectedId === String(row.id) }">
          <td>#{{ row.id }}</td>
          <td>{{ row.name }}</td>
          <td>{{ row.username || "-" }}</td>
          <td>{{ row.department || "-" }}</td>
          <td>{{ row.is_active ? "启用" : "停用" }}</td>
          <td>{{ row.active_task_count }}</td>
          <td>{{ row.submitted_task_count }}</td>
          <td><button @click="selectReviewer(row)">选择</button></td>
        </tr>
      </tbody>
    </table>
    <PaginationBar v-model:current="page" v-model:pageSize="pageSize" :total="reviewers.length" />
    <div v-if="!reviewers.length" class="empty-box">暂无评阅教师数据。</div>

    <h4 style="margin-top: 16px">新增评阅教师</h4>
    <div class="form-grid">
      <label>
        用户名
        <input v-model="createForm.username" />
      </label>
      <label>
        初始密码
        <input v-model="createForm.password" type="password" />
      </label>
      <label>
        姓名
        <input v-model="createForm.name" />
      </label>
      <label>
        邮箱
        <input v-model="createForm.email" />
      </label>
      <label>
        科室
        <input v-model="createForm.department" placeholder="如：计算机系" />
      </label>
      <button class="accent" @click="createReviewer">创建账号</button>
    </div>

    <h4 style="margin-top: 16px">编辑与账号操作</h4>
    <div v-if="selectedReviewer" class="detail-grid">
      <div><span>已选教师</span><b>{{ selectedReviewer.name }} (#{{ selectedReviewer.id }})</b></div>
      <div><span>当前状态</span><b>{{ selectedReviewer.is_active ? "启用" : "停用" }}</b></div>
    </div>

    <div class="form-grid" style="margin-top: 8px">
      <label>
        姓名
        <input v-model="editForm.name" :disabled="!selectedReviewer" />
      </label>
      <label>
        邮箱
        <input v-model="editForm.email" :disabled="!selectedReviewer" />
      </label>
      <label>
        科室
        <input v-model="editForm.department" :disabled="!selectedReviewer" />
      </label>
      <button :disabled="!selectedReviewer" @click="updateReviewer">保存教师信息</button>
    </div>

    <div class="form-grid" style="margin-top: 8px">
      <label>
        新密码
        <input v-model="resetPassword" type="password" :disabled="!selectedReviewer" />
      </label>
      <div></div>
      <div></div>
      <button :disabled="!selectedReviewer" @click="toggleActive">
        {{ selectedReviewer?.is_active ? "停用账号" : "启用账号" }}
      </button>
      <button class="warn" :disabled="!selectedReviewer" @click="resetReviewerPassword">重置密码</button>
    </div>
  </section>
</template>
