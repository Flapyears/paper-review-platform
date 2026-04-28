<script setup>
import { computed, onMounted, ref } from "vue";
import { request, requestJson } from "../../services/api";
import { notifyError, notifySuccess } from "../../stores/notice";
import PaginationBar from "../../components/common/PaginationBar.vue";
import { formatThesisStatus } from "../../utils/status";

const submittedTheses = ref([]);
const thesisId = ref("");
const assignReason = ref("");
const assignResult = ref(null);
const reviewerLimit = ref(8);
const autoAssigning = ref(false);
const autoReviewersPerThesis = ref(2);
const maxPerDepartment = ref(1);

const reviewers = ref([]);
const reviewerKeyword = ref("");
const loadingReviewers = ref(false);
const selectedReviewerIds = ref([]);
const thesisPage = ref(1);
const thesisPageSize = ref(10);
const reviewerPage = ref(1);
const reviewerPageSize = ref(10);

const pagedSubmittedTheses = computed(() => {
  const start = (thesisPage.value - 1) * thesisPageSize.value;
  return submittedTheses.value.slice(start, start + thesisPageSize.value);
});

const pagedReviewers = computed(() => {
  const start = (reviewerPage.value - 1) * reviewerPageSize.value;
  return reviewers.value.slice(start, start + reviewerPageSize.value);
});

async function loadSubmitted() {
  try {
    const resp = await request("/api/admin/thesis?status=SUBMITTED");
    submittedTheses.value = resp.items || [];
    thesisPage.value = 1;
    if (!thesisId.value && submittedTheses.value.length) {
      thesisId.value = String(submittedTheses.value[0].id);
      await loadReviewers();
    }
    notifySuccess("待安排论文已更新");
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function loadReviewers() {
  if (!thesisId.value) {
    reviewers.value = [];
    selectedReviewerIds.value = [];
    return;
  }
  loadingReviewers.value = true;
  try {
    const params = new URLSearchParams();
    params.set("thesis_id", String(Number(thesisId.value)));
    params.set("max_task_limit", String(Number(reviewerLimit.value) || 8));
    params.set("max_per_department", String(Number(maxPerDepartment.value) || 1));
    if (reviewerKeyword.value.trim()) {
      params.set("q", reviewerKeyword.value.trim());
    }
    const resp = await request(`/api/admin/reviewers?${params.toString()}`);
    reviewers.value = resp.items || [];
    reviewerPage.value = 1;
    selectedReviewerIds.value = selectedReviewerIds.value.filter((id) =>
      reviewers.value.some((x) => x.id === id && !x.is_conflicted)
    );
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loadingReviewers.value = false;
  }
}

function toggleReviewer(id) {
  const reviewer = reviewers.value.find((x) => x.id === id);
  if (!reviewer || reviewer.is_conflicted || reviewer.department_will_exceed_quota) {
    return;
  }
  if (selectedReviewerIds.value.includes(id)) {
    selectedReviewerIds.value = selectedReviewerIds.value.filter((x) => x !== id);
  } else {
    selectedReviewerIds.value = [...selectedReviewerIds.value, id];
  }
}

const selectedReviewers = computed(() =>
  reviewers.value.filter((x) => selectedReviewerIds.value.includes(x.id))
);

const selectedThesis = computed(() =>
  submittedTheses.value.find((x) => x.id === Number(thesisId.value)) || null
);

const availableReviewers = computed(() => reviewers.value.filter((x) => !x.is_conflicted));

function fmtDate(iso) {
  if (!iso) {
    return "-";
  }
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) {
    return iso;
  }
  return dt.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function assignTasks() {
  try {
    if (!thesisId.value) {
      throw new Error("请先选择论文");
    }
    if (!selectedReviewerIds.value.length) {
      throw new Error("请至少选择一位评阅教师");
    }

    const payload = {
      items: [
        {
          thesis_id: Number(thesisId.value),
          reviewer_ids: selectedReviewerIds.value,
          reason: assignReason.value || null,
        },
      ],
      max_reviewers_per_department: Number(maxPerDepartment.value) || 1,
    };
    const resp = await requestJson("/api/admin/review-tasks/assign", "POST", payload);
    notifySuccess(`分配完成，已创建 ${(resp.data?.task_ids || []).length} 个任务`);
    const listResp = await request("/api/admin/thesis");
    const matched = (listResp.items || []).find((x) => x.id === Number(thesisId.value));
    assignResult.value = {
      taskIds: resp.data?.task_ids || [],
      thesis: matched || null,
      reviewerNames: selectedReviewers.value.map((x) => `${x.name}(#${x.id})`),
    };
    await loadSubmitted();
    await loadReviewers();
  } catch (err) {
    notifyError(err.message || String(err));
  }
}

async function autoAssignUnassigned() {
  autoAssigning.value = true;
  try {
    const resp = await requestJson("/api/admin/review-tasks/auto-assign", "POST", {
      reviewers_per_thesis: Number(autoReviewersPerThesis.value) || 2,
      max_task_limit: Number(reviewerLimit.value) || 8,
      max_reviewers_per_department: Number(maxPerDepartment.value) || 1,
      reason: assignReason.value || "系统自动分配",
    });
    const data = resp.data || {};
    notifySuccess(
      `自动安排完成：已处理 ${data.assigned_thesis_count || 0} 篇论文，生成 ${data.created_task_count || 0} 个任务`
    );
    assignResult.value = {
      taskIds: data.created_task_ids || [],
      thesis: null,
      reviewerNames: [],
      auto: {
        assignedThesisCount: data.assigned_thesis_count || 0,
        skippedCount: (data.skipped || []).length,
      },
    };
    await loadSubmitted();
    await loadReviewers();
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    autoAssigning.value = false;
  }
}

function selectThesis(id) {
  thesisId.value = String(id);
  selectedReviewerIds.value = [];
  loadReviewers();
}

onMounted(loadSubmitted);
</script>

<template>
  <section class="panel-card">
    <h4>评阅分配</h4>
    <p class="muted">先选论文，再选合适的评阅老师。</p>

    <div class="row-actions">
      <button class="accent" @click="loadSubmitted">刷新论文</button>
      <button :disabled="!thesisId || loadingReviewers" @click="loadReviewers">
        {{ loadingReviewers ? "加载中..." : "刷新候选教师" }}
      </button>
      <button class="warn" :disabled="autoAssigning" @click="autoAssignUnassigned">
        {{ autoAssigning ? "自动安排中..." : "自动安排剩余论文" }}
      </button>
    </div>

    <table v-if="submittedTheses.length" class="data-table">
      <thead>
        <tr>
          <th>论文ID</th>
          <th>标题</th>
          <th>学生ID</th>
          <th>版本号</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in pagedSubmittedTheses" :key="row.id">
          <td>{{ row.id }}</td>
          <td>{{ row.title }}</td>
          <td>{{ row.student_id }}</td>
          <td>{{ row.current_version_no ? `V${row.current_version_no}` : "-" }}</td>
          <td><button @click="selectThesis(row.id)">选择</button></td>
        </tr>
      </tbody>
    </table>
    <PaginationBar
      v-model:current="thesisPage"
      v-model:pageSize="thesisPageSize"
      :total="submittedTheses.length"
    />
    <div v-if="!submittedTheses.length" class="empty-box">当前没有待安排的论文。</div>

    <div class="form-grid three" style="margin-top: 12px">
      <label>
        论文ID
        <input v-model="thesisId" type="number" @change="loadReviewers" />
      </label>
      <label>
        搜索教师
        <input v-model="reviewerKeyword" placeholder="输入姓名或ID" />
      </label>
      <label>
        单人任务上限
        <input v-model.number="reviewerLimit" type="number" min="1" @change="loadReviewers" />
      </label>
      <label>
        自动分配每篇人数
        <input v-model.number="autoReviewersPerThesis" type="number" min="1" max="5" />
      </label>
      <label>
        科室名额上限
        <select v-model.number="maxPerDepartment" @change="loadReviewers">
          <option :value="1">1</option>
          <option :value="2">2</option>
          <option :value="3">3</option>
        </select>
      </label>
    </div>
    <div class="row-actions" style="margin-top: 8px">
      <button :disabled="!thesisId || loadingReviewers" @click="loadReviewers">按条件重新筛选教师</button>
    </div>

    <div v-if="selectedThesis" class="detail-grid" style="margin-top: 8px">
      <div><span>当前论文</span><b>{{ selectedThesis.title }} (#{{ selectedThesis.id }})</b></div>
      <div><span>学生ID</span><b>{{ selectedThesis.student_id }}</b></div>
      <div><span>当前版本</span><b>{{ selectedThesis.current_version_no ? `V${selectedThesis.current_version_no}` : "-" }}</b></div>
      <div><span>已分配数</span><b>{{ selectedThesis.assigned_count }}</b></div>
    </div>

    <table v-if="reviewers.length" class="data-table" style="margin-top: 12px">
      <thead>
        <tr>
          <th>选择</th>
          <th>教师</th>
          <th>科室</th>
          <th>活跃任务</th>
          <th>已提交任务</th>
          <th>可分配余量</th>
          <th>科室名额</th>
          <th>冲突</th>
          <th>最近分配</th>
          <th>推荐分</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="reviewer in pagedReviewers" :key="reviewer.id" :class="{ conflict: reviewer.is_conflicted }">
          <td>
            <input
              type="checkbox"
              :disabled="reviewer.is_conflicted || reviewer.department_will_exceed_quota"
              :checked="selectedReviewerIds.includes(reviewer.id)"
              @change="toggleReviewer(reviewer.id)"
            />
          </td>
          <td>{{ reviewer.name }} (#{{ reviewer.id }})</td>
          <td>{{ reviewer.department }}</td>
          <td>{{ reviewer.active_task_count }}</td>
          <td>{{ reviewer.submitted_task_count }}</td>
          <td>{{ reviewer.available_slots }}</td>
          <td>
            {{ reviewer.department_assigned_count }}/{{ reviewer.department_max_limit }}
            <span v-if="reviewer.department_will_exceed_quota">（超限）</span>
          </td>
          <td>
            {{
              reviewer.is_conflicted
                ? reviewer.conflict_reason
                : reviewer.department_will_exceed_quota
                  ? "科室名额超限"
                  : "-"
            }}
          </td>
          <td>{{ fmtDate(reviewer.latest_assigned_at) }}</td>
          <td>{{ reviewer.recommendation_score }}</td>
        </tr>
      </tbody>
    </table>
    <PaginationBar
      v-model:current="reviewerPage"
      v-model:pageSize="reviewerPageSize"
      :total="reviewers.length"
    />
    <div v-if="!reviewers.length && thesisId && !loadingReviewers" class="empty-box">
      该论文暂无可显示的教师候选，或当前筛选条件没有结果。
    </div>

    <div v-if="selectedReviewers.length" class="detail-grid" style="margin-top: 10px">
      <div>
        <span>已选教师</span>
        <b>{{ selectedReviewers.map((x) => `${x.name}(#${x.id})`).join("，") }}</b>
      </div>
      <div>
        <span>已选数量</span>
        <b>{{ selectedReviewers.length }}</b>
      </div>
    </div>

    <label class="single-line-label">
      分配原因
      <input v-model="assignReason" placeholder="可选，方便记录安排原因" />
    </label>

    <div class="row-actions">
      <button class="accent" :disabled="!thesisId || !selectedReviewerIds.length" @click="assignTasks">
        确认分配
      </button>
    </div>

    <div class="detail-grid">
      <div><span>候选教师数</span><b>{{ reviewers.length }}</b></div>
      <div><span>可分配教师数</span><b>{{ availableReviewers.length }}</b></div>
      <div><span>当前科室名额</span><b>{{ maxPerDepartment }}</b></div>
    </div>

    <div v-if="assignResult" class="detail-grid">
      <div><span>新建任务ID</span><b>{{ assignResult.taskIds.join(", ") || "-" }}</b></div>
      <div><span>论文ID</span><b>{{ assignResult.thesis?.id || thesisId }}</b></div>
      <div><span>论文状态</span><b>{{ formatThesisStatus(assignResult.thesis?.status) }}</b></div>
      <div><span>已分配任务数</span><b>{{ assignResult.thesis?.assigned_count ?? "-" }}</b></div>
      <div><span>分配给</span><b>{{ assignResult.reviewerNames.join("，") || "-" }}</b></div>
      <div><span>自动分配论文数</span><b>{{ assignResult.auto?.assignedThesisCount ?? "-" }}</b></div>
      <div><span>自动分配跳过数</span><b>{{ assignResult.auto?.skippedCount ?? "-" }}</b></div>
    </div>
  </section>
</template>
