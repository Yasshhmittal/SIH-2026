/**
 * API client for the PRAHARI backend.
 * All calls go to 127.0.0.1:8077 — there is no external endpoint.
 */

const API_BASE = "http://127.0.0.1:8077";

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
  return res.json();
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
  return res.json();
}

export function sseUrl(runId) {
  return `${API_BASE}/api/runs/${runId}/events`;
}
