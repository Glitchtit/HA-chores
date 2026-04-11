import axios from 'axios';

// Derive ingress base path from current URL — works even if nginx sub_filter
// fails to inject the meta tag. Under HA ingress the pathname is
// /api/hassio_ingress/{token}[/...]; outside HA it is just '/'.
function getIngressPath() {
  const meta = document.querySelector('meta[name="ingress-path"]')?.content;
  if (meta) return meta;
  const match = window.location.pathname.match(/^(\/api\/hassio_ingress\/[^/]+)/);
  return match ? match[1] : '';
}

const INGRESS_PATH = getIngressPath();
const api = axios.create({ baseURL: `${INGRESS_PATH}/api` });

// ── Health ──────────────────────────────────────────────────────────────────
export const getHealth = () => api.get('/health').then(r => r.data);

// ── Chores ──────────────────────────────────────────────────────────────────
export const getChores = (activeOnly = true) =>
  api.get('/chores/', { params: { active_only: activeOnly } }).then(r => r.data);
export const getChore = (id) => api.get(`/chores/${id}`).then(r => r.data);
export const createChore = (data) => api.post('/chores/', data).then(r => r.data);
export const updateChore = (id, data) => api.put(`/chores/${id}`, data).then(r => r.data);
export const deleteChore = (id) => api.delete(`/chores/${id}`);

// ── Assignments / Instances ─────────────────────────────────────────────────
export const getInstances = (params = {}) =>
  api.get('/assignments/', { params }).then(r => r.data);
export const getTodayInstances = (person) =>
  api.get('/assignments/today', { params: person ? { person } : {} }).then(r => r.data);
export const createInstance = (data) => api.post('/assignments/', data).then(r => r.data);
export const claimInstance = (id, personId) =>
  api.post(`/assignments/${id}/claim`, { person_id: personId }).then(r => r.data);
export const completeInstance = (id, completedBy, notes = '') =>
  api.post(`/assignments/${id}/complete`, { completed_by: completedBy, notes }).then(r => r.data);
export const skipInstance = (id) => api.post(`/assignments/${id}/skip`).then(r => r.data);
export const assignInstance = (id, personId) =>
  api.post(`/assignments/${id}/assign`, { person_id: personId }).then(r => r.data);

// ── Persons ─────────────────────────────────────────────────────────────────
export const getPersons = () => api.get('/persons/').then(r => r.data);
export const getMe = () => api.get('/persons/me').then(r => r.data);
export const syncPersons = () => api.post('/persons/sync').then(r => r.data);
export const testNotification = (entityId) =>
  api.post(`/persons/${entityId}/test-notification`).then(r => r.data);

// ── Gamification ────────────────────────────────────────────────────────────
export const getLeaderboard = () => api.get('/gamification/leaderboard').then(r => r.data);
export const getBadges = () => api.get('/gamification/badges').then(r => r.data);
export const getPersonBadges = (entityId) =>
  api.get(`/gamification/person/${entityId}/badges`).then(r => r.data);
export const getPersonStats = (entityId) =>
  api.get(`/gamification/person/${entityId}/stats`).then(r => r.data);

// ── Calendar ────────────────────────────────────────────────────────────────
export const getCalendarEvents = (start, end) =>
  api.get('/calendar/events', { params: { start, end } }).then(r => r.data);

// ── Config ──────────────────────────────────────────────────────────────────
export const getConfig = () => api.get('/config/').then(r => r.data);
export const getConfigValue = (key) => api.get(`/config/${key}`).then(r => r.data);
export const setConfigValue = (key, value) =>
  api.put(`/config/${key}`, { key, value }).then(r => r.data);
