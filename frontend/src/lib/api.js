const BASE = '/api';

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${method} ${path} → ${res.status}: ${text}`);
  }
  // 204 No Content
  if (res.status === 204) return null;
  return res.json();
}

// Exercises
export const api = {
  exercises: {
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request('GET', `/exercises${qs ? '?' + qs : ''}`);
    },
    get: (id) => request('GET', `/exercises/${id}`),
    create: (data) => request('POST', '/exercises', data),
    history: (id) => request('GET', `/exercises/${id}/history`),
  },

  sessions: {
    list: (page = 1) => request('GET', `/sessions?page=${page}`),
    active: () => request('GET', '/sessions/active'),
    get: (id) => request('GET', `/sessions/${id}`),
    create: (data) => request('POST', '/sessions', data),
    update: (id, data) => request('PATCH', `/sessions/${id}`, data),
    finish: (id) => request('POST', `/sessions/${id}/finish`),
    addSet: (id, data) => request('POST', `/sessions/${id}/sets`, data),
    updateSet: (sessionId, setId, data) =>
      request('PUT', `/sessions/${sessionId}/sets/${setId}`, data),
    deleteSet: (sessionId, setId) =>
      request('DELETE', `/sessions/${sessionId}/sets/${setId}`),
  },

  history: {
    recent: () => request('GET', '/history'),
    exerciseProgression: (id) => request('GET', `/history/exercise/${id}`),
    lastSession: (id) => request('GET', `/history/exercise/${id}/last-session`),
  },

  profile: {
    get: () => request('GET', '/profile'),
    update: (data) => request('PUT', '/profile', data),
    updateEquipment: (equipment) =>
      request('PUT', '/profile/equipment', { equipment }),
  },

  chat: {
    send: (message, context_type = 'general') =>
      request('POST', '/chat', { message, context_type }),
  },

  programs: {
    getSplits: () => request('GET', '/programs/splits'),
    getSplit: (slug) => request('GET', `/programs/splits/${slug}`),
    createMesocycle: (data) => request('POST', '/programs/mesocycles', data),
    listMesocycles: () => request('GET', '/programs/mesocycles'),
    getActiveMesocycle: () => request('GET', '/programs/mesocycles/active'),
    getMesocycle: (id) => request('GET', `/programs/mesocycles/${id}`),
    updateMesocycle: (id, data) => request('PATCH', `/programs/mesocycles/${id}`, data),
    advanceMesocycle: (id) => request('POST', `/programs/mesocycles/${id}/advance`),
    getPlannedSession: (id) => request('GET', `/programs/planned/${id}`),
    updatePlannedExercises: (id, exercises) =>
      request('PUT', `/programs/planned/${id}/exercises`, exercises),
    startPlannedSession: (id) => request('POST', `/programs/planned/${id}/start`),
  },

  landmarks: {
    get: () => request('GET', '/landmarks'),
    update: (data) => request('PUT', '/landmarks', data),
  },

  volume: {
    forSession: (sessionId) => request('GET', `/volume/session/${sessionId}`),
    forWeek: (date) => request('GET', `/volume/week${date ? '?date=' + date : ''}`),
    forMesocycle: (id) => request('GET', `/volume/mesocycle/${id}`),
    allTime: (weeks = 52) => request('GET', `/volume/alltime?weeks=${weeks}`),
  },

  prs: {
    getAll: () => request('GET', '/prs'),
    forExercise: (exerciseId) => request('GET', `/prs/exercise/${exerciseId}`),
    checkSession: (sessionId) => request('POST', `/prs/check/${sessionId}`),
  },
};
