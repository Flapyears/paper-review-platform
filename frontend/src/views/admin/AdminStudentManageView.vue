<script setup>
import { computed, onMounted, ref } from "vue";
import BaseModal from "../../components/common/BaseModal.vue";
import ExcelImportModal from "../../components/common/ExcelImportModal.vue";
import HelpTip from "../../components/common/HelpTip.vue";
import PaginationBar from "../../components/common/PaginationBar.vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";
import { downloadProtectedFile } from "../../utils/download";

const students = ref([]);
const loading = ref(false);
const keyword = ref("");
const activeFilter = ref("ALL");
const page = ref(1);
const pageSize = ref(10);

const showCreateModal = ref(false);
const showEditModal = ref(false);
const showResetPasswordModal = ref(false);
const showToggleModal = ref(false);
const showImportModal = ref(false);

const selectedStudent = ref(null);
const downloadingTemplate = ref(false);
const uploadingExcel = ref(false);
const importResult = ref(null);

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

const resetPassword = ref("");

const pagedStudents = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return students.value.slice(start, start + pageSize.value);
});

const toggleActionLabel = computed(() => {
  if (!selectedStudent.value) return "停用";
  return selectedStudent.value.is_active ? "停用" : "启用";
});

function emptyCreateForm() {
  createForm.value = {
    username: "",
    password: "",
    name: "",
    student_no: "",
    email: "",
  };
}

function fillEditForm(row) {
  selectedStudent.value = row;
  editForm.value = {
    name: row.name || "",
    student_no: row.student_no || "",
    email: row.email || "",
  };
}

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
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}

function openCreateModal() {
  emptyCreateForm();
  showCreateModal.value = true;
}

function openEditModal(row) {
  fillEditForm(row);
  showEditModal.value = true;
}

function openResetPasswordModal(row) {
  selectedStudent.value = row;
  resetPassword.value = "";
  showResetPasswordModal.value = true;
}

function openToggleModal(row) {
  selectedStudent.value = row;
  showToggleModal.value = true;
}

function openImportModal() {
  importResult.value = null;
  showImportModal.value = true;
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
    showCreateModal.value = false;
    notifySuccess("学生账号已创建");
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
    showEditModal.value = false;
    notifySuccess("学生信息已保存");
    await loadStudents();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function resetStudentPassword() {
  try {
    if (!selectedStudent.value) throw new Error("请先选择学生");
    if (!resetPassword.value.trim()) throw new Error("请输入新密码");
    await requestJson(`/api/admin/students/${selectedStudent.value.id}/reset-password`, "POST", {
      password: resetPassword.value.trim(),
    });
    showResetPasswordModal.value = false;
    resetPassword.value = "";
    notifySuccess("密码已重置");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function toggleStudentActive() {
  try {
    if (!selectedStudent.value) throw new Error("请先选择学生");
    await requestJson(`/api/admin/students/${selectedStudent.value.id}/toggle-active`, "POST", {});
    showToggleModal.value = false;
    notifySuccess(`账号已${selectedStudent.value.is_active ? "停用" : "启用"}`);
    await loadStudents();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function downloadTemplate() {
  downloadingTemplate.value = true;
  try {
    await downloadProtectedFile("/api/admin/students/import-template", "student-import-template.xlsx");
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    downloadingTemplate.value = false;
  }
}

async function importExcel(payload) {
  uploadingExcel.value = true;
  try {
    const form = new FormData();
    form.append("file", payload.file);
    if (payload.defaultPassword) {
      form.append("default_password", payload.defaultPassword);
    }
    const resp = await request("/api/admin/students/import-excel", {
      method: "POST",
      body: form,
    });
    importResult.value = resp.data || null;
    notifySuccess("导入已完成");
    await loadStudents();
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    uploadingExcel.value = false;
  }
}

onMounted(loadStudents);
</script>

<template>
  <section class="panel-card">
    <div class="page-header">
      <div class="title-inline">
        <h4>学生管理</h4>
        <HelpTip text="这里用于新增学生、修改资料、重置密码和批量导入账号。" />
      </div>
      <div class="action-bar">
        <button class="ghost" :disabled="loading" @click="loadStudents">
          {{ loading ? "刷新中..." : "刷新" }}
        </button>
        <button class="ghost" @click="downloadTemplate">下载模板</button>
        <button class="accent" @click="openImportModal">导入 Excel</button>
        <button class="accent" @click="openCreateModal">新增学生</button>
      </div>
    </div>

    <div class="form-grid">
      <label>
        关键词
        <div class="title-inline">
          <input v-model="keyword" placeholder="姓名 / ID / 学号 / 用户名" />
          <HelpTip text="支持按姓名、学号、账号 ID、用户名筛选。" />
        </div>
      </label>
      <label>
        账号状态
        <div class="title-inline">
          <select v-model="activeFilter">
            <option value="ALL">全部</option>
            <option value="ACTIVE">仅启用</option>
            <option value="INACTIVE">仅停用</option>
          </select>
          <HelpTip text="停用后账号无法登录，但学生历史数据仍会保留。" />
        </div>
      </label>
      <div></div>
      <button class="accent" :disabled="loading" @click="loadStudents">
        {{ loading ? "加载中..." : "应用筛选" }}
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
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in pagedStudents" :key="row.id">
          <td>#{{ row.id }}</td>
          <td>{{ row.name }}</td>
          <td>{{ row.student_no || "-" }}</td>
          <td>{{ row.username || "-" }}</td>
          <td>{{ row.is_active ? "启用" : "停用" }}</td>
          <td>{{ row.thesis_count }}</td>
          <td>
            <div class="table-actions">
              <button @click="openEditModal(row)">编辑</button>
              <button class="ghost" @click="openResetPasswordModal(row)">重置密码</button>
              <button class="warn" @click="openToggleModal(row)">
                {{ row.is_active ? "停用" : "启用" }}
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <PaginationBar v-model:current="page" v-model:pageSize="pageSize" :total="students.length" />
    <div v-if="!students.length" class="empty-box">当前没有符合条件的学生。</div>

    <BaseModal v-model="showCreateModal" title="新增学生">
      <div class="modal-stack">
        <div class="title-inline">
          <strong>基础信息</strong>
          <HelpTip text="创建后可以继续维护学号、邮箱，也可以单独重置密码。" />
        </div>
        <div class="form-grid">
          <label>
            用户名
            <input v-model="createForm.username" placeholder="至少 3 个字符" />
          </label>
          <label>
            初始密码
            <input v-model="createForm.password" type="password" placeholder="至少 6 个字符" />
          </label>
          <label>
            姓名
            <input v-model="createForm.name" placeholder="请输入姓名" />
          </label>
          <label>
            学号
            <input v-model="createForm.student_no" placeholder="建议唯一" />
          </label>
          <label>
            邮箱
            <input v-model="createForm.email" placeholder="可选" />
          </label>
        </div>
      </div>
      <template #footer>
        <button class="ghost" @click="showCreateModal = false">取消</button>
        <button class="accent" @click="createStudent">创建</button>
      </template>
    </BaseModal>

    <BaseModal v-model="showEditModal" title="编辑学生">
      <div class="modal-stack">
        <div v-if="selectedStudent" class="detail-grid">
          <div><span>当前学生</span><b>{{ selectedStudent.name }} (#{{ selectedStudent.id }})</b></div>
          <div><span>用户名</span><b>{{ selectedStudent.username || "-" }}</b></div>
        </div>
        <div class="form-grid">
          <label>
            姓名
            <input v-model="editForm.name" placeholder="请输入姓名" />
          </label>
          <label>
            学号
            <input v-model="editForm.student_no" placeholder="建议唯一" />
          </label>
          <label>
            邮箱
            <input v-model="editForm.email" placeholder="可选" />
          </label>
        </div>
      </div>
      <template #footer>
        <button class="ghost" @click="showEditModal = false">取消</button>
        <button class="accent" @click="updateStudent">保存</button>
      </template>
    </BaseModal>

    <BaseModal v-model="showResetPasswordModal" title="重置密码" width="520px">
      <div class="modal-stack">
        <p v-if="selectedStudent" class="muted">为 {{ selectedStudent.name }} 设置新密码。</p>
        <label>
          新密码
          <input v-model="resetPassword" type="password" placeholder="至少 6 个字符" />
        </label>
      </div>
      <template #footer>
        <button class="ghost" @click="showResetPasswordModal = false">取消</button>
        <button class="warn" @click="resetStudentPassword">确认重置</button>
      </template>
    </BaseModal>

    <BaseModal v-model="showToggleModal" :title="`${toggleActionLabel}账号`" width="520px">
      <div class="modal-stack">
        <p v-if="selectedStudent">
          确认要{{ toggleActionLabel }} {{ selectedStudent.name }}（{{ selectedStudent.username }}）吗？
        </p>
      </div>
      <template #footer>
        <button class="ghost" @click="showToggleModal = false">取消</button>
        <button class="warn" @click="toggleStudentActive">确认</button>
      </template>
    </BaseModal>

    <ExcelImportModal
      v-model="showImportModal"
      title="导入学生"
      :fields="['姓名', '用户名', '学号', '邮箱']"
      :tip="'先下载模板，再按列填写。可以手动指定本次导入的初始密码；留空时默认使用 student123。'"
      :uploading="uploadingExcel"
      :downloading="downloadingTemplate"
      :result="importResult"
      @download-template="downloadTemplate"
      @upload-file="importExcel"
    />
  </section>
</template>
