<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { request } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const thesisId = ref("");
const fileRef = ref(null);
const current = ref(null);

function statusLabel(status) {
  if (status === "DRAFT") return "草稿中";
  if (status === "SUBMITTED") return "已提交待分配";
  if (status === "REVIEWING") return "评阅中";
  if (status === "REVIEW_DONE") return "评阅完成";
  return status || "-";
}

const submitCards = computed(() => {
  if (!current.value) {
    return [
      { label: "论文编号", value: "未创建", tone: "neutral" },
      { label: "论文状态", value: "待处理", tone: "neutral" },
      { label: "当前版本号", value: "-", tone: "neutral" },
      { label: "送审结果", value: "未提交", tone: "neutral" },
    ];
  }

  return [
    { label: "论文编号", value: current.value.id, tone: "primary" },
    { label: "论文状态", value: statusLabel(current.value.status), tone: "accent" },
    {
      label: "当前版本号",
      value: current.value.current_version_no ? `V${current.value.current_version_no}` : "-",
      tone: "neutral",
    },
    {
      label: "送审结果",
      value: current.value.status === "SUBMITTED" || current.value.status === "REVIEWING" || current.value.status === "REVIEW_DONE"
        ? "已提交"
        : "未提交",
      tone: "neutral",
    },
  ];
});

const submitFacts = computed(() => {
  if (!current.value) return [];
  return [
    { label: "论文编号", value: current.value.id },
    { label: "论文状态", value: statusLabel(current.value.status) },
    {
      label: "当前版本号",
      value: current.value.current_version_no ? `V${current.value.current_version_no}` : "-",
    },
    { label: "退回原因", value: current.value.return_reason || "-" },
  ];
});

function onFileChange(event) {
  fileRef.value = event.target.files?.[0] ?? null;
}

async function uploadFinal() {
  try {
    if (!fileRef.value) {
      // 如果没选文件，点击按钮触发文件选择
      if (current.value?.status === 'DRAFT') {
        const input = document.querySelector('input[type="file"]');
        if (input) input.click();
      }
      return;
    }
    const form = new FormData();
    form.append("file", fileRef.value);
    const data = await request(`/api/thesis/${Number(thesisId.value)}/upload-final`, {
      method: "POST",
      body: form,
    });
    notifySuccess(`终稿上传成功，版本号: V${data?.data?.version_no || "-"}`);
    fileRef.value = null; // 上传成功后清空本地引用
    await loadCurrent();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function submitFinal() {
  try {
    const data = await request(`/api/thesis/${Number(thesisId.value)}/submit-final`, {
      method: "POST",
    });
    const nextStatus = data?.data?.thesis_status || "SUBMITTED";
    notifySuccess(
      `送审已提交，当前状态：${statusLabel(nextStatus)}，版本 V${data?.data?.version_no || "-"}`
    );
    await loadCurrent();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function loadCurrent() {
  try {
    const data = await request("/api/thesis/my");
    current.value = data.thesis;
    if (current.value?.id) thesisId.value = String(current.value.id);
    if (!current.value) thesisId.value = "";
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

onMounted(loadCurrent);
</script>

<template>
  <section class="overview-page">
    <div class="panel-card page-hero">
      <div class="page-hero-main">
        <div>
          <p class="section-kicker">上传与送审</p>
          <h4>终稿上传与送审提交</h4>
          <p class="muted">上传终稿后即可提交送审。</p>
        </div>
        <div class="header-actions">
          <button class="tool-btn" @click="loadCurrent" title="刷新状态">
            <span class="icon">↻</span>
          </button>
          <button class="primary-btn secondary" @click="uploadFinal" :disabled="!current || current.status !== 'DRAFT'">
            <span class="icon">↑</span> {{ fileRef ? '确认上传' : '上传终稿' }}
          </button>
          <button class="primary-btn danger" @click="submitFinal" :disabled="!current || current.status !== 'DRAFT' || !current.current_version_no">
            <span class="icon">🚀</span> 提交送审
          </button>
        </div>
      </div>

      <div class="overview-metrics">
        <article
          v-for="card in submitCards"
          :key="card.label"
          class="metric-card"
          :class="card.tone"
        >
          <span>{{ card.label }}</span>
          <b>{{ card.value }}</b>
        </article>
      </div>
    </div>

    <div class="overview-main">
      <section class="panel-card content-card">
        <div class="section-head">
          <div>
            <h4>终稿办理</h4>
            <p class="muted">确认文件无误后再提交。</p>
          </div>
          <span class="status-chip" :class="{ empty: !current }">
            {{ current ? statusLabel(current.status) : "暂无论文" }}
          </span>
        </div>

        <div class="upload-section">
          <div class="thesis-meta-bar">
            <div class="meta-item">
              <span class="meta-label">论文 ID</span>
              <code class="meta-value">#{{ thesisId || '-' }}</code>
            </div>
            <div class="meta-item" v-if="current">
              <span class="meta-label">当前版本</span>
              <span class="meta-value">V{{ current.current_version_no || '0' }}</span>
            </div>
          </div>

          <div class="file-uploader-wrap">
            <span class="field-label">终稿文件上传 (支持 PDF / DOCX)</span>
            <div class="file-uploader" :class="{ has_file: fileRef, disabled: current?.status !== 'DRAFT' }" @click="current?.status === 'DRAFT' && $refs.fileInput.click()">
              <input type="file" ref="fileInput" accept=".pdf,.docx" hidden @change="onFileChange" :disabled="current?.status !== 'DRAFT'" />
              <div v-if="!fileRef" class="upload-placeholder">
                <span class="upload-icon">📄</span>
                <div class="upload-text">
                  <strong v-if="current?.status === 'DRAFT'">点击此处或拖拽文件上传</strong>
                  <strong v-else>当前状态不可上传</strong>
                  <span v-if="current?.status === 'DRAFT'">建议文件大小不超过 50MB</span>
                  <span v-else>论文已提交或在评阅中，如需修改请联系管理员退回</span>
                </div>
              </div>
              <div v-else class="file-preview">
                <span class="file-icon">✅</span>
                <div class="file-info">
                  <span class="file-name">{{ fileRef.name }}</span>
                  <span class="file-size">{{ (fileRef.size / 1024).toFixed(1) }} KB</span>
                </div>
                <button class="remove-file" @click.stop="fileRef = null">更换文件</button>
              </div>
            </div>
          </div>
          
          <div class="upload-action-bar" v-if="fileRef && current?.status === 'DRAFT'">
             <button class="accent-btn" @click="uploadFinal">立即同步终稿文件</button>
             <p class="muted-tip">同步后将自动创建新版本，您可以在下方列表中查看详情。</p>
          </div>
        </div>

        <div v-if="current" class="detail-grid overview-detail-grid">
          <div v-for="item in submitFacts" :key="item.label">
            <span>{{ item.label }}</span>
            <b>{{ item.value }}</b>
          </div>
        </div>

        <div v-else class="empty-box">
          <p>当前尚未建立论文信息，请先前往论文信息页面创建论文。</p>
          <div class="quick-links">
            <RouterLink class="entry-link" to="/student/thesis">前往论文信息</RouterLink>
          </div>
        </div>
      </section>

      <aside class="overview-side">
        <section class="panel-card content-card side-card">
          <div class="section-head">
          <div>
            <h4>提交提醒</h4>
            <p class="muted">确认无误后再提交，避免重复修改。</p>
          </div>
          </div>

          <div class="state-note" :class="{ warning: !current }">
            <strong>{{ current ? "可继续办理送审" : "请先建立论文信息" }}</strong>
            <p>
              {{
                current
                  ? "提交后会按当前版本进入评审。如被退回，按提示修改后重新上传即可。"
                  : "请先填写论文标题并选择指导教师，建立论文信息后再上传终稿。"
              }}
            </p>
          </div>
        </section>

        <section class="panel-card content-card side-card">
          <div class="section-head">
          <div>
            <h4>常用入口</h4>
            <p class="muted">需要补充信息时，可以直接从这里进入。</p>
          </div>
          </div>

          <div class="quick-action-list">
            <RouterLink class="action-tile primary" to="/student/overview">
              <strong>论文总览</strong>
              <span>查看论文状态、进度和版本信息</span>
            </RouterLink>
            <RouterLink class="action-tile" to="/student/thesis">
              <strong>论文信息</strong>
              <span>维护论文标题和指导教师信息</span>
            </RouterLink>
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.overview-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-hero {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  padding: 32px;
}

.page-hero-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
}

.section-kicker {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent);
  margin-bottom: 8px;
}

.page-hero-main h4 {
  font-size: 24px;
  margin: 0 0 8px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.primary-btn {
  height: 48px;
  padding: 0 24px;
  background: var(--accent);
  color: white;
  border-radius: 14px;
  font-weight: 700;
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: none;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(30, 58, 138, 0.2);
}

.primary-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
}

.primary-btn.secondary {
  background: white;
  color: var(--accent);
  border: 1px solid var(--accent);
  box-shadow: none;
}

.primary-btn.secondary:hover:not(:disabled) {
  background: var(--accent-soft);
}

.primary-btn.danger {
  background: #f43f5e;
  box-shadow: 0 4px 12px rgba(244, 63, 94, 0.2);
}

.primary-btn.danger:hover:not(:disabled) {
  background: #e11d48;
  box-shadow: 0 8px 20px rgba(244, 63, 94, 0.3);
}

.tool-btn {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  background: white;
  border: 1px solid var(--line);
  color: var(--muted);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.tool-btn:hover {
  background: #f1f5f9;
  color: var(--ink);
}

.icon {
  font-size: 20px;
}

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.metric-card {
  padding: 20px;
  border-radius: 18px;
  background: white;
  border: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-card span {
  font-size: 13px;
  color: var(--muted);
  font-weight: 600;
}

.metric-card b {
  font-size: 20px;
  color: var(--ink);
}

.metric-card.primary { border-left: 4px solid var(--accent); }
.metric-card.accent { border-left: 4px solid #10b981; }

.overview-main {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.status-chip {
  padding: 6px 14px;
  border-radius: 999px;
  background: #dcfce7;
  color: #15803d;
  font-size: 12px;
  font-weight: 700;
}

.status-chip.empty {
  background: #f1f5f9;
  color: #64748b;
}

.upload-section {
  padding: 10px 0;
}

.thesis-meta-bar {
  display: flex;
  gap: 32px;
  margin-bottom: 24px;
  padding: 12px 20px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid var(--line);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta-label {
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
}

.meta-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  background: white;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid var(--line);
}

code.meta-value {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--accent);
}

.file-uploader-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.file-uploader {
  min-height: 180px;
  border: 2px dashed #cbd5e1;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  background: #fbfcfd;
}

.file-uploader:hover:not(.disabled) {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.file-uploader.disabled {
  cursor: not-allowed;
  background: #f8fafc;
  border-color: #e2e8f0;
}

.file-uploader.disabled .upload-icon {
  filter: grayscale(1) opacity(0.3);
}

.file-uploader.has_file {
  border-style: solid;
  border-color: #10b981;
  background: #f0fdf4;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}

.upload-icon {
  font-size: 42px;
  filter: grayscale(1) opacity(0.5);
}

.upload-text strong {
  display: block;
  font-size: 15px;
  color: var(--ink);
  margin-bottom: 4px;
}

.upload-text span {
  font-size: 12px;
  color: var(--muted);
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  width: 100%;
}

.file-icon {
  font-size: 32px;
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-weight: 700;
  color: var(--ink);
  word-break: break-all;
}

.file-size {
  font-size: 12px;
  color: var(--muted);
}

.remove-file {
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: white;
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.remove-file:hover {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fecaca;
}

.upload-action-bar {
  margin-top: 24px;
  padding: 16px;
  background: #f0fdf4;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.accent-btn {
  height: 40px;
  padding: 0 20px;
  background: #10b981;
  color: white;
  border-radius: 10px;
  border: none;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.muted-tip {
  margin: 0;
  font-size: 13px;
  color: #15803d;
}

.state-note {
  padding: 16px;
  border-radius: 14px;
  background: #f0f9ff;
  border-left: 4px solid #0ea5e9;
  margin-bottom: 20px;
}

.state-note.warning {
  background: #fffbeb;
  border-left-color: #f59e0b;
}

.action-tile {
  display: flex;
  flex-direction: column;
  padding: 18px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid var(--line);
  text-decoration: none;
  gap: 6px;
  transition: all 0.2s ease;
}

.action-tile:hover {
  background: white;
  border-color: var(--accent);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  transform: translateX(4px);
}

.action-tile.primary {
  background: var(--accent-soft);
}

@media (max-width: 1100px) {
  .overview-main { grid-template-columns: 1fr; }
  .form-grid { grid-template-columns: 1fr; }
  .page-hero-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>
