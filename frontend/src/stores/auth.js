import { reactive } from "vue";

const STORAGE_KEY = "prp_auth_session";

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

const saved = loadFromStorage();

export const authState = reactive({
  token: saved?.token ?? "",
  userId: saved?.userId ?? "",
  role: saved?.role ?? "",
  userName: saved?.userName ?? "",
  isAuthenticated: Boolean(saved?.token),
});

export function persistAuth() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      token: authState.token,
      userId: authState.userId,
      role: authState.role,
      userName: authState.userName,
    })
  );
}

export function setSession({ token, user }) {
  authState.token = token;
  authState.userId = String(user.id);
  authState.role = user.role;
  authState.userName = user.name;
  authState.isAuthenticated = true;
  persistAuth();
}

export function setDevIdentity({ userId, role, userName }) {
  authState.token = "";
  authState.userId = String(userId);
  authState.role = role;
  authState.userName = userName;
  authState.isAuthenticated = true;
  persistAuth();
}

export function clearSession() {
  authState.token = "";
  authState.userId = "";
  authState.role = "";
  authState.userName = "";
  authState.isAuthenticated = false;
  localStorage.removeItem(STORAGE_KEY);
}

export function authHeaders() {
  if (authState.token) {
    return { Authorization: `Bearer ${authState.token}` };
  }
  // Fallback for local dev tools mode
  if (authState.userId && authState.role) {
    return {
      "X-User-Id": String(authState.userId),
      "X-Role": String(authState.role),
      "X-User-Name": String(authState.userName || "dev-user"),
    };
  }
  return {};
}
