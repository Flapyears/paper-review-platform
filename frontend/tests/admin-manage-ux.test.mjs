import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

function readUtf8(relativePath) {
  return readFileSync(new URL(relativePath, import.meta.url), "utf8");
}

const reviewerView = readUtf8("../src/views/admin/AdminReviewerManageView.vue");
const studentView = readUtf8("../src/views/admin/AdminStudentManageView.vue");

for (const [fileName, content] of [
  ["AdminReviewerManageView.vue", reviewerView],
  ["AdminStudentManageView.vue", studentView],
]) {
  assert.ok(
    !content.includes("新增评阅教师") && !content.includes("新增学生账号"),
    `${fileName} 仍保留页内新增表单标题`
  );
  assert.ok(
    !content.includes("编辑与账号操作"),
    `${fileName} 仍保留页内编辑区域`
  );
  assert.ok(
    content.includes("导入 Excel"),
    `${fileName} 缺少导入 Excel 入口`
  );
  assert.ok(
    content.includes("下载模板"),
    `${fileName} 缺少下载模板入口`
  );
}

console.log("admin manage ux checks passed");
