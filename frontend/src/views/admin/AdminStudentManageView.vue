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
        <HelpTip text="这里用于管理学生账号。你可以通过关键词搜索、按状态筛选，或进行批量导入和导出操作。" />
      </div>
      <div class="header-actions">
        <button class="accent" @click="openCreateModal">
          <span class="icon">＋</span> 新增学生
        </button>
      </div>
    </div>

    <div class="toolbar">
      <div class="filter-group">
        <div class="search-input">
          <input v-model="keyword" placeholder="搜索姓名 / ID / 学号 / 用户名" @keyup.enter="loadStudents" />
        </div>
        <select v-model="activeFilter" class="status-select">
          <option value="ALL">全部状态</option>
          <option value="ACTIVE">仅启用</option>
          <option value="INACTIVE">仅停用</option>
        </select>
        <button class="ghost" :disabled="loading" @click="loadStudents">
          {{ loading ? "加载中..." : "应用筛选" }}
        </button>
      </div>
      
      <div class="tool-group">
        <button class="minimal" @click="downloadTemplate" :title="downloadingTemplate ? '下载中...' : '下载 Excel 模板'">
          <span class="icon">↓</span> 模板
        </button>
        <button class="minimal" @click="openImportModal">
          <span class="icon">↑</span> 导入
        </button>
        <button class="minimal" :disabled="loading" @click="loadStudents" title="刷新列表">
          <span class="icon">↻</span>
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      正在加载学生数据...
    </div>
    
    <table v-else-if="students.length" class="data-table">
      <thead>
        <tr>
          <th width="80">ID</th>
          <th>姓名 / 学号</th>
          <th>用户名</th>
          <th width="100">状态</th>
          <th width="80">论文数</th>
          <th width="240" class="text-right">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in pagedStudents" :key="row.id">
          <td class="text-muted">#{{ row.id }}</td>
          <td>
            <div class="student-info">
              <span class="name">{{ row.name }}</span>
              <span class="no">{{ row.student_no || "-" }}</span>
            </div>
          </td>
          <td><code>{{ row.username || "-" }}</code></td>
          <td>
            <span :class="['badge', row.is_active ? 'success' : 'neutral']">
              {{ row.is_active ? "启用中" : "已停用" }}
            </span>
          </td>
          <td class="text-center">
            <span class="count-tag">{{ row.thesis_count }}</span>
          </td>
          <td>
            <div class="table-actions j-end">
              <button class="action-btn" @click="openEditModal(row)">编辑</button>
              <button class="action-btn ghost" @click="openResetPasswordModal(row)">重置密码</button>
              <button :class="['action-btn', row.is_active ? 'warn' : 'accent-soft']" @click="openToggleModal(row)">
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

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.search-input {
  flex: 1;
  max-width: 360px;
}

.search-input input {
  height: 42px;
  border-radius: 12px;
  border: 1px solid var(--line);
  font-size: 14px;
  transition: all 0.2s;
}

.search-input input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}

.status-select {
  width: auto;
  height: 42px;
  border-radius: 12px;
  border: 1px solid var(--line);
  padding: 0 12px;
  font-size: 14px;
  background-color: white;
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.minimal {
  padding: 8px 14px;
  font-size: 13px;
  background: transparent;
  color: var(--muted);
  border: 1px solid transparent;
  border-radius: 10px;
}

.minimal:hover {
  background: #f1f5f9;
  color: var(--ink);
  transform: none;
}

.minimal .icon {
  font-size: 16px;
  margin-right: 4px;
}

.loading-state {
  padding: 60px;
  text-align: center;
  color: var(--muted);
  font-size: 15px;
}

.data-table {
  border: none;
  border-radius: 0;
  margin-top: 0;
}

.data-table thead {
  background: #f8fafc;
}

.data-table th {
  border: none;
  padding: 16px 12px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.08em;
}

.data-table td {
  border: none;
  border-bottom: 1px solid #f1f5f9;
  padding: 16px 12px;
  vertical-align: middle;
}

.data-table tr:hover {
  background: #f8fafc;
}

.student-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.student-info .name {
  font-weight: 600;
  color: var(--ink);
  font-size: 15px;
}

.student-info .no {
  font-size: 12px;
  color: var(--muted);
  font-family: ui-monospace, monospace;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.badge.success {
  background: #dcfce7;
  color: #15803d;
}

.badge.neutral {
  background: #f1f5f9;
  color: #64748b;
}

.count-tag {
  display: inline-block;
  padding: 2px 8px;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 6px;
  font-weight: 700;
  font-size: 13px;
}

.table-actions {
  display: flex;
  gap: 8px;
}

.j-end {
  justify-content: flex-end;
}

.action-btn {
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 8px;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid transparent;
}

.action-btn:hover {
  background: #e2e8f0;
  transform: translateY(-1px);
}

.action-btn.accent-soft {
  background: var(--accent-soft);
  color: var(--accent);
}

.action-btn.ghost {
  background: transparent;
  border: 1px solid var(--line);
}

.action-btn.warn {
  background: #fee2e2;
  color: #dc2626;
}

.action-btn.warn:hover {
  background: #fecaca;
}

.text-muted {
  color: var(--muted);
}

.text-center {
  text-align: center;
}

.text-right {
  text-align: right;
}

code {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  color: #1e293b;
}

@media (max-width: 1024px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-group {
    flex-wrap: wrap;
  }
  
  .search-input {
    max-width: none;
  }
}
</style>
