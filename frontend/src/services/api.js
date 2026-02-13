import { authHeaders } from "../stores/auth";

function joinError(status, statusText, detail) {
  return `${status} ${statusText}: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`;
}

export async function request(path, options = {}) {
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
    throw new Error(joinError(response.status, response.statusText, payload?.detail || payload));
  }
  return payload;
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
