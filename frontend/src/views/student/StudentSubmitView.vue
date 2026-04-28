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
      throw new Error("请先选择文件");
    }
    const form = new FormData();
    form.append("file", fileRef.value);
    const data = await request(`/api/thesis/${Number(thesisId.value)}/upload-final`, {
      method: "POST",
      body: form,
    });
    notifySuccess(`终稿上传成功，版本号: V${data?.data?.version_no || "-"}`);
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
        <div class="row-actions compact">
          <button class="accent" @click="uploadFinal">上传终稿</button>
          <button class="warn" @click="submitFinal">提交送审</button>
          <button @click="loadCurrent">刷新</button>
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

        <div class="form-grid three">
          <label>
            论文ID
            <input v-model="thesisId" type="number" />
          </label>
          <label class="wide">
            终稿文件（PDF / DOCX）
            <input type="file" accept=".pdf,.docx" @change="onFileChange" />
          </label>
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
