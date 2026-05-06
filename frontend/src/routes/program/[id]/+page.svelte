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

  // Post-mesocycle review
  let review = null;
  let showReview = false;
  let acceptedSuggestions = new Set();
  let savingSuggestions = false;

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
    try {
      review = await api.programs.review(meso.id);
      showReview = true;
    } catch {}
    updating = false;
  }

  async function applyLandmarkSuggestion(muscle, suggestion, suggestedMrv, suggestedMev, currentLm) {
    if (!currentLm) return;
    const updated = { ...currentLm, muscle };
    if (suggestion === 'raise_mrv' && suggestedMrv) updated.mrv = suggestedMrv;
    if (suggestion === 'lower_mev' && suggestedMev) updated.mev = suggestedMev;
    try {
      await api.landmarks.update([updated]);
      acceptedSuggestions = new Set([...acceptedSuggestions, muscle]);
    } catch {}
  }

  function rrLabel(muscle) {
    const m = review?.muscles?.find(m => m.muscle === muscle);
    if (!m) return '';
    if (m.avg_rir_early != null && m.avg_rir_late != null) {
      return `RIR ${m.avg_rir_early} → ${m.avg_rir_late}`;
    }
    return '';
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
              <div style="font-weight:600; font-size:14px; color:{ps.completed ? '#4caf6a' : 'var(--text)'}; display:flex; align-items:center; gap:5px; flex-wrap:wrap;">
                {ps.base_session_name ?? ps.split_day_name ?? `Day ${DOW[ps.day_of_week] ?? ps.day_of_week + 1}`}
                {#if ps.variant}
                  <span style="display:inline-block; padding:1px 5px; border-radius:8px; background:rgba(232,160,64,0.18); color:var(--accent); font-size:9px; font-weight:700; line-height:1.5;">{ps.variant}</span>
                {/if}
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
      {@const numWeeks = meso.weeks.length}
      {@const chartW = Math.max(400, numWeeks * 80)}
      {@const chartH = 160}
      {@const padL = 32}
      {@const padB = 24}
      {@const padR = 16}
      {@const padT = 16}
      {@const iW = chartW - padL - padR}
      {@const iH = chartH - padT - padB}
      <div class="card">
        <div class="section-title mb-4">Volume Progression</div>
        <div style="position:relative; overflow-x:auto;">

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

<!-- Post-mesocycle review modal -->
{#if showReview && review}
  <div class="review-backdrop">
    <div class="review-modal">
      <div class="review-hdr">
        <div>
          <div class="review-title">Mesocycle Complete</div>
          <div class="review-sub">{review.name}</div>
        </div>
        <button class="review-close" on:click={() => showReview = false}>✕</button>
      </div>

      <!-- Adherence score -->
      <div class="review-adh">
        <div class="review-adh-num" style="color:{review.adherence.pct >= 80 ? 'var(--success)' : review.adherence.pct >= 50 ? 'var(--warn)' : 'var(--danger)'}">
          {review.adherence.pct}%
        </div>
        <div class="review-adh-lbl">Adherence — {review.adherence.completed} of {review.adherence.planned} sessions</div>
      </div>

      <!-- Per-muscle summary -->
      {#if review.muscles.length}
        <div class="review-section-title">Volume Summary</div>
        <div class="review-muscles">
          {#each review.muscles as m}
            {@const hasSuggestion = m.suggestion && !acceptedSuggestions.has(m.muscle)}
            <div class="review-muscle-row" class:has-suggestion={hasSuggestion}>
              <div class="review-muscle-main">
                <div class="review-muscle-name">{m.muscle}</div>
                <div class="review-muscle-stats">
                  Avg {m.avg_sets_per_week} sets/wk · Peak {m.peak_sets_per_week}
                  {#if m.avg_rir_early != null && m.avg_rir_late != null}
                    · RIR {m.avg_rir_early}→{m.avg_rir_late}
                  {/if}
                </div>
                {#if m.landmark}
                  <div class="review-lm-bar-wrap">
                    <div class="review-lm-mav"
                      style="left:{(m.landmark.mav_low / m.landmark.mrv) * 100}%;width:{((m.landmark.mav_high - m.landmark.mav_low) / m.landmark.mrv) * 100}%">
                    </div>
                    <div class="review-lm-fill"
                      style="width:{Math.min(100, (m.avg_sets_per_week / m.landmark.mrv) * 100)}%;background:{m.avg_sets_per_week > m.landmark.mav_high ? 'var(--warn)' : m.avg_sets_per_week >= m.landmark.mav_low ? 'var(--success)' : 'var(--muted)'}">
                    </div>
                  </div>
                  <div class="review-lm-labels">
                    <span>MEV {m.landmark.mev}</span>
                    <span>MAV {m.landmark.mav_low}–{m.landmark.mav_high}</span>
                    <span>MRV {m.landmark.mrv}</span>
                  </div>
                {/if}
              </div>
              {#if hasSuggestion}
                <div class="review-suggestion">
                  {#if m.suggestion === 'raise_mrv'}
                    <div class="suggest-text">Raise MRV to {m.suggested_mrv}</div>
                  {:else if m.suggestion === 'lower_mev'}
                    <div class="suggest-text">Lower MEV to {m.suggested_mev}</div>
                  {/if}
                  <button class="suggest-btn"
                    on:click={() => applyLandmarkSuggestion(m.muscle, m.suggestion, m.suggested_mrv, m.suggested_mev, m.landmark)}>
                    Apply
                  </button>
                </div>
              {:else if acceptedSuggestions.has(m.muscle)}
                <div class="suggest-accepted">✓ Updated</div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}

      <button class="review-done-btn" on:click={() => { showReview = false; goto('/program/builder'); }}>
        Start New Mesocycle
      </button>
      <button class="review-skip-btn" on:click={() => showReview = false}>
        Close
      </button>
    </div>
  </div>
{/if}

<style>
  .review-backdrop {
    position:fixed; inset:0; background:rgba(0,0,0,0.7);
    z-index:200; display:flex; align-items:flex-end;
  }
  .review-modal {
    width:100%; background:var(--surf);
    border-radius:20px 20px 0 0; padding:24px 20px 40px;
    max-height:90vh; overflow-y:auto;
  }
  .review-hdr { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px; }
  .review-title { font-family:var(--serif); font-size:22px; color:var(--text); }
  .review-sub { font-size:12px; color:var(--muted); margin-top:2px; }
  .review-close { background:none; border:none; font-size:18px; color:var(--muted); cursor:pointer; padding:0; }

  .review-adh { text-align:center; margin-bottom:24px; padding:16px; background:var(--surf-2); border-radius:var(--radius-lg); }
  .review-adh-num { font-family:var(--serif); font-size:48px; line-height:1; }
  .review-adh-lbl { font-size:12px; color:var(--muted); margin-top:4px; }

  .review-section-title {
    font-size:10px; text-transform:uppercase; letter-spacing:0.1em;
    color:var(--muted); font-weight:600; margin-bottom:10px;
  }
  .review-muscles { display:flex; flex-direction:column; gap:10px; margin-bottom:20px; }
  .review-muscle-row {
    background:var(--surf-2); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:12px 14px;
  }
  .review-muscle-row.has-suggestion { border-color:rgba(232,160,54,0.4); }
  .review-muscle-main { flex:1; }
  .review-muscle-name { font-size:13px; font-weight:600; color:var(--text); text-transform:capitalize; }
  .review-muscle-stats { font-size:11px; color:var(--muted); margin-top:2px; }

  .review-lm-bar-wrap {
    position:relative; height:6px; background:var(--faint);
    border-radius:3px; margin-top:8px; overflow:hidden;
  }
  .review-lm-mav {
    position:absolute; top:0; bottom:0;
    background:rgba(34,197,94,0.2); border-radius:3px;
  }
  .review-lm-fill {
    position:absolute; top:0; bottom:0; left:0;
    border-radius:3px; transition:width 0.5s;
  }
  .review-lm-labels {
    display:flex; justify-content:space-between;
    font-size:9px; color:var(--faint); margin-top:3px;
  }

  .review-suggestion {
    display:flex; align-items:center; justify-content:space-between;
    margin-top:10px; padding-top:10px; border-top:1px solid var(--bdr);
  }
  .suggest-text { font-size:11px; color:var(--warn); font-weight:600; }
  .suggest-btn {
    padding:4px 12px; background:rgba(232,160,54,0.15);
    border:1px solid rgba(232,160,54,0.4); border-radius:var(--radius);
    font-size:11px; color:var(--warn); cursor:pointer; transition:all 0.15s;
  }
  .suggest-btn:hover { background:rgba(232,160,54,0.25); }
  .suggest-accepted { font-size:11px; color:var(--success); margin-top:8px; font-weight:600; }

  .review-done-btn {
    width:100%; background:var(--accent); color:#fff; border:none;
    border-radius:var(--radius-lg); padding:16px;
    font-family:var(--serif); font-size:18px; cursor:pointer;
    margin-bottom:8px; transition:background 0.15s;
  }
  .review-done-btn:hover { background:#f05070; }
  .review-skip-btn {
    width:100%; background:transparent; border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:12px;
    font-size:13px; color:var(--muted); cursor:pointer;
  }
</style>
