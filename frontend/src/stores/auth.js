import { reactive } from "vue";

const STORAGE_KEY = "prp_vue_auth";

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

const saved = loadFromStorage();

export const authState = reactive({
  userId: saved?.userId ?? "1",
  role: saved?.role ?? "student",
  userName: saved?.userName ?? "demo-user",
});

export function saveAuth() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(authState));
}

export function authHeaders() {
  return {
    "X-User-Id": String(authState.userId || ""),
    "X-Role": String(authState.role || ""),
    "X-User-Name": String(authState.userName || ""),
  };
}
