<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '$lib/api.js';
  import { formatDate, epley1RM } from '$lib/utils.js';
  import { Chart, registerables } from 'chart.js';
  Chart.register(...registerables);

  let sessions = [];
  let loading = true;
  let page = 1;
  let hasMore = true;
  let expandedId = null;
  let expandedDetail = null;
  let loadingDetail = false;

  // Progression chart
  let exercises = [];
  let selectedExercise = null;
  let progressionData = [];
  let chart = null;
  let chartCanvas;
  let loadingChart = false;

  // Month summary stats
  let monthSessions = 0;
  let monthSets = 0;
  let monthDuration = 0;

  onMount(async () => {
    await loadPage();
    exercises = await api.exercises.list();
    loading = false;
    computeMonthStats();
  });

  onDestroy(() => { if (chart) chart.destroy(); });

  async function loadPage() {
    const data = await api.sessions.list(page);
    const completed = data.filter(s => s.completed_at);
    sessions = [...sessions, ...completed];
    hasMore = data.length === 20;
  }

  async function loadMore() { page++; await loadPage(); }

  function computeMonthStats() {
    const now = new Date();
    const ms = sessions.filter(s => {
      if (!s.started_at) return false;
      const d = new Date(s.started_at);
      return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
    });
    monthSessions = ms.length;
    monthDuration = ms.reduce((a, s) => {
      if (!s.started_at || !s.completed_at) return a;
      return a + (new Date(s.completed_at) - new Date(s.started_at)) / 60000;
    }, 0);
  }

  async function toggleExpand(id) {
    if (expandedId === id) { expandedId = null; expandedDetail = null; return; }
    expandedId = id;
    loadingDetail = true;
    expandedDetail = await api.sessions.get(id);
    loadingDetail = false;
  }

  async function loadChart(exerciseId) {
    if (!exerciseId) { progressionData = []; destroyChart(); return; }
    loadingChart = true;
    progressionData = await api.history.exerciseProgression(exerciseId);
    loadingChart = false;
    await drawChart();
  }

  $: if (selectedExercise !== null) loadChart(selectedExercise);

  async function drawChart() {
    await new Promise(r => setTimeout(r, 0));
    if (!chartCanvas || !progressionData.length) { destroyChart(); return; }
    destroyChart();
    chart = new Chart(chartCanvas, {
      type: 'line',
      data: {
        labels: progressionData.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
        datasets: [{
          label: 'Est. 1RM',
          data: progressionData.map(d => d.estimated_1rm),
          borderColor: '#e8365d',
          backgroundColor: 'rgba(232,54,93,0.08)',
          borderWidth: 2,
          pointBackgroundColor: '#e8365d',
          pointRadius: 4,
          tension: 0.3,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#6868a0', font: { size: 11 } } },
          tooltip: { backgroundColor: '#12121a', borderColor: '#22222e', borderWidth: 1, titleColor: '#f8f8ff', bodyColor: '#6868a0' },
        },
        scales: {
          x: { ticks: { color: '#6868a0', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.03)' } },
          y: { ticks: { color: '#6868a0', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.03)' } },
        },
      },
    });
  }

  function destroyChart() { if (chart) { chart.destroy(); chart = null; } }

  function sessionDuration(s) {
    if (!s.started_at || !s.completed_at) return '';
    const m = Math.round((new Date(s.completed_at) - new Date(s.started_at)) / 60000);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    const rem = m % 60;
    return rem > 0 ? `${h}h ${rem}m` : `${h}h`;
  }

  function sessionDot(s) {
    const muscles = (s.muscles || []).map(m => m.toLowerCase());
    const lower = ['quads','hamstrings','glutes','calves'];
    const hasLower = muscles.some(m => lower.includes(m));
    const hasUpper = muscles.some(m => !lower.includes(m) && m !== 'abs' && m !== 'core');
    if (hasLower && hasUpper) return 'var(--success)';
    if (hasLower) return 'var(--push)';
    if (hasUpper) return 'var(--warn)';
    return 'var(--squat)';
  }

  async function repeatSession(s) {
    try {
      const detail = await api.sessions.get(s.id);
      const newS = await api.sessions.create({ name: s.name });
      for (const group of (detail.exercises || [])) {
        for (const ws of group.sets) {
          await api.sessions.addSet(newS.id, {
            exercise_id: ws.exercise_id,
            set_number: ws.set_number,
            weight: ws.weight,
            reps: ws.reps,
            rir: ws.rir,
            set_type: ws.set_type,
          });
        }
      }
      window.location.href = '/log';
    } catch {}
  }

  async function saveAsTemplate(s) {
    const name = prompt('Template name:', s.name || '');
    if (!name) return;
    try {
      await api.templates.saveFromSession(s.id, name);
      alert('Template saved!');
    } catch {}
  }

  async function deleteSession(s) {
    if (!confirm(`Delete "${s.name || 'this session'}"? This cannot be undone.`)) return;
    try {
      await api.sessions.delete(s.id);
      sessions = sessions.filter(x => x.id !== s.id);
      if (expandedId === s.id) { expandedId = null; expandedDetail = null; }
      computeMonthStats();
    } catch {}
  }
</script>

<svelte:head><title>History — LiftForge</title></svelte:head>

<!-- Page title -->
<div class="page-title">Session <em>History</em></div>

<!-- Month summary stats -->
<div class="month-grid">
  <div class="month-stat">
    <div class="month-val">{monthSessions}</div>
    <div class="month-lbl">This month</div>
  </div>
  <div class="month-stat">
    <div class="month-val">{sessions.length}</div>
    <div class="month-lbl">All time</div>
  </div>
  <div class="month-stat">
    <div class="month-val">{Math.round(monthDuration / Math.max(monthSessions, 1))}</div>
    <div class="month-lbl">Avg min</div>
  </div>
  <div class="month-stat">
    <div class="month-val">{Math.round(monthDuration)}</div>
    <div class="month-lbl">Min trained</div>
  </div>
</div>

<!-- Progression chart -->
<div class="card prog-card">
  <div class="section-title">Exercise Progression</div>
  <select bind:value={selectedExercise} class="ex-select">
    <option value={null}>Select exercise…</option>
    {#each exercises as ex}
      <option value={ex.id}>{ex.name}</option>
    {/each}
  </select>
  {#if loadingChart}
    <div class="chart-placeholder"><div class="spinner"></div></div>
  {:else if selectedExercise && !progressionData.length}
    <div class="chart-placeholder" style="color:var(--muted);font-size:13px;">No data yet.</div>
  {:else if selectedExercise}
    <div class="chart-wrap"><canvas bind:this={chartCanvas}></canvas></div>
  {:else}
    <div class="chart-placeholder" style="color:var(--faint);font-size:12px;">Select an exercise to see 1RM trend</div>
  {/if}
</div>

<!-- Session list -->
<div class="section-title mt-4">Past Sessions</div>

{#if loading}
  <div class="flex items-center gap-3" style="padding:24px 0;"><div class="spinner"></div></div>
{:else if sessions.length === 0}
  <div class="empty-state"><p>No completed sessions yet.</p></div>
{:else}
  <div class="sessions-list">
    {#each sessions as s}
      <div class="session-card" class:expanded={expandedId === s.id}>
        <button class="session-hdr" on:click={() => toggleExpand(s.id)}>
          <span class="session-dot" style="background:{sessionDot(s)}"></span>
          <div class="session-hdr-info">
            <div class="session-name">{s.name || 'Unnamed Session'}</div>
            <div class="session-meta">
              {formatDate(s.started_at)}{sessionDuration(s) ? ' · ' + sessionDuration(s) : ''}
            </div>
          </div>
          <span class="session-expand-arrow">{expandedId === s.id ? '▲' : '▼'}</span>
        </button>

        {#if expandedId === s.id}
          <div class="session-detail">
            {#if loadingDetail}
              <div class="flex items-center gap-2" style="padding:12px 0;"><div class="spinner"></div></div>
            {:else if expandedDetail}
              {#each expandedDetail.exercises as group}
                <div class="detail-group">
                  <div class="detail-ex-name">{group.exercise_name}</div>
                  <div class="set-chips">
                    {#each group.sets.filter(s => s.set_type !== 'warmup') as ws}
                      <span class="set-chip">
                        {ws.weight ?? 'BW'}×{ws.reps}
                        {#if ws.rir != null}<span class="set-chip-rir">R{ws.rir}</span>{/if}
                      </span>
                    {/each}
                  </div>
                </div>
              {/each}
              <div class="detail-actions">
                <button class="detail-action-btn" on:click={() => repeatSession(s)}>Repeat Session</button>
                <button class="detail-action-btn" on:click={() => saveAsTemplate(s)}>Save Template</button>
                <button class="detail-action-btn detail-action-danger" on:click={() => deleteSession(s)}>Delete</button>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    {/each}
  </div>

  {#if hasMore}
    <div style="text-align:center;margin-top:16px;">
      <button class="btn-secondary" on:click={loadMore}>Load More</button>
    </div>
  {/if}
{/if}

<style>
  .page-title {
    font-family: var(--serif);
    font-size: 26px;
    color: var(--text);
    margin-bottom: 16px;
    line-height: 1;
  }
  .page-title em { font-style: italic; color: var(--accent); }

  /* Month stats */
  .month-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 16px;
  }
  .month-stat {
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-radius: var(--radius-lg);
    padding: 12px 8px;
    text-align: center;
  }
  .month-val { font-family: var(--serif); font-size: 22px; color: var(--accent); line-height: 1; }
  .month-lbl { font-size: 9px; color: var(--muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.06em; }

  /* Progression chart */
  .prog-card { margin-bottom: 4px; }
  .ex-select { margin-top: 10px; margin-bottom: 12px; max-width: 300px; }
  .chart-placeholder { height: 100px; display: flex; align-items: center; justify-content: center; }
  .chart-wrap { height: 200px; position: relative; }

  /* Session list */
  .sessions-list { display: flex; flex-direction: column; gap: 6px; }
  .session-card {
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-radius: var(--radius-lg);
    overflow: hidden;
    transition: border-color 0.15s;
  }
  .session-card.expanded { border-color: var(--bdr-2); }
  .session-hdr {
    width: 100%; text-align: left; background: transparent; border: none;
    padding: 14px 16px; cursor: pointer;
    display: flex; align-items: center; gap: 12px;
  }
  .session-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  }
  .session-hdr-info { flex: 1; }
  .session-name { font-family: var(--serif); font-size: 17px; color: var(--text); line-height: 1; }
  .session-meta { font-size: 11px; color: var(--muted); margin-top: 3px; }
  .session-expand-arrow { font-size: 11px; color: var(--muted); }

  /* Session detail */
  .session-detail {
    border-top: 1px solid var(--bdr);
    padding: 14px 16px;
    background: var(--surf-2);
  }
  .detail-group { margin-bottom: 14px; }
  .detail-ex-name {
    font-size: 12px; color: var(--accent);
    font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; margin-bottom: 8px;
  }
  .set-chips { display: flex; flex-wrap: wrap; gap: 4px; }
  .set-chip {
    font-size: 11px; padding: 3px 9px; border-radius: 3px;
    background: var(--surf-3); border: 1px solid var(--bdr-2); color: var(--text);
  }
  .set-chip-rir { color: var(--muted); margin-left: 3px; }
  .detail-actions { display: flex; gap: 8px; margin-top: 4px; }
  .detail-action-btn {
    flex: 1; padding: 8px;
    background: transparent; border: 1px solid var(--bdr-2);
    border-radius: var(--radius); font-size: 12px; color: var(--muted);
    cursor: pointer; text-align: center; transition: all 0.15s;
  }
  .detail-action-btn:hover { border-color: var(--accent); color: var(--accent); }
  .detail-action-danger { color: var(--danger, #e8365d) !important; }
  .detail-action-danger:hover { border-color: var(--danger, #e8365d) !important; color: var(--danger, #e8365d) !important; }
</style>
