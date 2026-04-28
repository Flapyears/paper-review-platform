<script setup>
import { computed, onMounted, ref } from "vue";
import BaseModal from "../../components/common/BaseModal.vue";
import ExcelImportModal from "../../components/common/ExcelImportModal.vue";
import HelpTip from "../../components/common/HelpTip.vue";
import PaginationBar from "../../components/common/PaginationBar.vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";
import { downloadProtectedFile } from "../../utils/download";

const reviewers = ref([]);
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

const selectedReviewer = ref(null);
const downloadingTemplate = ref(false);
const uploadingExcel = ref(false);
const importResult = ref(null);

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

const resetPassword = ref("");

const pagedReviewers = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return reviewers.value.slice(start, start + pageSize.value);
});

const toggleActionLabel = computed(() => {
  if (!selectedReviewer.value) return "停用";
  return selectedReviewer.value.is_active ? "停用" : "启用";
});

function emptyCreateForm() {
  createForm.value = {
    username: "",
    password: "",
    name: "",
    email: "",
    department: "",
  };
}

function fillEditForm(row) {
  selectedReviewer.value = row;
  editForm.value = {
    name: row.name || "",
    email: row.email || "",
    department: row.department === "未设置科室" ? "" : row.department || "",
  };
}

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
  selectedReviewer.value = row;
  resetPassword.value = "";
  showResetPasswordModal.value = true;
}

function openToggleModal(row) {
  selectedReviewer.value = row;
  showToggleModal.value = true;
}

function openImportModal() {
  importResult.value = null;
  showImportModal.value = true;
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
    showCreateModal.value = false;
    notifySuccess("教师账号已创建");
    await loadReviewers();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function updateReviewer() {
  try {
    if (!selectedReviewer.value) throw new Error("请先选择教师");
    await requestJson(`/api/admin/reviewers/${selectedReviewer.value.id}`, "PATCH", {
      name: editForm.value.name.trim(),
      email: editForm.value.email.trim() || null,
      department: editForm.value.department.trim() || null,
    });
    showEditModal.value = false;
    notifySuccess("教师信息已保存");
    await loadReviewers();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function resetReviewerPassword() {
  try {
    if (!selectedReviewer.value) throw new Error("请先选择教师");
    if (!resetPassword.value.trim()) throw new Error("请输入新密码");
    await requestJson(`/api/admin/reviewers/${selectedReviewer.value.id}/reset-password`, "POST", {
      password: resetPassword.value.trim(),
    });
    showResetPasswordModal.value = false;
    resetPassword.value = "";
    notifySuccess("密码已重置");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function toggleReviewerActive() {
  try {
    if (!selectedReviewer.value) throw new Error("请先选择教师");
    await requestJson(`/api/admin/reviewers/${selectedReviewer.value.id}/toggle-active`, "POST", {});
    showToggleModal.value = false;
    notifySuccess(`账号已${selectedReviewer.value.is_active ? "停用" : "启用"}`);
    await loadReviewers();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function downloadTemplate() {
  downloadingTemplate.value = true;
  try {
    await downloadProtectedFile("/api/admin/reviewers/import-template", "reviewer-import-template.xlsx");
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
    const resp = await request("/api/admin/reviewers/import-excel", {
      method: "POST",
      body: form,
    });
    importResult.value = resp.data || null;
    notifySuccess("导入已完成");
    await loadReviewers();
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    uploadingExcel.value = false;
  }
}

onMounted(loadReviewers);
</script>

<template>
  <section class="panel-card">
    <div class="page-header">
      <div class="title-inline">
        <h4>教师管理</h4>
        <HelpTip text="这里用于新增教师、修改资料、重置密码和批量导入账号。" />
      </div>
      <div class="action-bar">
        <button class="ghost" :disabled="loading" @click="loadReviewers">
          {{ loading ? "刷新中..." : "刷新" }}
        </button>
        <button class="ghost" @click="downloadTemplate">下载模板</button>
        <button class="accent" @click="openImportModal">导入 Excel</button>
        <button class="accent" @click="openCreateModal">新增教师</button>
      </div>
    </div>

    <div class="form-grid">
      <label>
        关键词
        <div class="title-inline">
          <input v-model="keyword" placeholder="姓名 / ID / 用户名" />
          <HelpTip text="支持按教师姓名、账号 ID、用户名筛选。" />
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
          <HelpTip text="停用后账号无法登录，但数据仍会保留。" />
        </div>
      </label>
      <div></div>
      <button class="accent" :disabled="loading" @click="loadReviewers">
        {{ loading ? "加载中..." : "应用筛选" }}
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
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in pagedReviewers" :key="row.id">
          <td>#{{ row.id }}</td>
          <td>{{ row.name }}</td>
          <td>{{ row.username || "-" }}</td>
          <td>{{ row.department || "-" }}</td>
          <td>{{ row.is_active ? "启用" : "停用" }}</td>
          <td>{{ row.active_task_count }}</td>
          <td>{{ row.submitted_task_count }}</td>
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

    <PaginationBar v-model:current="page" v-model:pageSize="pageSize" :total="reviewers.length" />
    <div v-if="!reviewers.length" class="empty-box">当前没有符合条件的教师。</div>

    <BaseModal v-model="showCreateModal" title="新增教师">
      <div class="modal-stack">
        <div class="title-inline">
          <strong>基础信息</strong>
          <HelpTip text="创建后可以随时编辑资料或重置密码。" />
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
            邮箱
            <input v-model="createForm.email" placeholder="可选" />
          </label>
          <label>
            科室
            <input v-model="createForm.department" placeholder="如：计算机系" />
          </label>
        </div>
      </div>
      <template #footer>
        <button class="ghost" @click="showCreateModal = false">取消</button>
        <button class="accent" @click="createReviewer">创建</button>
      </template>
    </BaseModal>

    <BaseModal v-model="showEditModal" title="编辑教师">
      <div class="modal-stack">
        <div v-if="selectedReviewer" class="detail-grid">
          <div><span>当前教师</span><b>{{ selectedReviewer.name }} (#{{ selectedReviewer.id }})</b></div>
          <div><span>用户名</span><b>{{ selectedReviewer.username || "-" }}</b></div>
        </div>
        <div class="form-grid">
          <label>
            姓名
            <input v-model="editForm.name" placeholder="请输入姓名" />
          </label>
          <label>
            邮箱
            <input v-model="editForm.email" placeholder="可选" />
          </label>
          <label>
            科室
            <input v-model="editForm.department" placeholder="可选" />
          </label>
        </div>
      </div>
      <template #footer>
        <button class="ghost" @click="showEditModal = false">取消</button>
        <button class="accent" @click="updateReviewer">保存</button>
      </template>
    </BaseModal>

    <BaseModal v-model="showResetPasswordModal" title="重置密码" width="520px">
      <div class="modal-stack">
        <p v-if="selectedReviewer" class="muted">为 {{ selectedReviewer.name }} 设置新密码。</p>
        <label>
          新密码
          <input v-model="resetPassword" type="password" placeholder="至少 6 个字符" />
        </label>
      </div>
      <template #footer>
        <button class="ghost" @click="showResetPasswordModal = false">取消</button>
        <button class="warn" @click="resetReviewerPassword">确认重置</button>
      </template>
    </BaseModal>

    <BaseModal v-model="showToggleModal" :title="`${toggleActionLabel}账号`" width="520px">
      <div class="modal-stack">
        <p v-if="selectedReviewer">
          确认要{{ toggleActionLabel }} {{ selectedReviewer.name }}（{{ selectedReviewer.username }}）吗？
        </p>
      </div>
      <template #footer>
        <button class="ghost" @click="showToggleModal = false">取消</button>
        <button class="warn" @click="toggleReviewerActive">确认</button>
      </template>
    </BaseModal>

    <ExcelImportModal
      v-model="showImportModal"
      title="导入教师"
      :fields="['姓名', '用户名', '邮箱', '科室']"
      :tip="'先下载模板，再按列填写。可以手动指定本次导入的初始密码；留空时默认使用 reviewer123。'"
      :uploading="uploadingExcel"
      :downloading="downloadingTemplate"
      :result="importResult"
      @download-template="downloadTemplate"
      @upload-file="importExcel"
    />
  </section>
</template>
