import { reactive } from "vue";

export const noticeState = reactive({
  message: "",
  type: "success",
});

export function notifySuccess(message) {
  noticeState.message = message;
  noticeState.type = "success";
}

export function notifyError(message) {
  noticeState.message = message;
  noticeState.type = "error";
}

export function clearNotice() {
  noticeState.message = "";
  noticeState.type = "success";
}
