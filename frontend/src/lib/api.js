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
    swapExercise: (sessionId, oldId, newId) =>
      request('POST', `/sessions/${sessionId}/swap-exercise`, { old_exercise_id: oldId, new_exercise_id: newId }),
    pairExercises: (sessionId, exerciseIds) =>
      request('POST', `/sessions/${sessionId}/pair-exercises`, { exercise_ids: exerciseIds }),
    unpairExercises: (sessionId, group) =>
      request('DELETE', `/sessions/${sessionId}/pair-exercises/${group}`),
  },

  history: {
    recent: () => request('GET', '/history'),
    exerciseProgression: (id) => request('GET', `/history/exercise/${id}`),
    lastSession: (id) => request('GET', `/history/exercise/${id}/last-session`),
    calendar: (year, month) => request('GET', `/history/calendar?year=${year}&month=${month}`),
    search: (q) => request('GET', `/history/search?q=${encodeURIComponent(q)}`),
  },

  profile: {
    get: () => request('GET', '/profile'),
    update: (data) => request('PUT', '/profile', data),
    updateEquipment: (equipment) =>
      request('PUT', '/profile/equipment', { equipment }),
    strengthLevel: () => request('GET', '/profile/strength-level'),
  },

  chat: {
    send: (message, context_type = 'general') =>
      request('POST', '/chat', { message, context_type }),
  },

  programs: {
    getSplits: () => request('GET', '/programs/splits'),
    getSplit: (slug) => request('GET', `/programs/splits/${slug}`),
    previewMesocycle: (data) => request('POST', '/programs/mesocycles/preview', data),
    validateSlots: (data) => request('POST', '/programs/mesocycles/validate-slots', data),
    previewCustomSlots: (data) => request('POST', '/programs/mesocycles/preview-custom-slots', data),
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
    adherence: (id) => request('GET', `/programs/mesocycles/${id}/adherence`),
    review: (id) => request('GET', `/programs/mesocycles/${id}/review`),
    listLibrary: () => request('GET', '/programs/library'),
    previewLibraryProgram: (slug) => request('GET', `/programs/library/${slug}/preview`),
    installLibraryProgram: (slug, config = {}) => request('POST', `/programs/library/${slug}/install`, config),
  },

  landmarks: {
    get: () => request('GET', '/landmarks'),
    update: (data) => request('PUT', '/landmarks', data),
    forGoal: (goal) => request('GET', `/landmarks/${goal}`),
  },

  volume: {
    forSession: (sessionId) => request('GET', `/volume/session/${sessionId}`),
    forWeek: (date) => request('GET', `/volume/week${date ? '?date=' + date : ''}`),
    forMesocycle: (id) => request('GET', `/volume/mesocycle/${id}`),
    allTime: (weeks = 52) => request('GET', `/volume/alltime?weeks=${weeks}`),
    fatigueReport: () => request('GET', '/volume/fatigue-report'),
  },

  prs: {
    getAll: () => request('GET', '/prs'),
    forExercise: (exerciseId) => request('GET', `/prs/exercise/${exerciseId}`),
    checkSession: (sessionId) => request('POST', `/prs/check/${sessionId}`),
  },

  templates: {
    list: () => request('GET', '/templates'),
    get: (id) => request('GET', `/templates/${id}`),
    create: (data) => request('POST', '/templates', data),
    update: (id, data) => request('PUT', `/templates/${id}`, data),
    delete: (id) => request('DELETE', `/templates/${id}`),
    start: (id) => request('POST', `/templates/${id}/start`),
    saveFromSession: (sessionId, name) =>
      request('POST', `/sessions/${sessionId}/save-as-template`, { name }),
    generate: () => request('POST', '/sessions/generate'),
  },

  measurements: {
    list: () => request('GET', '/measurements'),
    latest: () => request('GET', '/measurements/latest'),
    create: (data) => request('POST', '/measurements', data),
    update: (id, data) => request('PUT', `/measurements/${id}`, data),
    delete: (id) => request('DELETE', `/measurements/${id}`),
  },

  recovery: {
    getMap: () => request('GET', '/recovery-map'),
    checkinStatus: () => request('GET', '/recovery/checkin/status'),
    submitCheckin: (data) => request('POST', '/recovery/checkin', data),
  },

  goals: {
    list: () => request('GET', '/goals'),
    create: (data) => request('POST', '/goals', data),
    delete: (id) => request('DELETE', `/goals/${id}`),
  },

  injuries: {
    list: () => request('GET', '/injuries'),
    create: (data) => request('POST', '/injuries', data),
    delete: (id) => request('DELETE', `/injuries/${id}`),
    affectedExercises: () => request('GET', '/injuries/affected-exercises'),
  },
};
