<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { request } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";

const loading = ref(false);
const thesis = ref(null);
const progressMap = {
  DRAFT: 25,
  SUBMITTED: 50,
  REVIEWING: 75,
  REVIEW_DONE: 100,
};

function statusLabel(status) {
  if (status === "DRAFT") return "草稿中";
  if (status === "SUBMITTED") return "已提交待分配";
  if (status === "REVIEWING") return "评阅中";
  if (status === "REVIEW_DONE") return "评阅完成";
  return status || "-";
}

const progressValue = computed(() => {
  if (!thesis.value) return 0;
  return progressMap[thesis.value.status] || 0;
});

const overviewCards = computed(() => {
  if (!thesis.value) {
    return [
      { label: "当前状态", value: "未创建论文", tone: "neutral" },
      { label: "当前版本号", value: "-", tone: "neutral" },
      { label: "导师信息", value: "未选择", tone: "neutral" },
      { label: "流程进度", value: "0%", tone: "neutral" },
    ];
  }

  return [
    { label: "当前状态", value: statusLabel(thesis.value.status), tone: "primary" },
    {
      label: "当前版本号",
      value: thesis.value.current_version_no ? `V${thesis.value.current_version_no}` : "-",
      tone: "neutral",
    },
    { label: "导师信息", value: thesis.value.advisor_id ? `#${thesis.value.advisor_id}` : "未选择", tone: "neutral" },
    { label: "流程进度", value: `${progressValue.value}%`, tone: "accent" },
  ];
});

const thesisFacts = computed(() => {
  if (!thesis.value) return [];
  return [
    { label: "论文ID", value: thesis.value.id },
    { label: "论文标题", value: thesis.value.title || "-" },
    { label: "当前状态", value: statusLabel(thesis.value.status) },
    {
      label: "当前版本号",
      value: thesis.value.current_version_no ? `V${thesis.value.current_version_no}` : "-",
    },
    { label: "导师信息", value: thesis.value.advisor_id ? `#${thesis.value.advisor_id}` : "未选择" },
    { label: "退回原因", value: thesis.value.return_reason || "-" },
  ];
});

const stepItems = computed(() => {
  if (!thesis.value) {
    return [
      { title: "创建论文", desc: "前往“论文信息”页面填写论文标题并选择指导教师。", done: false },
      { title: "上传终稿", desc: "论文信息创建完成后，在“上传与送审”页面上传终稿文件。", done: false },
      { title: "提交送审", desc: "确认终稿无误后提交送审，等待后续评审流程。", done: false },
    ];
  }

  const status = thesis.value.status;
  return [
    {
      title: "创建论文",
      desc: "论文基础信息已建立，可继续办理后续事项。",
      done: true,
    },
    {
      title: "上传终稿",
      desc:
        status === "DRAFT"
          ? "请上传当前准备送审的终稿文件。"
          : "终稿版本已上传，可根据需要查看当前版本号。",
      done: status !== "DRAFT",
    },
    {
      title: "提交送审",
      desc:
        status === "DRAFT"
          ? "上传终稿后即可提交送审。"
          : status === "SUBMITTED"
            ? "论文已提交送审，等待分配评阅。"
            : status === "REVIEWING"
              ? "论文已进入评阅环节，请关注评阅进度。"
              : "评阅流程已完成，请关注后续安排。",
      done: status !== "DRAFT",
    },
  ];
});

const nextAction = computed(() => {
  if (!thesis.value) {
    return {
      title: "优先完成论文创建",
      desc: "请先进入“论文信息”页面创建论文并填写基础信息。",
    };
  }

  const status = thesis.value.status;
  if (status === "DRAFT") {
    return {
      title: "上传终稿并提交送审",
      desc: "当前论文仍处于草稿阶段，请尽快上传终稿并完成送审提交。",
    };
  }
  if (status === "SUBMITTED") {
    return {
      title: "等待分配评阅",
      desc: "论文已提交成功，请关注状态变化并等待后续评审安排。",
    };
  }
  if (status === "REVIEWING") {
    return {
      title: "关注评阅进度",
      desc: "论文正在评阅中，如有退回请按要求修改后重新提交。",
    };
  }
  return {
    title: "评阅已完成",
    desc: "请根据平台后续通知办理下一阶段事项。",
  };
});

async function fetchMyThesis() {
  loading.value = true;
  try {
    const data = await request("/api/thesis/my");
    thesis.value = data.thesis;
    notifySuccess("论文信息已更新");
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}

onMounted(fetchMyThesis);
</script>

<template>
  <section class="overview-page">
    <div class="panel-card page-hero">
      <div class="page-hero-main">
        <div>
          <p class="section-kicker">论文进度</p>
          <h4>我的论文总览</h4>
          <p class="muted">这里能看到论文进展、版本和下一步。</p>
        </div>
        <div class="header-actions">
          <button class="tool-btn" :disabled="loading" @click="fetchMyThesis" :title="loading ? '刷新中...' : '刷新状态'">
            <span class="icon">↻</span>
          </button>
          <RouterLink class="secondary-btn" to="/student/thesis">
            <span class="icon">📄</span> 论文信息
          </RouterLink>
          <RouterLink class="primary-btn" to="/student/submit">
            <span class="entry-text">上传与送审</span>
            <span class="entry-arrow">→</span>
          </RouterLink>
        </div>
      </div>

      <div class="overview-metrics">
        <article
          v-for="card in overviewCards"
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
            <h4>论文状态</h4>
            <p class="muted">查看论文当前进度、状态和基础信息。</p>
          </div>
          <span class="status-chip" :class="{ empty: !thesis }">
            {{ thesis ? statusLabel(thesis.status) : "暂无论文" }}
          </span>
        </div>

        <div class="progress-box">
          <div class="progress-meta">
            <span>流程进度</span>
            <b>{{ progressValue }}%</b>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: `${progressValue}%` }"></div>
          </div>
          <p class="muted">
            {{ thesis ? `当前阶段：${statusLabel(thesis.status)}` : "当前账号暂无论文，请在“论文信息”页面创建。" }}
          </p>
        </div>

        <div v-if="thesis" class="detail-grid overview-detail-grid">
          <div v-for="item in thesisFacts" :key="item.label">
            <span>{{ item.label }}</span>
            <b>{{ item.value }}</b>
          </div>
        </div>

        <div class="student-flow-card">
          <div class="student-flow-head">
            <h5>当前办理步骤</h5>
            <span>{{ stepItems.filter((item) => item.done).length }}/{{ stepItems.length }}</span>
          </div>
          <div class="student-step-list">
            <div
              v-for="item in stepItems"
              :key="item.title"
              class="student-step-item"
              :class="{ done: item.done }"
            >
              <strong>{{ item.title }}</strong>
              <p>{{ item.desc }}</p>
            </div>
          </div>
        </div>

        <div class="empty-box overview-action-box" :class="{ ready: thesis }">
          <p v-if="thesis">{{ nextAction.title }}：{{ nextAction.desc }}</p>
          <p v-else>当前账号暂无论文，请在“论文信息”页面创建。</p>
          <div class="quick-links">
            <RouterLink class="entry-link" to="/student/thesis">前往论文信息</RouterLink>
            <RouterLink class="mini-link" to="/student/submit">查看上传与送审</RouterLink>
          </div>
        </div>
      </section>

      <aside class="overview-side">
        <section class="panel-card content-card side-card">
          <div class="section-head">
            <div>
            <h4>办理提醒</h4>
              <p class="muted">下一步做什么，这里会直接告诉你。</p>
            </div>
          </div>

          <div class="state-note" :class="{ warning: !thesis }">
            <strong>{{ thesis ? "可以继续下一步" : "先补全论文信息" }}</strong>
            <p>
              {{
                thesis
                  ? "如需继续提交终稿，请前往“上传与送审”页面完成后续操作。"
                  : "当前账号暂无论文，请先在“论文信息”页面创建论文并填写基础信息。"
              }}
            </p>
          </div>
        </section>

        <section class="panel-card content-card side-card">
          <div class="section-head">
            <div>
              <h4>常用入口</h4>
              <p class="muted">直接进入常用页面，继续处理即可。</p>
            </div>
          </div>

          <div class="quick-action-list">
            <RouterLink class="action-tile primary" to="/student/thesis">
              <strong>论文信息</strong>
              <span>创建或维护论文标题与导师信息</span>
            </RouterLink>
            <RouterLink class="action-tile" to="/student/submit">
              <strong>上传与送审</strong>
              <span>上传终稿文件并提交送审流程</span>
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
  font-size: 26px;
  margin: 0 0 8px;
  letter-spacing: -0.01em;
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
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(30, 58, 138, 0.2);
}

.primary-btn:hover {
  background: #1a357d;
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(30, 58, 138, 0.3);
}

.secondary-btn {
  height: 48px;
  padding: 0 20px;
  background: white;
  color: var(--accent);
  border: 2px solid var(--accent);
  border-radius: 14px;
  text-decoration: none;
  font-weight: 700;
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.secondary-btn:hover {
  background: var(--accent-soft);
  border-color: var(--accent);
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

.entry-arrow {
  font-size: 18px;
  transition: transform 0.2s;
}

.primary-btn:hover .entry-arrow {
  transform: translateX(4px);
}

.icon {
  font-size: 18px;
}

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.metric-card {
  padding: 24px;
  border-radius: 20px;
  background: white;
  border: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: transform 0.2s;
}

.metric-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
}

.metric-card span {
  font-size: 13px;
  color: var(--muted);
  font-weight: 600;
}

.metric-card b {
  font-size: 22px;
  color: var(--ink);
}

.metric-card.primary { border-left: 5px solid var(--accent); }
.metric-card.accent { border-left: 5px solid #10b981; }

.overview-main {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
}

.progress-box {
  margin: 24px 0;
  padding: 20px;
  background: #f8fafc;
  border-radius: 16px;
  border: 1px solid var(--line);
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.progress-track {
  height: 10px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent) 0%, #3b82f6 100%);
  border-radius: 999px;
  transition: width 1s ease-out;
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

.student-flow-card {
  margin-top: 32px;
  padding: 24px;
  background: white;
  border: 1px solid var(--line);
  border-radius: 20px;
}

.student-flow-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.student-flow-head h5 {
  margin: 0;
  font-size: 16px;
}

.student-step-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.student-step-item {
  position: relative;
  padding-left: 32px;
}

.student-step-item::before {
  content: "";
  position: absolute;
  left: 0;
  top: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid var(--line);
  background: white;
}

.student-step-item.done::before {
  background: #10b981;
  border-color: #10b981;
  content: "✓";
  color: white;
  font-size: 12px;
  display: grid;
  place-items: center;
}

.student-step-item strong {
  display: block;
  font-size: 14px;
  margin-bottom: 4px;
}

.student-step-item p {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.action-tile {
  display: flex;
  flex-direction: column;
  padding: 20px;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px solid var(--line);
  text-decoration: none;
  gap: 8px;
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

.action-tile strong {
  font-size: 15px;
  color: var(--ink);
}

.action-tile span {
  font-size: 12px;
  color: var(--muted);
}

@media (max-width: 1100px) {
  .overview-main { grid-template-columns: 1fr; }
  .page-hero-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
}
</style>
