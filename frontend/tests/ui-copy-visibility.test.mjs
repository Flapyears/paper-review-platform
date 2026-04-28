import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

function readUtf8(path) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

const styles = readUtf8("../src/styles.css");
const authLayout = readUtf8("../src/layouts/AuthLayout.vue");
const loginView = readUtf8("../src/views/LoginView.vue");
const homeView = readUtf8("../src/views/HomeView.vue");
const studentOverviewView = readUtf8("../src/views/student/StudentOverviewView.vue");
const studentSubmitView = readUtf8("../src/views/student/StudentSubmitView.vue");
const studentThesisManageView = readUtf8("../src/views/student/StudentThesisManageView.vue");
const adminOverviewView = readUtf8("../src/views/admin/AdminOverviewView.vue");
const adminAssignView = readUtf8("../src/views/admin/AdminAssignView.vue");
const reviewerOverviewView = readUtf8("../src/views/reviewer/ReviewerOverviewView.vue");
const reviewerFormSubmitView = readUtf8("../src/views/reviewer/ReviewerFormSubmitView.vue");
const helpView = readUtf8("../src/views/HelpView.vue");

assert.match(
  styles,
  /\.panel-card\.auth-hero\s*\{/,
  "缺少针对 auth-hero 的专用卡片样式，通用 panel-card 仍可能把深色欢迎区冲掉。"
);

const forbiddenCopyByFile = [
  {
    file: "AuthLayout.vue",
    content: authLayout,
    phrases: [
      "Paper Review Platform",
      "系统将根据角色进入对应工作台。",
      "学生：论文上传与送审",
      "管理员：评阅分配与过程控制",
      "评阅教师：任务执行与评阅提交",
      "流程可追溯",
      "权限隔离",
      "状态联动",
    ],
  },
  {
    file: "LoginView.vue",
    content: loginView,
    phrases: ["Secure Login", "请输入账号和密码登录系统。", "快速登录（仅开发环境）"],
  },
  {
    file: "HomeView.vue",
    content: homeView,
    phrases: ["以下内容根据当前登录角色自动展示。"],
  },
  {
    file: "StudentOverviewView.vue",
    content: studentOverviewView,
    phrases: ["展示当前账号关联论文的核心状态与版本信息。", "请根据当前论文状态继续办理后续事项。"],
  },
  {
    file: "StudentSubmitView.vue",
    content: studentSubmitView,
    phrases: ["上传终稿后提交送审，系统将记录当前送审版本。", "快速查看论文状态或维护论文基础信息。"],
  },
  {
    file: "StudentThesisManageView.vue",
    content: studentThesisManageView,
    phrases: ["填写论文标题并选择导师，完成论文基础信息维护。", "按流程继续办理论文相关事项。"],
  },
  {
    file: "AdminOverviewView.vue",
    content: adminOverviewView,
    phrases: ["查看论文状态分布与评阅完成度。"],
  },
  {
    file: "AdminAssignView.vue",
    content: adminAssignView,
    phrases: ["先选择论文，再从候选教师列表中选择评阅人。"],
  },
  {
    file: "ReviewerOverviewView.vue",
    content: reviewerOverviewView,
    phrases: ["查看当前评阅教师分配到的全部任务。"],
  },
  {
    file: "ReviewerFormSubmitView.vue",
    content: reviewerFormSubmitView,
    phrases: ["从“我的任务列表”点击“填写评阅”进入后会自动加载任务；无任务时不可提交。", "点击任务可快速切换。"],
  },
  {
    file: "HelpView.vue",
    content: helpView,
    phrases: ["这里集中展示平台业务流程与操作建议。"],
  },
];

for (const entry of forbiddenCopyByFile) {
  for (const phrase of entry.phrases) {
    assert.ok(
      !entry.content.includes(phrase),
      `${entry.file} 仍包含偏技术或冗长文案：${phrase}`
    );
  }
}

console.log("ui copy and visibility checks passed");
