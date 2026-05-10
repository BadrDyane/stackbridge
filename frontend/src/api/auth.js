import { api } from "./client";

export async function login(email, password) {
  const data = await api.post("/auth/login", { email, password });
  localStorage.setItem("sb_token", data.access_token);
  return data;
}

export function logout() {
  localStorage.removeItem("sb_token");
  window.location.href = "/login";
}

export function isLoggedIn() {
  return !!localStorage.getItem("sb_token");
}

export async function getMe() {
  return api.get("/auth/me");
}