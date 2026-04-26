<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { request, requestJson } from "../../services/api";
import { authHeaders } from "../../stores/auth";
import { notifyError, notifySuccess } from "../../stores/notice";

const route = useRoute();
const router = useRouter();

// 资源状态
const taskId = ref("");
const detail = ref(null);
const fileBlobUrl = ref("");
const loadingData = ref(false);
const loadingFile = ref(false);

// 表单状态
const score = ref("");
const grade = ref("A");
const allowDefense = ref("YES");
const comments = ref("");
const internalComments = ref("");

// 快捷列表状态
const quickTasks = ref([]);
const loadingQuickTasks = ref(false);

const gradeOptions = ["A", "B", "C", "D"];
const canOperate = computed(() => Number(taskId.value) > 0 && !loadingData.value);
const currentTaskIdNum = computed(() => Number(taskId.value) || 0);

// 表单回填与重置
function resetFormToDefault() {
  score.value = "";
  grade.value = "A";
  allowDefense.value = "YES";
  comments.value = "";
  internalComments.value = "";
}

function fillFormFromResponse(form) {
  if (!form) {
    resetFormToDefault();
    return;
  }
  score.value = form.score == null ? "" : String(form.score);
  grade.value = form.grade || "A";
  allowDefense.value = form.allow_defense || "YES";
  comments.value = form.comments || "";
  internalComments.value = form.internal_comments || "";
}

function revokeFileBlobUrl() {
  if (fileBlobUrl.value) {
    URL.revokeObjectURL(fileBlobUrl.value);
    fileBlobUrl.value = "";
  }
}

// 获取快速任务列表
async function loadQuickTasks(showToast = false) {
  loadingQuickTasks.value = true;
  try {
    const resp = await request("/api/reviewer/tasks");
    quickTasks.value = resp.items || [];
    if (showToast) {
      notifySuccess("任务快捷列表已刷新");
    }
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loadingQuickTasks.value = false;
  }
}

// 加载任务详情
async function loadTaskDetailById(id, showToast = true) {
  if (!id || id <= 0) return;
  loadingData.value = true;
  try {
    const resp = await request(`/api/reviewer/tasks/${id}`);
    detail.value = resp;
    fillFormFromResponse(resp.form);
    if (showToast) {
      notifySuccess("任务详情已从服务器加载");
    }
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loadingData.value = false;
  }
}

// 在线通过 Blob 加载文件并创建 ObjectURL
async function fetchOnlineDocument(id) {
  if (!id || id <= 0) return;
  loadingFile.value = true;
  revokeFileBlobUrl(); // 取消可能存在的老对象URL
  try {
    const response = await fetch(`/api/reviewer/tasks/${id}/download`, {
      method: "GET",
      headers: authHeaders(),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const blob = await response.blob();
    fileBlobUrl.value = URL.createObjectURL(blob);
  } catch (err) {
    notifyError("无法加载文档预览：" + (err.message || String(err)));
  } finally {
    loadingFile.value = false;
  }
}

function switchTask(id) {
  if (!id) return;
  router.push({ path: "/reviewer/workspace", query: { taskId: String(id) } });
}

async function saveDraft() {
  if (!canOperate.value) {
    notifyError("未选择有效任务，无法保存");
    return;
  }
  try {
    const payload = {
      score: score.value === "" ? null : Number(score.value),
      grade: grade.value || null,
      allow_defense: allowDefense.value || null,
      comments: comments.value || null,
      internal_comments: internalComments.value || null,
    };
    await requestJson(`/api/reviewer/tasks/${currentTaskIdNum.value}/form`, "PUT", payload);
    notifySuccess("评阅草稿已保存");
    await loadTaskDetailById(currentTaskIdNum.value, false);
    await loadQuickTasks(false);
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function submitForm() {
  if (!canOperate.value) return;
  try {
    await request(`/api/reviewer/tasks/${currentTaskIdNum.value}/submit`, { method: "POST" });
    notifySuccess("评阅评审意见已提交");
    await loadTaskDetailById(currentTaskIdNum.value, false);
    await loadQuickTasks(false);
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function forceDownload() {
    if (!canOperate.value) return;
    try {
        const response = await fetch(`/api/reviewer/tasks/${currentTaskIdNum.value}/download`, {
        method: "GET",
        headers: authHeaders(),
        });
        if (!response.ok) {
        throw new Error(await response.text());
        }
        const blob = await response.blob();
        const contentDisposition = response.headers.get("content-disposition") || "";
        const matched = contentDisposition.match(/filename=\"?([^\"]+)\"?/i);
        const fileName = matched ? matched[1] : `task-${taskId.value}.bin`;

        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = fileName;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
        notifySuccess(`下载成功：${fileName}`);
    } catch (err) {
        notifyError(err.message || String(err));
    }
}

// 监听路由参数 taskId 变化
watch(
  () => route.query.taskId,
  async (queryTaskId) => {
    if (!queryTaskId) {
      taskId.value = "";
      detail.value = null;
      revokeFileBlobUrl();
      resetFormToDefault();
      await loadQuickTasks(false);
      return;
    }
    const targetId = Number(queryTaskId);
    if (currentTaskIdNum.value !== targetId) {
       taskId.value = String(queryTaskId);
       await Promise.all([
           loadTaskDetailById(targetId, false),
           fetchOnlineDocument(targetId),
           loadQuickTasks(false)
       ]);
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  revokeFileBlobUrl();
});
</script>

<template>
  <div class="workspace-layout">
    <!-- Left Panel: Document Viewer -->
    <div class="viewer-panel">
      <div v-if="loadingFile" class="viewer-overlay">
         <div class="loader-spinner"></div>
         <p>正在努力加载论文预览...</p>
      </div>
      <iframe
        v-else-if="fileBlobUrl"
        :src="fileBlobUrl"
        class="viewer-frame"
        title="PDF Preview"
      ></iframe>
      <div v-else class="viewer-empty">
         <p>无文档显示，请从右侧侧栏切换任务。</p>
      </div>
    </div>

    <!-- Right Panel: Task Sidebar & Review Form -->
    <div class="sidebar-panel">
        <header class="sidebar-header">
            <h4>在线审阅与评阅意见</h4>
            <div class="task-selector">
                <select :value="taskId" @change="e => switchTask(e.target.value)">
                    <option value="" disabled>-- 快速切换任务 --</option>
                    <option v-for="t in quickTasks" :key="t.task_id" :value="String(t.task_id)">
                        ID: {{ t.task_id }} | {{ t.thesis_title || '无标题' }} ({{ t.status }})
                    </option>
                </select>
            </div>
        </header>
        
        <div class="sidebar-content">
            <template v-if="detail?.task">
                <div class="task-info-card">
                   <div class="ti-row"><span>论文:</span> <strong>{{ detail.task.thesis_title || "-" }}</strong></div>
                   <div class="ti-row"><span>版本:</span> <strong>{{ detail.task.version_no ? `V${detail.task.version_no}` : "-" }}</strong></div>
                   <div class="ti-row"><span>状态:</span> <strong class="badge">{{ detail.task.status }}</strong></div>
                   <div v-if="detail.task.return_reason" class="ti-row ti-warn">
                       <span>退回原因:</span> <strong>{{ detail.task.return_reason }}</strong>
                   </div>
                   <div class="ti-actions">
                       <button class="ghost small" @click="forceDownload">强制下载离线阅读</button>
                   </div>
                </div>

                <div class="form-wrapper">
                    <label class="form-item">
                        <span>分数 (0-100)</span>
                        <input v-model="score" type="number" min="0" max="100" />
                    </label>
                    <div class="row-flex">
                        <label class="form-item half">
                            <span>评级</span>
                            <select v-model="grade">
                                <option v-for="item in gradeOptions" :key="item" :value="item">{{ item }}</option>
                            </select>
                        </label>
                        <label class="form-item half">
                            <span>同意答辩</span>
                            <select v-model="allowDefense">
                                <option value="YES">YES</option>
                                <option value="NO">NO</option>
                                <option value="REVISE">REVISE</option>
                            </select>
                        </label>
                    </div>
                    <label class="form-item">
                        <span>给学生评语</span>
                        <textarea v-model="comments" rows="5" placeholder="请填写详细评阅意见..."></textarea>
                    </label>
                    <label class="form-item">
                        <span>内部备注（可选）</span>
                        <textarea v-model="internalComments" rows="3" placeholder="仅供审批人/管理员参考"></textarea>
                    </label>

                    <div class="form-actions">
                        <button :disabled="loadingData" @click="saveDraft">保存草稿</button>
                        <button class="warn" :disabled="loadingData" @click="submitForm">提交评审</button>
                    </div>
                </div>
            </template>
            <template v-else>
                 <div class="empty-state">
                     <p>未选择有效任务，暂无评阅表单显示。</p>
                 </div>
            </template>
        </div>
    </div>
  </div>
</template>

<style scoped>
/* 全屏工作台布局：使用 flex 均分 */
.workspace-layout {
  display: flex;
  height: calc(100vh - 64px); /* 减去顶部导航高度，如果是 default MainLayout.vue 可能是 64px 左右 */
  width: 100%;
  background-color: #e5e7eb;
  overflow: hidden;
  margin: -24px; /* 补偿 MainLayout 的 padding，让其尽可能沉浸。可以根据情况微调 */
  padding: 0;
}

/* 左侧预览区：占据主视觉 */
.viewer-panel {
  flex: 1 1 auto;
  position: relative;
  min-width: 0;
  display: flex;
  align-items: stretch;
  background-color: #525659; /* PDF Viewer 同色背景色 */
}

.viewer-frame {
  width: 100%;
  height: 100%;
  border: none;
}

.viewer-overlay, .viewer-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #f3f4f6;
  font-size: 15px;
}

.loader-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 右侧侧边栏：评审区 */
.sidebar-panel {
  flex: 0 0 380px;
  background: white;
  border-left: 1px solid #d1d5db;
  display: flex;
  flex-direction: column;
  box-shadow: -2px 0 10px rgba(0,0,0,0.05);
  z-index: 10;
}

.sidebar-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  background-color: #f9fafb;
}

.sidebar-header h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #111827;
}

.task-selector select {
  width: 100%;
  padding: 8px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  font-size: 14px;
}

.sidebar-content {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 20px;
}

.task-info-card {
  background: #eff6ff;
  border-radius: 8px;
  padding: 14px;
  font-size: 13px;
  color: #1e3a8a;
  margin-bottom: 20px;
}

.ti-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.ti-row:last-child {
  margin-bottom: 0;
}

.ti-warn {
  color: #991b1b;
  background: #fef2f2;
  padding: 6px;
  border-radius: 4px;
}

.ti-actions {
  margin-top: 10px;
  border-top: 1px solid rgba(0,0,0,0.1);
  padding-top: 10px;
}

.badge {
  background: #dbeafe;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.form-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.row-flex {
  display: flex;
  gap: 12px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.form-item.half {
  flex: 1;
}

.form-item input,
.form-item select,
.form-item textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  transition: border-color 0.2s;
}

.form-item input:focus,
.form-item select:focus,
.form-item textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 10px;
}

.form-actions button {
  flex: 1;
}

.empty-state {
  color: #6b7280;
  text-align: center;
  padding: 30px 0;
  font-size: 14px;
}

@media (max-width: 900px) {
  .workspace-layout {
    flex-direction: column;
    margin: 0;
    height: auto;
  }
  .viewer-panel {
    height: 45vh;
    flex: none;
  }
  .sidebar-panel {
    flex: none;
    border-left: none;
    border-top: 2px solid #e5e7eb;
    width: 100%;
  }
}
</style>
