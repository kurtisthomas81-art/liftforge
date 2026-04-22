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
};
