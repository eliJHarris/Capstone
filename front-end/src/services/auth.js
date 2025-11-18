const resolveDefaultAuthBase = () => {
  if (typeof window !== "undefined" && window?.location?.origin) {
    return `${window.location.origin.replace(/\/$/, "")}/auth`;
  }
  return "https://localhost/auth";
};

const DEFAULT_AUTH_BASE = resolveDefaultAuthBase();

const AUTH_API_BASE =
  (import.meta.env.VITE_AUTH_API_BASE_URL || DEFAULT_AUTH_BASE).replace(/\/$/, "");

export async function loginRequest(username, password) {
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

  localStorage.setItem("auth_token", data.access_token);
  localStorage.setItem("auth_user", JSON.stringify(data.user));

  return data;
}

export function logout() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_user");
}
