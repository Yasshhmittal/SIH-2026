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
  if (!res.ok) throw new Error(await errorDetail(res, `POST ${path}`));
  return res.json();
}

export async function apiDelete(path) {
  const res = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await errorDetail(res, `DELETE ${path}`));
  return res.json();
}

/**
 * Surface FastAPI's `detail` message instead of a bare status code.
 * An upload rejected for being the wrong type should say so.
 */
async function errorDetail(res, prefix) {
  try {
    const body = await res.json();
    if (body?.detail) return `${body.detail}`;
  } catch {
    // not JSON — fall through to the status line
  }
  return `${prefix}: ${res.status}`;
}

/**
 * Upload a document and index it. Returns { uploaded, ingest, kb }.
 * Uses multipart/form-data, so Content-Type is set by the browser.
 */
export async function uploadDocument(file, orgId = "mrpl") {
  const form = new FormData();
  form.append("file", file);
  form.append("org_id", orgId);
  form.append("embed", "false");

  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await errorDetail(res, "upload"));
  return res.json();
}

export function listDocuments(orgId = "mrpl") {
  return apiGet(`/api/documents?org_id=${encodeURIComponent(orgId)}`);
}

export function deleteDocument(docId, orgId = "mrpl") {
  return apiDelete(
    `/api/documents/${encodeURIComponent(docId)}?org_id=${encodeURIComponent(orgId)}`
  );
}

export function searchDocuments(query, orgId = "mrpl", k = 6) {
  return apiPost("/api/documents/search", { query, org_id: orgId, k });
}

export function sseUrl(runId) {
  return `${API_BASE}/api/runs/${runId}/events`;
}
