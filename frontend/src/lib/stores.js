import { writable, derived } from 'svelte/store';
import { api } from './api.js';

// Active session — null if none
export const activeSession = writable(null);

// User profile
export const userProfile = writable(null);

export async function refreshActiveSession() {
  try {
    const s = await api.sessions.active();
    activeSession.set(s);
  } catch {
    activeSession.set(null);
  }
}

export async function refreshProfile() {
  try {
    const p = await api.profile.get();
    userProfile.set(p);
  } catch {
    userProfile.set(null);
  }
}

// Generated session plan — set by home page, consumed by log page
export const sessionPlan = writable(null);

// Autoregulation hints — set by planned/[id] before navigating to /log
export const arHints = writable({});

// Elapsed time for active session
export function getElapsed(startedAt) {
  if (!startedAt) return '0:00';
  const start = new Date(startedAt + 'Z'); // treat as UTC
  const now = new Date();
  const diff = Math.floor((now - start) / 1000);
  const h = Math.floor(diff / 3600);
  const m = Math.floor((diff % 3600) / 60);
  const s = diff % 60;
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }
  return `${m}:${String(s).padStart(2, '0')}`;
}
