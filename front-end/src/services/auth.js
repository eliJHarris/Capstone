// src/services/auth.js
const DEFAULT_AUTH_BASE = (() => {
  if (typeof window === "undefined") {
    return "https://localhost/auth";
  }
  const origin = window.location.origin;
  const normalized = origin.replace(/\/$/, "");
  const isLocalDev =
    origin.includes("localhost:5173") ||
    origin.includes("localhost:3000") ||
    origin.includes("localhost:8080");

  if (isLocalDev || origin.startsWith("http://localhost")) {
    return "https://localhost/auth";
  }
  return `${normalized}/auth`;
})();

const AUTH_API_BASE =
  (import.meta.env.VITE_AUTH_API_BASE_URL || DEFAULT_AUTH_BASE).replace(/\/$/, "");

export async function loginRequest(username, password) {
  // auth-api expects x-www-form-urlencoded
  const body = new URLSearchParams();
  body.append("username", username);
  body.append("password", password);

  const resp = await fetch(`${AUTH_API_BASE}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });

  if (!resp.ok) {
    const errData = await resp.json().catch(() => ({}));
    throw new Error(errData.detail || "Login failed");
  }

  const data = await resp.json();
  // data looks like:
  // {
  //   access_token: "....",
  //   token_type: "bearer",
  //   user: { dn, cn, uid, mail }
  // }

  localStorage.setItem("auth_token", data.access_token);
  localStorage.setItem("auth_user", JSON.stringify(data.user));

  return data;
}

export function getAuthToken() {
  return localStorage.getItem("auth_token");
}

export function getAuthUser() {
  const raw = localStorage.getItem("auth_user");
  try {
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function logout() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_user");
}
