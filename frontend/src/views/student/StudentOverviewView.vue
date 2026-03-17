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
    notifySuccess("已刷新我的论文信息");
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
          <p class="section-kicker">论文工作台</p>
          <h4>我的论文总览</h4>
          <p class="muted">展示当前账号关联论文的核心状态与版本信息。</p>
        </div>
        <div class="row-actions compact">
          <button class="accent" :disabled="loading" @click="fetchMyThesis">
            {{ loading ? "刷新中..." : "刷新" }}
          </button>
          <RouterLink class="mini-link strong" to="/student/thesis">论文信息</RouterLink>
          <RouterLink class="mini-link strong" to="/student/submit">上传与送审</RouterLink>
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
              <p class="muted">请根据当前论文状态继续办理后续事项。</p>
            </div>
          </div>

          <div class="state-note" :class="{ warning: !thesis }">
            <strong>{{ thesis ? "论文信息已同步" : "待完善基础信息" }}</strong>
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
              <p class="muted">可直接进入论文信息维护或上传送审办理。</p>
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
