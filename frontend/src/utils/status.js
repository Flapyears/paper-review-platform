export function formatThesisStatus(status) {
  if (status === "DRAFT") return "草稿中";
  if (status === "SUBMITTED") return "已提交待分配";
  if (status === "REVIEWING") return "评阅中";
  if (status === "REVIEW_DONE") return "评阅完成";
  return status || "-";
}

export function formatReviewTaskStatus(status) {
  if (status === "ASSIGNED") return "待处理";
  if (status === "DRAFTING") return "填写中";
  if (status === "SUBMITTED") return "已提交";
  if (status === "RETURNED") return "退回修改";
  if (status === "CANCELLED") return "已取消";
  return status || "-";
}
