<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let loading = true;
  let activeMeso = null;
  let weekVolume = null;
  let error = null;

  const DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  onMount(async () => {
    try {
      activeMeso = await api.programs.getActiveMesocycle();
      if (activeMeso) {
        weekVolume = await api.volume.forWeek(null);
      }
    } catch (e) {
      error = e.message;
    }
    loading = false;
  });

  function goalBadgeColor(goal) {
    if (goal === 'strength') return '#5b9bd5';
    if (goal === 'recomp') return '#7cb87c';
    return 'var(--primary)';
  }

  function sessionLabel(ps) {
    const today = new Date().getDay(); // 0=Sun, 1=Mon...
    // Convert to Mon=0 basis
    const todayDow = today === 0 ? 6 : today - 1;
    if (ps.session_id) return 'Completed';
    if (ps.day_of_week === todayDow) return 'Today';
    return null;
  }

  function getMavWidth(muscle, volume) {
    if (!volume) return 0;
    const entry = volume.muscles.find(m => m.muscle === muscle);
    if (!entry || !entry.landmarks) return 0;
    const mrv = entry.landmarks.mrv || 25;
    return Math.min(100, (entry.sets / mrv) * 100);
  }

  function getMavRange(muscle, volume) {
    if (!volume) return { start: 0, end: 0 };
    const entry = volume.muscles.find(m => m.muscle === muscle);
    if (!entry || !entry.landmarks) return { start: 0, end: 0 };
    const mrv = entry.landmarks.mrv || 25;
    return {
      start: (entry.landmarks.mav_low / mrv) * 100,
      end: (entry.landmarks.mav_high / mrv) * 100,
    };
  }

  function getBarColor(muscle, volume) {
    if (!volume) return 'var(--text-muted)';
    const entry = volume.muscles.find(m => m.muscle === muscle);
    if (!entry) return 'var(--text-muted)';
    if (entry.status === 'at_mrv') return '#c94040';
    if (entry.status === 'in_mav') return '#4caf6a';
    if (entry.status === 'above_mav') return '#e8a040';
    return 'var(--text-muted)';
  }

  const CHART_MUSCLES = ['chest', 'back', 'quads', 'hamstrings', 'shoulders', 'biceps', 'triceps'];

  let totalSetsThisWeek = 0;
  let completedSessionsThisWeek = 0;
  $: if (activeMeso && activeMeso.current_week_sessions) {
    completedSessionsThisWeek = activeMeso.current_week_sessions.filter(s => s.session_id).length;
  }
  $: if (weekVolume) {
    totalSetsThisWeek = weekVolume.muscles.reduce((sum, m) => sum + m.sets, 0);
  }
</script>

<svelte:head><title>Program — LiftForge</title></svelte:head>

<div style="max-width:900px;">
  <div class="flex items-center justify-between mb-4">
    <h2 style="font-size:20px; font-weight:700;">Program</h2>
    <button class="btn-primary" on:click={() => goto('/program/builder')}>
      + Create Program
    </button>
  </div>

  {#if loading}
    <div class="flex items-center gap-3" style="padding:32px 0;">
      <div class="spinner"></div>
      <span style="color:var(--text-muted);">Loading...</span>
    </div>

  {:else if error}
    <div class="card" style="color:var(--danger);">{error}</div>

  {:else if !activeMeso}
    <div class="card">
      <div class="empty-state">
        <div class="empty-icon">▦</div>
        <p>No active program.</p>
        <p style="color:var(--text-muted); font-size:13px; margin-bottom:16px;">
          Build a structured mesocycle to guide your training with progressive overload.
        </p>
        <button class="btn-primary" on:click={() => goto('/program/builder')}
          style="padding:12px 32px; font-size:15px;">
          Create Program
        </button>
      </div>
    </div>

  {:else}
    <!-- Active mesocycle card -->
    <div class="card mb-4">
      <div class="flex items-center justify-between mb-3" style="flex-wrap:wrap; gap:8px;">
        <div>
          <div style="font-size:17px; font-weight:700;">{activeMeso.name}</div>
          <div style="margin-top:4px; display:flex; align-items:center; gap:8px;">
            <span style="background:{goalBadgeColor(activeMeso.goal)}22; color:{goalBadgeColor(activeMeso.goal)}; border:1px solid {goalBadgeColor(activeMeso.goal)}44; border-radius:3px; padding:2px 8px; font-size:11px; font-weight:600; text-transform:capitalize;">
              {activeMeso.goal}
            </span>
            {#if activeMeso.split_name}
              <span style="color:var(--text-muted); font-size:12px;">{activeMeso.split_name}</span>
            {/if}
          </div>
        </div>
        <a href="/program/{activeMeso.id}" class="btn-ghost btn-sm">View Details</a>
      </div>

      <!-- Week progress bar -->
      <div style="margin-bottom:4px;">
        <div class="flex justify-between" style="font-size:12px; color:var(--text-muted); margin-bottom:6px;">
          <span>Week {activeMeso.current_week} of {activeMeso.weeks_total}</span>
          {#if activeMeso.current_week_is_deload}
            <span style="color:var(--primary);">Deload Week</span>
          {/if}
        </div>
        <div style="background:var(--surface-2); border-radius:4px; height:6px; overflow:hidden;">
          <div style="background:var(--primary); height:100%; width:{(activeMeso.current_week / activeMeso.weeks_total) * 100}%; border-radius:4px; transition:width 0.3s;"></div>
        </div>
      </div>
    </div>

    <!-- This week's training grid -->
    <div class="card mb-4">
      <div class="section-title mb-3">This Week</div>
      <div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:6px;">
        {#each DOW as day, i}
          {@const ps = activeMeso.current_week_sessions?.find(s => s.day_of_week === i)}
          <div style="text-align:center;">
            <div style="font-size:11px; color:var(--text-faint); margin-bottom:4px;">{day}</div>
            {#if ps}
              {@const label = sessionLabel(ps)}
              <a
                href="/planned/{ps.id}"
                style="display:block; padding:8px 4px; background:{ps.session_id ? 'rgba(76,175,106,0.12)' : label === 'Today' ? 'rgba(232,160,64,0.12)' : 'var(--surface-2)'}; border:1px solid {ps.session_id ? 'rgba(76,175,106,0.3)' : label === 'Today' ? 'rgba(232,160,64,0.4)' : 'var(--border)'}; border-radius:6px; text-decoration:none; transition:border-color 0.15s;"
              >
                <div style="font-size:11px; font-weight:600; color:{ps.session_id ? '#4caf6a' : label === 'Today' ? 'var(--primary)' : 'var(--text)'}; word-break:break-word; line-height:1.3;">
                  {ps.split_day_name || 'Training'}
                </div>
                {#if label}
                  <div style="font-size:10px; margin-top:3px; color:{ps.session_id ? '#4caf6a' : 'var(--primary)'};">
                    {label}
                  </div>
                {/if}
              </a>
            {:else}
              <div style="padding:8px 4px; background:var(--surface-2); border:1px solid var(--border); border-radius:6px; opacity:0.4;">
                <div style="font-size:11px; color:var(--text-faint);">Rest</div>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    </div>

    <!-- Quick stats -->
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
      <div class="card" style="text-align:center;">
        <div style="font-size:28px; font-weight:700; color:var(--primary);">{completedSessionsThisWeek}</div>
        <div style="font-size:12px; color:var(--text-muted);">Sessions this week</div>
      </div>
      <div class="card" style="text-align:center;">
        <div style="font-size:28px; font-weight:700; color:var(--primary);">{totalSetsThisWeek}</div>
        <div style="font-size:12px; color:var(--text-muted);">Total sets this week</div>
      </div>
    </div>

    <!-- Weekly volume chart -->
    {#if weekVolume}
      <div class="card">
        <div class="section-title mb-3">Weekly Volume</div>
        <div style="display:flex; flex-direction:column; gap:10px;">
          {#each CHART_MUSCLES as muscle}
            {@const entry = weekVolume.muscles.find(m => m.muscle === muscle)}
            {@const sets = entry?.sets ?? 0}
            {@const lm = entry?.landmarks}
            {@const mrv = lm?.mrv ?? 25}
            {@const mavRange = getMavRange(muscle, weekVolume)}
            <div>
              <div class="flex justify-between" style="font-size:12px; margin-bottom:4px;">
                <span style="text-transform:capitalize; color:var(--text);">{muscle}</span>
                <span style="color:var(--text-muted);">{sets} sets{lm ? ` / ${mrv} MRV` : ''}</span>
              </div>
              <div style="position:relative; background:var(--surface-2); border-radius:3px; height:14px; overflow:hidden;">
                <!-- MAV range band (green background) -->
                {#if lm}
                  <div style="position:absolute; top:0; bottom:0; left:{mavRange.start}%; width:{mavRange.end - mavRange.start}%; background:rgba(76,175,106,0.15);"></div>
                  <!-- MRV line -->
                  <div style="position:absolute; top:0; bottom:0; left:calc(100% - 2px); width:2px; background:rgba(201,64,64,0.5);"></div>
                {/if}
                <!-- Sets bar -->
                <div style="position:absolute; top:0; bottom:0; left:0; width:{Math.min(100, (sets / mrv) * 100)}%; background:{getBarColor(muscle, weekVolume)}; border-radius:3px; transition:width 0.3s;"></div>
              </div>
            </div>
          {/each}
        </div>
        <div style="display:flex; gap:16px; margin-top:12px; font-size:11px; color:var(--text-faint);">
          <span style="display:flex; align-items:center; gap:4px;"><span style="width:10px; height:10px; background:rgba(76,175,106,0.3); border-radius:1px; display:inline-block;"></span> MAV range</span>
          <span style="display:flex; align-items:center; gap:4px;"><span style="width:2px; height:10px; background:rgba(201,64,64,0.7); display:inline-block;"></span> MRV</span>
        </div>
      </div>
    {/if}
  {/if}
</div>
