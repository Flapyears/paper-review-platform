<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const title = ref("");
const advisorId = ref("");
const thesisId = ref("");
const advisors = ref([]);
const loadingAdvisors = ref(false);
const currentThesis = ref(null);

function statusLabel(status) {
  if (status === "DRAFT") return "草稿中";
  if (status === "SUBMITTED") return "已提交待分配";
  if (status === "REVIEWING") return "评阅中";
  if (status === "REVIEW_DONE") return "评阅完成";
  return status || "-";
}

const summaryCards = computed(() => {
  if (!currentThesis.value) {
    return [
      { label: "论文编号", value: "未创建", tone: "neutral" },
      { label: "论文状态", value: "待填写", tone: "neutral" },
      { label: "导师信息", value: "未选择", tone: "neutral" },
      { label: "当前版本号", value: "-", tone: "neutral" },
    ];
  }

  return [
    { label: "论文编号", value: currentThesis.value.id, tone: "primary" },
    { label: "论文状态", value: statusLabel(currentThesis.value.status), tone: "accent" },
    { label: "导师信息", value: currentThesis.value.advisor_id || "-", tone: "neutral" },
    {
      label: "当前版本号",
      value: currentThesis.value.current_version_no ? `V${currentThesis.value.current_version_no}` : "-",
      tone: "neutral",
    },
  ];
});

const thesisFacts = computed(() => {
  if (!currentThesis.value) return [];
  return [
    { label: "论文编号", value: currentThesis.value.id },
    { label: "论文标题", value: currentThesis.value.title || "-" },
    { label: "论文状态", value: statusLabel(currentThesis.value.status) },
    { label: "导师信息", value: currentThesis.value.advisor_id ? `#${currentThesis.value.advisor_id}` : "未选择" },
    {
      label: "当前版本号",
      value: currentThesis.value.current_version_no ? `V${currentThesis.value.current_version_no}` : "-",
    },
    { label: "退回原因", value: currentThesis.value.return_reason || "-" },
  ];
});

async function loadMyThesis() {
  try {
    const resp = await request("/api/thesis/my");
    const thesis = resp.thesis;
    currentThesis.value = thesis || null;
    if (!thesis) {
      thesisId.value = "";
      title.value = "";
      advisorId.value = "";
      return;
    }
    thesisId.value = String(thesis.id || "");
    title.value = thesis.title || "";
    advisorId.value = thesis.advisor_id != null ? String(thesis.advisor_id) : "";
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function loadAdvisors() {
  loadingAdvisors.value = true;
  try {
    const resp = await request("/api/thesis/advisors");
    advisors.value = resp.items || [];
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loadingAdvisors.value = false;
  }
}

async function createThesis() {
  try {
    if (!advisorId.value) {
      throw new Error("请选择导师后再创建论文");
    }
    const payload = { title: title.value.trim() };
    payload.advisor_id = Number(advisorId.value);
    const data = await requestJson("/api/thesis/my", "POST", payload);
    thesisId.value = String(data?.data?.thesis_id || "");
    await loadMyThesis();
    notifySuccess("论文已创建");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function updateTitle() {
  try {
    if (!advisorId.value) {
      throw new Error("请选择导师后再保存");
    }
    await requestJson(`/api/thesis/${Number(thesisId.value)}`, "PUT", {
      title: title.value.trim(),
      advisor_id: Number(advisorId.value),
    });
    await loadMyThesis();
    notifySuccess("论文信息已保存");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

onMounted(async () => {
  await Promise.all([loadAdvisors(), loadMyThesis()]);
});
</script>

<template>
  <section class="overview-page">
    <div class="panel-card page-hero">
      <div class="page-hero-main">
        <div>
          <p class="section-kicker">论文信息</p>
          <h4>论文信息维护</h4>
          <p class="muted">先补全标题和导师，后续操作会更顺畅。</p>
        </div>
        <div class="header-actions">
          <button v-if="!thesisId" class="primary-btn" :disabled="!advisorId" @click="createThesis">
            <span class="icon">＋</span> 创建论文
          </button>
          <button v-else class="primary-btn" :disabled="!advisorId" @click="updateTitle">
            <span class="icon">✓</span> 保存论文信息
          </button>
          <button class="tool-btn" @click="loadMyThesis" title="刷新论文信息">
            <span class="icon">↻</span>
          </button>
          <RouterLink class="submit-entry" to="/student/submit">
            <span class="entry-text">上传与送审</span>
            <span class="entry-arrow">→</span>
          </RouterLink>
        </div>
      </div>

      <div class="overview-metrics">
        <article
          v-for="card in summaryCards"
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
            <h4>基础信息填写</h4>
            <p class="muted">确认信息无误后再保存。</p>
          </div>
          <span class="status-chip" :class="{ empty: !currentThesis }">
            {{ currentThesis ? "已建立论文" : "待创建论文" }}
          </span>
        </div>

        <div class="form-grid three">
          <label>
            论文ID
            <input :value="thesisId || '尚未创建'" readonly />
          </label>
          <label class="wide">
            论文标题
            <input v-model="title" placeholder="请输入论文标题" />
          </label>
          <label>
            指导教师
            <select v-model="advisorId" :disabled="loadingAdvisors">
              <option value="">请选择导师</option>
              <option v-for="advisor in advisors" :key="advisor.id" :value="String(advisor.id)">
                {{ advisor.name }} (#{{ advisor.id }}){{ advisor.department ? ` - ${advisor.department}` : "" }}
              </option>
            </select>
          </label>
        </div>

        <div class="row-actions">
          <button :disabled="loadingAdvisors" @click="loadAdvisors">
            {{ loadingAdvisors ? "加载中..." : "刷新导师列表" }}
          </button>
        </div>

        <div v-if="currentThesis" class="detail-grid overview-detail-grid">
          <div v-for="item in thesisFacts" :key="item.label">
            <span>{{ item.label }}</span>
            <b>{{ item.value }}</b>
          </div>
        </div>

        <div v-else class="empty-box">
          <p>当前尚未创建论文，请先填写标题并选择导师后创建论文。</p>
          <div class="quick-links">
            <button class="accent" :disabled="!advisorId" @click="createThesis">立即创建论文</button>
          </div>
        </div>
      </section>

      <aside class="overview-side">
        <section class="panel-card content-card side-card">
          <div class="section-head">
          <div>
            <h4>办理提醒</h4>
            <p class="muted">这些信息会显示在后续评审流程里。</p>
          </div>
          </div>

          <div class="state-note" :class="{ warning: !currentThesis }">
            <strong>{{ currentThesis ? "论文信息已保存" : "请先建立论文信息" }}</strong>
            <p>
              {{
                currentThesis
                  ? "如需修改论文标题或指导教师，请在提交送审前完成更新。"
                  : "创建后就能继续上传终稿和提交送审。"
              }}
            </p>
          </div>
        </section>

        <section class="panel-card content-card side-card">
          <div class="section-head">
          <div>
            <h4>常用入口</h4>
            <p class="muted">下一步常用页面都在这里。</p>
          </div>
          </div>

          <div class="quick-action-list">
            <RouterLink class="action-tile primary" to="/student/overview">
              <strong>论文总览</strong>
              <span>查看论文状态、进度和版本信息</span>
            </RouterLink>
            <RouterLink class="action-tile" to="/student/submit">
              <strong>上传与送审</strong>
              <span>上传终稿并提交送审申请</span>
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
  letter-spacing: 0.1em;
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
  background: #1a357d;
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(30, 58, 138, 0.3);
}

.primary-btn:active:not(:disabled) {
  transform: translateY(0);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
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
  border-color: var(--muted);
}

.submit-entry {
  height: 48px;
  padding: 0 24px;
  background: white;
  color: var(--accent);
  border: 2px solid var(--accent);
  border-radius: 14px;
  text-decoration: none;
  font-weight: 700;
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s;
}

.submit-entry:hover {
  background: var(--accent);
  color: white;
  box-shadow: 0 4px 12px rgba(30, 58, 138, 0.15);
}

.entry-arrow {
  font-size: 18px;
  transition: transform 0.2s;
}

.submit-entry:hover .entry-arrow {
  transform: translateX(4px);
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
  transition: transform 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
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
  align-items: start;
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

.quick-action-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
  border-color: transparent;
}

.action-tile strong {
  color: var(--ink);
  font-size: 15px;
}

.action-tile span {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.4;
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

.state-note strong {
  display: block;
  font-size: 14px;
  margin-bottom: 4px;
}

.state-note p {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.5;
}

@media (max-width: 1100px) {
  .overview-main { grid-template-columns: 1fr; }
  .page-hero-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>
