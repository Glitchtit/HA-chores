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
export const assignInstance = (id, personId, assignedBy = null) =>
  api.post(`/assignments/${id}/assign`, { person_id: personId, assigned_by: assignedBy }).then(r => r.data);

// ── Persons ─────────────────────────────────────────────────────────────────
export const getPersons = () => api.get('/persons/').then(r => r.data);
export const getMe = () => api.get('/persons/me').then(r => r.data);
export const syncPersons = () => api.post('/persons/sync').then(r => r.data);
export const testNotification = (entityId) =>
  api.post(`/persons/${entityId}/test-notification`).then(r => r.data);
export const resetPersonProgress = (entityId) =>
  api.post(`/persons/${entityId}/reset-progress`).then(r => r.data);

// ── Gamification ────────────────────────────────────────────────────────────
export const getLeaderboard = () => api.get('/gamification/leaderboard').then(r => r.data);
export const getBadges = () => api.get('/gamification/badges').then(r => r.data);
export const getPersonBadges = (entityId) =>
  api.get(`/gamification/person/${entityId}/badges`).then(r => r.data);
export const getPersonStats = (entityId) =>
  api.get(`/gamification/person/${entityId}/stats`).then(r => r.data);
export const getMonthEndCheck = (entityId) =>
  api.get(`/gamification/month-end-check/${entityId}`).then(r => r.data);
export const markMonthEndSeen = (entityId) =>
  api.post(`/gamification/month-end-seen/${entityId}`).then(r => r.data);

// ── Calendar ────────────────────────────────────────────────────────────────
export const getCalendarEvents = (start, end) =>
  api.get('/calendar/events', { params: { start, end } }).then(r => r.data);

// ── Power-ups ───────────────────────────────────────────────────────────────
export const getActivePowerups = (entityId) =>
  api.get(`/powerups/${entityId}`).then(r => r.data);
export const discardPowerup = (powerupId) =>
  api.delete(`/powerups/${powerupId}`);

// ── Pets ────────────────────────────────────────────────────────────────────
export const getMyPet = () => api.get('/pets/me').then(r => r.data);
export const getHouseholdPets = () => api.get('/pets/').then(r => r.data);
export const setPetEmoji = (entityId, emoji) =>
  api.put(`/pets/${entityId}/emoji`, { emoji }).then(r => r.data);
export const setPetDesign = (entityId, design) =>
  api.put(`/pets/${entityId}/design`, { design }).then(r => r.data);
export const setPetName = (entityId, name) =>
  api.put(`/pets/${entityId}/name`, { name }).then(r => r.data);
export const getLayout = () => api.get('/pets/layout').then(r => r.data);
export const saveLayout = (layout) => api.put('/pets/layout', layout).then(r => r.data);
export const deleteLayout = () => api.delete('/pets/layout').then(r => r.data);
export const getSunState = () => api.get('/pets/sun').then(r => r.data);

// ── Config ──────────────────────────────────────────────────────────────────
export const getConfig = () => api.get('/config/').then(r => r.data);
export const getConfigValue = (key) =>
  api.get(`/config/${encodeURIComponent(key)}`).then(r => r.data);
export const setConfigValue = (key, value) =>
  api.put(`/config/${encodeURIComponent(key)}`, { key, value }).then(r => r.data);

// ── Pending celebrations (cross-app completions) ────────────────────────────
export const getPendingCelebrations = () =>
  api.get('/persons/me/pending-celebrations').then(r => r.data);

export const ackPendingCelebrations = (ids) =>
  api.post('/persons/me/pending-celebrations/ack', { ids }).then(r => r.data);

// ── Cosmetics shop (v0.4.3) ─────────────────────────────────────────────────
export const getCosmeticCatalog = () => api.get('/cosmetics/').then(r => r.data);
export const getMyCosmetics = (entityId) =>
  api.get(`/cosmetics/${entityId}`).then(r => r.data);
export const purchaseCosmetic = (entityId, cosmeticId) =>
  api.post(`/cosmetics/${entityId}/purchase`, { cosmetic_id: cosmeticId }).then(r => r.data);
export const equipCosmetic = (entityId, cosmeticId) =>
  api.post(`/cosmetics/${entityId}/equip`, { cosmetic_id: cosmeticId }).then(r => r.data);
export const unequipCosmetic = (entityId, slot) =>
  api.post(`/cosmetics/${entityId}/unequip`, { slot }).then(r => r.data);

// ── Placed nameplates (v0.7.0) ──────────────────────────────────────────────
export const getPlacedNameplates = () =>
  api.get('/cosmetics/nameplates/placed').then(r => r.data);
export const placeNameplate = (entityId, cosmeticId, x, y) =>
  api.put(`/cosmetics/nameplates/placed/${entityId}`, { cosmetic_id: cosmeticId, x, y }).then(r => r.data);
export const removeNameplate = (entityId) =>
  api.delete(`/cosmetics/nameplates/placed/${entityId}`).then(r => r.data);

// ── Class specialization (v0.4.4) ────────────────────────────────────────────
export const getClassCatalog = () => api.get('/classes/').then(r => r.data);
export const setPersonClass = (entityId, classId) =>
  api.post(`/classes/persons/${entityId}`, { class_id: classId }).then(r => r.data);

// ── Daily quests (v0.4.5) ────────────────────────────────────────────────────
export const getDailyQuests = (entityId) =>
  api.get(`/quests/today/${entityId}`).then(r => r.data);
export const getQuestHistory = (entityId, since) =>
  api.get(`/quests/${entityId}`, { params: since ? { since } : {} }).then(r => r.data);

// ── Household challenges (v0.4.6) ────────────────────────────────────────────
export const getActiveChallenge = () =>
  api.get('/challenges/active').then(r => r.data);
export const getChallengeHistory = (limit = 20) =>
  api.get('/challenges/', { params: { limit } }).then(r => r.data);
export const createChallenge = (data) =>
  api.post('/challenges/', data).then(r => r.data);
export const cancelChallenge = (id) =>
  api.delete(`/challenges/${id}`).then(r => r.data);

// ── Seasonal boss chores (v0.5.0) ────────────────────────────────────────────
export const getActiveBoss = () =>
  api.get('/bosses/active').then(r => r.data);
export const listBosses = () =>
  api.get('/bosses/').then(r => r.data);
export const createBoss = (data) =>
  api.post('/bosses/', data).then(r => r.data);
export const updateBoss = (id, data) =>
  api.put(`/bosses/${id}`, data).then(r => r.data);
export const cancelBoss = (id) =>
  api.delete(`/bosses/${id}`).then(r => r.data);
