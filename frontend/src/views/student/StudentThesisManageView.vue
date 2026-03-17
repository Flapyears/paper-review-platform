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
    notifySuccess(`论文创建成功，ID: ${thesisId.value}`);
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
    notifySuccess("论文信息已更新");
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
          <p class="muted">填写论文标题并选择导师，完成论文基础信息维护。</p>
        </div>
        <div class="row-actions compact">
          <button v-if="!thesisId" class="accent" :disabled="!advisorId" @click="createThesis">创建论文</button>
          <button v-else class="accent" :disabled="!advisorId" @click="updateTitle">保存论文信息</button>
          <button @click="loadMyThesis">刷新论文信息</button>
          <RouterLink class="mini-link" to="/student/submit">上传与送审</RouterLink>
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
            <p class="muted">请确认论文标题和导师信息准确无误。</p>
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
              <p class="muted">基础信息将作为后续上传和送审的论文依据。</p>
            </div>
          </div>

          <div class="state-note" :class="{ warning: !currentThesis }">
            <strong>{{ currentThesis ? "论文信息已保存" : "请先建立论文信息" }}</strong>
            <p>
              {{
                currentThesis
                  ? "如需修改论文标题或指导教师，请在提交送审前完成更新。"
                  : "创建论文后，系统会记录论文编号，并用于后续终稿上传和送审提交。"
              }}
            </p>
          </div>
        </section>

        <section class="panel-card content-card side-card">
          <div class="section-head">
            <div>
              <h4>常用入口</h4>
              <p class="muted">按流程继续办理论文相关事项。</p>
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
