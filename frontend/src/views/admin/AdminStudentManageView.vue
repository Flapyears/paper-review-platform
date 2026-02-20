<script setup>
import { computed, onMounted, ref } from "vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";
import PaginationBar from "../../components/common/PaginationBar.vue";

const students = ref([]);
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
  student_no: "",
  email: "",
});

const editForm = ref({
  name: "",
  student_no: "",
  email: "",
});

const selectedStudent = computed(() => students.value.find((x) => x.id === Number(selectedId.value)) || null);
const pagedStudents = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return students.value.slice(start, start + pageSize.value);
});

async function loadStudents() {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    if (keyword.value.trim()) params.set("q", keyword.value.trim());
    if (activeFilter.value === "ACTIVE") params.set("is_active", "true");
    if (activeFilter.value === "INACTIVE") params.set("is_active", "false");
    const path = params.size ? `/api/admin/students/manage?${params.toString()}` : "/api/admin/students/manage";
    const resp = await request(path);
    students.value = resp.items || [];
    page.value = 1;
    if (selectedId.value) {
      const target = students.value.find((x) => x.id === Number(selectedId.value));
      if (target) {
        editForm.value = {
          name: target.name || "",
          student_no: target.student_no || "",
          email: target.email || "",
        };
      }
    }
    notifySuccess("学生列表已刷新");
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}

function selectStudent(row) {
  selectedId.value = String(row.id);
  editForm.value = {
    name: row.name || "",
    student_no: row.student_no || "",
    email: row.email || "",
  };
  resetPassword.value = "";
}

async function createStudent() {
  try {
    await requestJson("/api/admin/students", "POST", {
      username: createForm.value.username.trim(),
      password: createForm.value.password,
      name: createForm.value.name.trim(),
      student_no: createForm.value.student_no.trim() || null,
      email: createForm.value.email.trim() || null,
    });
    notifySuccess("学生账号创建成功");
    createForm.value = { username: "", password: "", name: "", student_no: "", email: "" };
    await loadStudents();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function updateStudent() {
  try {
    if (!selectedStudent.value) throw new Error("请先选择学生");
    await requestJson(`/api/admin/students/${selectedStudent.value.id}`, "PATCH", {
      name: editForm.value.name.trim(),
      student_no: editForm.value.student_no.trim() || null,
      email: editForm.value.email.trim() || null,
    });
    notifySuccess("学生信息已更新");
    await loadStudents();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function toggleActive() {
  try {
    if (!selectedStudent.value) throw new Error("请先选择学生");
    await requestJson(`/api/admin/students/${selectedStudent.value.id}/toggle-active`, "POST", {});
    notifySuccess("学生账号状态已切换");
    await loadStudents();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function resetStudentPassword() {
  try {
    if (!selectedStudent.value) throw new Error("请先选择学生");
    if (!resetPassword.value) throw new Error("请输入新密码");
    await requestJson(`/api/admin/students/${selectedStudent.value.id}/reset-password`, "POST", {
      password: resetPassword.value,
    });
    notifySuccess("学生密码已重置");
    resetPassword.value = "";
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

onMounted(loadStudents);
</script>

<template>
  <section class="panel-card">
    <h4>学生账号管理</h4>
    <p class="muted">管理员可创建学生账号，维护学号/邮箱，启停用账号并重置密码。</p>

    <div class="form-grid">
      <label>
        关键词
        <input v-model="keyword" placeholder="姓名 / ID / 学号 / 用户名" />
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
      <button class="accent" :disabled="loading" @click="loadStudents">
        {{ loading ? "加载中..." : "刷新学生列表" }}
      </button>
    </div>

    <table v-if="students.length" class="data-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>姓名</th>
          <th>学号</th>
          <th>用户名</th>
          <th>状态</th>
          <th>论文数</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in pagedStudents" :key="row.id" :class="{ active: selectedId === String(row.id) }">
          <td>#{{ row.id }}</td>
          <td>{{ row.name }}</td>
          <td>{{ row.student_no || "-" }}</td>
          <td>{{ row.username || "-" }}</td>
          <td>{{ row.is_active ? "启用" : "停用" }}</td>
          <td>{{ row.thesis_count }}</td>
          <td><button @click="selectStudent(row)">选择</button></td>
        </tr>
      </tbody>
    </table>
    <PaginationBar v-model:current="page" v-model:pageSize="pageSize" :total="students.length" />
    <div v-if="!students.length" class="empty-box">暂无学生数据。</div>

    <h4 style="margin-top: 16px">新增学生账号</h4>
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
        学号
        <input v-model="createForm.student_no" />
      </label>
      <label>
        邮箱
        <input v-model="createForm.email" />
      </label>
      <button class="accent" @click="createStudent">创建账号</button>
    </div>

    <h4 style="margin-top: 16px">编辑与账号操作</h4>
    <div v-if="selectedStudent" class="detail-grid">
      <div><span>已选学生</span><b>{{ selectedStudent.name }} (#{{ selectedStudent.id }})</b></div>
      <div><span>当前状态</span><b>{{ selectedStudent.is_active ? "启用" : "停用" }}</b></div>
    </div>

    <div class="form-grid" style="margin-top: 8px">
      <label>
        姓名
        <input v-model="editForm.name" :disabled="!selectedStudent" />
      </label>
      <label>
        学号
        <input v-model="editForm.student_no" :disabled="!selectedStudent" />
      </label>
      <label>
        邮箱
        <input v-model="editForm.email" :disabled="!selectedStudent" />
      </label>
      <button :disabled="!selectedStudent" @click="updateStudent">保存学生信息</button>
    </div>

    <div class="form-grid" style="margin-top: 8px">
      <label>
        新密码
        <input v-model="resetPassword" type="password" :disabled="!selectedStudent" />
      </label>
      <div></div>
      <div></div>
      <button :disabled="!selectedStudent" @click="toggleActive">
        {{ selectedStudent?.is_active ? "停用账号" : "启用账号" }}
      </button>
      <button class="warn" :disabled="!selectedStudent" @click="resetStudentPassword">重置密码</button>
    </div>
  </section>
</template>
