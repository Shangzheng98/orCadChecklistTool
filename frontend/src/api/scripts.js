import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

// ── Scripts ─────────────────────────────────────────────────

export function listScripts(params = {}) {
  return api.get('/scripts', { params });
}

export function getScript(scriptId) {
  return api.get(`/scripts/${scriptId}`);
}

export function createScript(data) {
  return api.post('/scripts', data);
}

export function updateScript(scriptId, data) {
  return api.put(`/scripts/${scriptId}`, data);
}

export function deleteScript(scriptId) {
  return api.delete(`/scripts/${scriptId}`);
}

export function publishScript(scriptId) {
  return api.post(`/scripts/${scriptId}/publish`);
}

export function getVersions(scriptId) {
  return api.get(`/scripts/${scriptId}/versions`);
}

// ── Knowledge ───────────────────────────────────────────────

export function listDocs(params = {}) {
  return api.get('/knowledge', { params });
}

export function getDoc(docId) {
  return api.get(`/knowledge/${docId}`);
}

export function createDoc(data) {
  return api.post('/knowledge', data);
}

export function updateDoc(docId, data) {
  return api.put(`/knowledge/${docId}`, data);
}

export function deleteDoc(docId) {
  return api.delete(`/knowledge/${docId}`);
}

// ── AI Agent ────────────────────────────────────────────────

export function agentChat(sessionId, message) {
  return api.post('/agent/chat', { session_id: sessionId, message });
}

export function saveGeneratedScript(data) {
  return api.post('/agent/save', data);
}

// ── Clients ─────────────────────────────────────────────────

export function listClients() {
  return api.get('/clients');
}

export default api;
