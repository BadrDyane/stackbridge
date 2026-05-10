const BASE_URL = "http://localhost:8000";

function getToken() {
  return localStorage.getItem("sb_token");
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const resp = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (resp.status === 401) {
    localStorage.removeItem("sb_token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      detail = err.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  if (resp.status === 204) return null;
  return resp.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, body, headers) =>
    request(path, { method: "POST", body: JSON.stringify(body), headers }),
  patch: (path, body) =>
    request(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: "DELETE" }),
  postRaw: (path, body, contentType) =>
    request(path, {
      method: "POST",
      body,
      headers: { "Content-Type": contentType },
    }),
};