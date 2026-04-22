<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let meso = null;
  let loading = true;
  let error = null;
  let activeWeek = 1;
  let updating = false;
  let volumeData = null;

  const DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  onMount(async () => {
    const id = $page.params.id;
    try {
      meso = await api.programs.getMesocycle(id);
      activeWeek = meso.current_week;
      volumeData = await api.volume.forMesocycle(id);
    } catch (e) {
      error = e.message;
    }
    loading = false;
  });

  async function markComplete() {
    if (!confirm('Mark this mesocycle as complete?')) return;
    updating = true;
    await api.programs.updateMesocycle(meso.id, { status: 'completed' });
    meso = { ...meso, status: 'completed' };
    updating = false;
  }

  async function abandon() {
    if (!confirm('Abandon this mesocycle?')) return;
    updating = true;
    await api.programs.updateMesocycle(meso.id, { status: 'abandoned' });
    meso = { ...meso, status: 'abandoned' };
    updating = false;
  }

  function goalColor(goal) {
    if (goal === 'strength') return '#5b9bd5';
    if (goal === 'recomp') return '#7cb87c';
    return 'var(--primary)';
  }

  function statusColor(status) {
    if (status === 'completed') return '#4caf6a';
    if (status === 'abandoned') return 'var(--danger)';
    return 'var(--primary)';
  }

  // Volume progression chart data
  const CHART_MUSCLES = ['chest', 'back', 'quads', 'hamstrings', 'shoulders', 'biceps', 'triceps'];
  const MUSCLE_COLORS = {
    chest: '#5b9bd5',
    back: '#7cb87c',
    quads: '#e8a040',
    hamstrings: '#a78bca',
    shoulders: '#4bc9e8',
    biceps: '#e87f4b',
    triceps: '#e84b7f',
  };

  function getVolumeChartData() {
    if (!volumeData) return [];
    return CHART_MUSCLES.map(muscle => ({
      muscle,
      color: MUSCLE_COLORS[muscle] || 'var(--text-muted)',
      data: volumeData.weeks.map(w => w.muscles[muscle] || 0),
    }));
  }

  $: chartData = getVolumeChartData();
  $: maxSets = chartData.length
    ? Math.max(1, ...chartData.flatMap(d => d.data))
    : 1;
</script>

<svelte:head>
  <title>{meso?.name ?? 'Program'} — LiftForge</title>
</svelte:head>

<div style="max-width:900px;">
  {#if loading}
    <div class="flex items-center gap-3" style="padding:32px 0;">
      <div class="spinner"></div>
    </div>

  {:else if error}
    <div class="card" style="color:var(--danger);">{error}</div>

  {:else if meso}
    <!-- Header -->
    <div class="flex items-center gap-3 mb-4" style="flex-wrap:wrap;">
      <a href="/program" class="btn-ghost btn-sm">← Program</a>
      <div style="flex:1;">
        <h2 style="font-size:20px; font-weight:700;">{meso.name}</h2>
        <div style="display:flex; align-items:center; gap:8px; margin-top:4px; flex-wrap:wrap;">
          <span style="background:{goalColor(meso.goal)}22; color:{goalColor(meso.goal)}; border:1px solid {goalColor(meso.goal)}44; border-radius:3px; padding:2px 8px; font-size:11px; font-weight:600; text-transform:capitalize;">
            {meso.goal}
          </span>
          <span style="color:{statusColor(meso.status)}; font-size:12px; text-transform:capitalize;">{meso.status}</span>
          {#if meso.split_name}
            <span style="color:var(--text-muted); font-size:12px;">{meso.split_name}</span>
          {/if}
          {#if meso.start_date}
            <span style="color:var(--text-faint); font-size:12px;">Started {meso.start_date}</span>
          {/if}
        </div>
      </div>
      {#if meso.status === 'active'}
        <div class="flex gap-2">
          <button class="btn-ghost btn-sm" on:click={markComplete} disabled={updating}>
            Mark Complete
          </button>
          <button class="btn-ghost btn-sm" on:click={abandon} disabled={updating}
            style="color:var(--danger); border-color:var(--danger);">
            Abandon
          </button>
        </div>
      {/if}
    </div>

    <!-- Week tabs -->
    <div style="display:flex; gap:4px; margin-bottom:16px; flex-wrap:wrap;">
      {#each meso.weeks as week}
        <button
          on:click={() => activeWeek = week.week_number}
          style="padding:6px 14px; border-radius:4px; border:1px solid {activeWeek === week.week_number ? 'var(--primary)' : 'var(--border)'}; background:{activeWeek === week.week_number ? 'rgba(232,160,64,0.15)' : 'var(--surface-2)'}; color:{activeWeek === week.week_number ? 'var(--primary)' : 'var(--text-muted)'}; font-size:12px; font-weight:{activeWeek === week.week_number ? '700' : '400'}; cursor:pointer; transition:all 0.15s;"
        >
          {week.is_deload ? 'Deload' : `Week ${week.week_number}`}
          {#if week.week_number === meso.current_week && meso.status === 'active'}
            <span style="color:var(--primary); margin-left:4px;">•</span>
          {/if}
        </button>
      {/each}
    </div>

    <!-- Week sessions -->
    {#each meso.weeks.filter(w => w.week_number === activeWeek) as week}
      <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:12px; margin-bottom:24px;">
        {#each week.sessions as ps}
          <div class="card" style="border-color:{ps.completed ? 'rgba(76,175,106,0.3)' : 'var(--border)'};">
            <div class="flex items-center justify-between mb-2">
              <div style="font-weight:600; font-size:14px; color:{ps.completed ? '#4caf6a' : 'var(--text)'};">
                {ps.split_day_name || `Day ${DOW[ps.day_of_week] ?? ps.day_of_week + 1}`}
              </div>
              <span style="font-size:11px; color:var(--text-muted);">{DOW[ps.day_of_week] ?? ''}</span>
            </div>
            {#if ps.completed}
              <div style="font-size:11px; color:#4caf6a; margin-bottom:8px;">Completed</div>
            {/if}
            <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:10px;">
              {#each ps.exercises.slice(0, 5) as ex}
                <div style="font-size:12px; color:var(--text-muted);">
                  {ex.exercise_name}
                  <span style="color:var(--text-faint); font-size:11px;"> {ex.target_sets}×{ex.target_reps_min}-{ex.target_reps_max}</span>
                </div>
              {/each}
              {#if ps.exercises.length > 5}
                <div style="font-size:11px; color:var(--text-faint);">+{ps.exercises.length - 5} more</div>
              {/if}
            </div>
            {#if !ps.completed && week.week_number === meso.current_week && meso.status === 'active'}
              <a href="/planned/{ps.id}" class="btn-primary btn-sm" style="font-size:12px;">
                Start Session →
              </a>
            {:else}
              <a href="/planned/{ps.id}" class="btn-ghost btn-sm" style="font-size:12px;">
                View
              </a>
            {/if}
          </div>
        {/each}
      </div>
    {/each}

    <!-- Volume progression chart -->
    {#if volumeData && meso.weeks.length > 0}
      <div class="card">
        <div class="section-title mb-4">Volume Progression</div>
        <div style="position:relative; overflow-x:auto;">
          <!-- Simple SVG line chart -->
          {@const numWeeks = meso.weeks.length}
          {@const chartW = Math.max(400, numWeeks * 80)}
          {@const chartH = 160}
          {@const padL = 32}
          {@const padB = 24}
          {@const padR = 16}
          {@const padT = 16}
          {@const iW = chartW - padL - padR}
          {@const iH = chartH - padT - padB}

          <svg viewBox="0 0 {chartW} {chartH}" style="width:100%; min-width:{chartW}px; height:{chartH}px; display:block;">
            <!-- Grid lines -->
            {#each [0, 0.25, 0.5, 0.75, 1] as frac}
              <line
                x1={padL} y1={padT + iH * (1 - frac)}
                x2={padL + iW} y2={padT + iH * (1 - frac)}
                stroke="var(--border)" stroke-width="1"
              />
              <text x={padL - 4} y={padT + iH * (1 - frac) + 4} text-anchor="end" font-size="9" fill="var(--text-faint)">
                {Math.round(maxSets * frac)}
              </text>
            {/each}

            <!-- Week labels -->
            {#each meso.weeks as week, wi}
              <text
                x={padL + (wi / Math.max(1, numWeeks - 1)) * iW}
                y={chartH - 4}
                text-anchor="middle"
                font-size="9"
                fill="var(--text-faint)"
              >{week.is_deload ? 'D' : week.week_number}</text>
            {/each}

            <!-- Lines per muscle -->
            {#each chartData as series}
              {@const pts = series.data.map((v, i) => {
                const x = padL + (i / Math.max(1, numWeeks - 1)) * iW;
                const y = padT + iH - (v / maxSets) * iH;
                return `${x},${y}`;
              })}
              {#if series.data.some(v => v > 0)}
                <polyline
                  points={pts.join(' ')}
                  fill="none"
                  stroke={series.color}
                  stroke-width="2"
                  stroke-linejoin="round"
                  stroke-linecap="round"
                  opacity="0.85"
                />
              {/if}
            {/each}
          </svg>
        </div>

        <!-- Legend -->
        <div style="display:flex; flex-wrap:wrap; gap:10px; margin-top:8px;">
          {#each chartData.filter(d => d.data.some(v => v > 0)) as series}
            <span style="display:flex; align-items:center; gap:5px; font-size:11px; color:var(--text-muted);">
              <span style="width:16px; height:2px; background:{series.color}; border-radius:1px; display:inline-block;"></span>
              {series.muscle}
            </span>
          {/each}
        </div>
      </div>
    {/if}
  {/if}
</div>
