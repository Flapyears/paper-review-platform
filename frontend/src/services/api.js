import { authHeaders } from "../stores/auth";

function joinError(status, statusText, detail) {
  return `${status} ${statusText}: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`;
}

function statusToUserMessage(status) {
  if (status === 400) return "请求参数有误，请检查后重试。";
  if (status === 401) return "登录状态已失效，请重新登录。";
  if (status === 403) return "当前账号无权限执行该操作。";
  if (status === 404) return "目标数据不存在或已被删除。";
  if (status === 409) return "数据状态冲突，请刷新后重试。";
  if (status === 422) return "提交内容不符合要求，请检查输入。";
  if (status === 429) return "操作过于频繁，请稍后再试。";
  if (status >= 500) return "服务器开小差了，请稍后再试。";
  return "请求失败，请稍后重试。";
}

function buildUserMessage(status, detail) {
  if (status === 422 && typeof detail === "string") {
    return detail;
  }
  if (status === 400 && typeof detail === "string") {
    if (detail.includes("incomplete")) return "评阅表单未填写完整，请补全后再提交。";
    if (detail.includes("Invalid")) return "输入数据格式有误，请检查后再试。";
  }
  return statusToUserMessage(status);
}

function logDevError(devMessage, context = {}) {
  if (import.meta.env.DEV || import.meta.env.VITE_LOG_API_ERRORS === "true") {
    console.error("[API_ERROR]", devMessage, context);
  }
}

class ApiRequestError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = "ApiRequestError";
    this.status = options.status || 0;
    this.devMessage = options.devMessage || message;
    this.rawDetail = options.rawDetail;
  }
}

export async function request(path, options = {}) {
  try {
    const headers = {
      ...authHeaders(),
      ...(options.headers || {}),
    };
    const response = await fetch(path, {
      ...options,
      headers,
    });
    const type = response.headers.get("content-type") || "";
    const payload = type.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
      const detail = payload?.detail || payload;
      const devMessage = joinError(response.status, response.statusText, detail);
      logDevError(devMessage, { path, method: options.method || "GET", detail });
      throw new ApiRequestError(buildUserMessage(response.status, detail), {
        status: response.status,
        devMessage,
        rawDetail: detail,
      });
    }
    return payload;
  } catch (err) {
    if (err instanceof ApiRequestError) {
      throw err;
    }
    const devMessage = err?.message || String(err);
    logDevError(devMessage, { path, method: options.method || "GET" });
    throw new ApiRequestError("网络异常，请检查网络连接后重试。", {
      status: 0,
      devMessage,
    });
  }
}

export async function requestJson(path, method, payload) {
  return request(path, {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
