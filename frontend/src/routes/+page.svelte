<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { activeSession, refreshActiveSession, getElapsed } from '$lib/stores.js';
  import { formatDate, autoSessionName } from '$lib/utils.js';

  let recentSessions = [];
  let loading = true;
  let elapsed = '0:00';
  let creating = false;

  let weekSessions = 0;
  let weekVolume = 0;

  onMount(async () => {
    await refreshActiveSession();
    try {
      const sessions = await api.history.recent();
      // Last 5 for dashboard
      recentSessions = sessions.slice(0, 5);

      // Week stats
      const now = new Date();
      const weekStart = new Date(now);
      weekStart.setDate(now.getDate() - now.getDay());
      weekStart.setHours(0, 0, 0, 0);

      const allSessions = await api.sessions.list(1);
      weekSessions = allSessions.filter(s => s.completed_at && new Date(s.started_at) >= weekStart).length;

      // Rough weekly volume from history summaries (set_count as proxy)
      const weekData = sessions.filter(s => s.started_at && new Date(s.started_at) >= weekStart);
      weekVolume = weekData.reduce((acc, s) => acc + s.set_count, 0);
    } catch (e) {
      console.error(e);
    }
    loading = false;
  });

  // Update elapsed every second when session is active
  $: if ($activeSession) {
    elapsed = getElapsed($activeSession.started_at);
  }

  async function startSession() {
    creating = true;
    try {
      const s = await api.sessions.create({ name: autoSessionName() });
      await refreshActiveSession();
      goto('/log');
    } catch (e) {
      console.error(e);
    }
    creating = false;
  }
</script>

<svelte:head><title>Dashboard — LiftForge</title></svelte:head>

<div style="max-width: 800px;">
  <div class="flex items-center justify-between mb-4">
    <h2 style="font-size:20px; font-weight:700;">Dashboard</h2>
  </div>

  <!-- Active session card or start button -->
  {#if $activeSession}
    <div class="card mb-4" style="border-color: rgba(232,160,64,0.3); background: rgba(232,160,64,0.05);">
      <div class="flex items-center justify-between">
        <div>
          <div style="color: var(--primary); font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:4px;">
            Session Active
          </div>
          <div style="font-size:16px; font-weight:600;">{$activeSession.name || 'Unnamed Session'}</div>
          <div style="color: var(--text-muted); font-size:13px; margin-top:2px;">{elapsed} elapsed</div>
        </div>
        <a href="/log" class="btn-primary" style="padding:10px 20px; border-radius:4px; font-weight:600; color:#000; background:var(--primary); text-decoration:none;">
          Continue
        </a>
      </div>
    </div>
  {:else}
    <div class="card mb-4">
      <div class="empty-state" style="padding: 24px;">
        <div style="font-size:14px; color:var(--text-muted); margin-bottom:16px;">No active session</div>
        <button class="btn-primary" on:click={startSession} disabled={creating} style="padding:12px 32px; font-size:15px;">
          {creating ? 'Starting...' : 'Start Workout'}
        </button>
      </div>
    </div>
  {/if}

  <!-- Week stats -->
  <div class="flex gap-3 mb-4">
    <div class="card" style="flex:1; text-align:center;">
      <div style="font-size:28px; font-weight:700; color:var(--primary);">{weekSessions}</div>
      <div style="color:var(--text-muted); font-size:12px; margin-top:2px;">Sessions this week</div>
    </div>
    <div class="card" style="flex:1; text-align:center;">
      <div style="font-size:28px; font-weight:700; color:var(--primary);">{weekVolume}</div>
      <div style="color:var(--text-muted); font-size:12px; margin-top:2px;">Sets this week</div>
    </div>
  </div>

  <!-- Recent sessions -->
  <div class="section-title">Recent Sessions</div>

  {#if loading}
    <div class="flex items-center gap-3" style="padding:24px 0;">
      <div class="spinner"></div>
      <span style="color:var(--text-muted);">Loading...</span>
    </div>
  {:else if recentSessions.length === 0}
    <div class="card">
      <div class="empty-state" style="padding:24px;">
        <p style="color:var(--text-muted);">No completed sessions yet. Start lifting!</p>
      </div>
    </div>
  {:else}
    <div style="display:flex; flex-direction:column; gap:8px;">
      {#each recentSessions as s}
        <a href="/history" class="card" style="display:block; text-decoration:none; color:inherit; transition: border-color 0.15s;"
           on:mouseenter={e => e.currentTarget.style.borderColor='var(--border-2)'}
           on:mouseleave={e => e.currentTarget.style.borderColor='var(--border)'}>
          <div class="flex items-center justify-between">
            <div>
              <div style="font-weight:600; font-size:14px;">{s.name || 'Unnamed Session'}</div>
              <div style="color:var(--text-muted); font-size:12px; margin-top:2px;">
                {formatDate(s.started_at)} · {s.set_count} sets
              </div>
            </div>
            <div class="flex gap-2" style="flex-wrap:wrap; justify-content:flex-end; max-width:200px;">
              {#each (s.muscles || []).slice(0, 4) as m}
                <span class="tag">{m}</span>
              {/each}
            </div>
          </div>
        </a>
      {/each}
    </div>
  {/if}
</div>
