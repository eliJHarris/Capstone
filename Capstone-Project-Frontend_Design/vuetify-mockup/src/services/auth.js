// src/services/auth.js
export async function loginRequest(username, password) {
  // auth-api expects x-www-form-urlencoded
  const body = new URLSearchParams();
  body.append("username", username);
  body.append("password", password);

  const resp = await fetch("http://localhost:8080/login", {
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
