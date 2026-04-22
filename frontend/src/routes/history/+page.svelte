<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { formatDate, formatDateTime, epley1RM } from '$lib/utils.js';
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

  onMount(async () => {
    await loadPage();
    exercises = await api.exercises.list();
    loading = false;
  });

  async function loadPage() {
    const data = await api.sessions.list(page);
    const completed = data.filter(s => s.completed_at);
    sessions = [...sessions, ...completed];
    hasMore = data.length === 20;
  }

  async function loadMore() {
    page++;
    await loadPage();
  }

  async function toggleExpand(id) {
    if (expandedId === id) {
      expandedId = null;
      expandedDetail = null;
      return;
    }
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
    await new Promise(r => setTimeout(r, 0)); // wait for DOM
    if (!chartCanvas || progressionData.length === 0) { destroyChart(); return; }
    destroyChart();

    const labels = progressionData.map(d => {
      const date = new Date(d.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const oneRMs = progressionData.map(d => d.estimated_1rm);
    const volumes = progressionData.map(d => d.total_volume);

    chart = new Chart(chartCanvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Est. 1RM',
            data: oneRMs,
            borderColor: '#e8a040',
            backgroundColor: 'rgba(232,160,64,0.08)',
            borderWidth: 2,
            pointBackgroundColor: '#e8a040',
            pointRadius: 4,
            tension: 0.3,
            yAxisID: 'y',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#888', font: { size: 12 } } },
          tooltip: {
            backgroundColor: '#1a1a1a',
            borderColor: '#2a2a2a',
            borderWidth: 1,
            titleColor: '#e0e0e0',
            bodyColor: '#888',
          },
        },
        scales: {
          x: {
            ticks: { color: '#555', font: { size: 11 } },
            grid: { color: 'rgba(255,255,255,0.04)' },
          },
          y: {
            ticks: { color: '#555', font: { size: 11 } },
            grid: { color: 'rgba(255,255,255,0.04)' },
          },
        },
      },
    });
  }

  function destroyChart() {
    if (chart) { chart.destroy(); chart = null; }
  }

  function sessionDuration(s) {
    if (!s.started_at || !s.completed_at) return '';
    const diff = new Date(s.completed_at) - new Date(s.started_at);
    const m = Math.round(diff / 60000);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    const rem = m % 60;
    return rem > 0 ? `${h}h ${rem}m` : `${h}h`;
  }
</script>

<svelte:head><title>History — LiftForge</title></svelte:head>

<div style="max-width:900px;">
  <h2 style="font-size:20px; font-weight:700; margin-bottom:24px;">History</h2>

  <!-- Progression chart section -->
  <div class="card mb-4">
    <div class="section-title" style="margin-bottom:12px;">Exercise Progression</div>
    <div style="margin-bottom:12px;">
      <select bind:value={selectedExercise} style="max-width:300px;">
        <option value={null}>Select an exercise...</option>
        {#each exercises as ex}
          <option value={ex.id}>{ex.name}</option>
        {/each}
      </select>
    </div>

    {#if loadingChart}
      <div class="flex items-center gap-3" style="height:180px;">
        <div class="spinner"></div>
        <span style="color:var(--text-muted);">Loading...</span>
      </div>
    {:else if selectedExercise && progressionData.length === 0}
      <div style="height:120px; display:flex; align-items:center; justify-content:center; color:var(--text-muted);">
        No data yet for this exercise.
      </div>
    {:else if selectedExercise}
      <div style="height:220px; position:relative;">
        <canvas bind:this={chartCanvas}></canvas>
      </div>
    {:else}
      <div style="height:80px; display:flex; align-items:center; justify-content:center; color:var(--text-faint); font-size:13px;">
        Select an exercise to see progression
      </div>
    {/if}
  </div>

  <!-- Sessions list -->
  <div class="section-title">Past Sessions</div>

  {#if loading}
    <div class="flex items-center gap-3" style="padding:24px 0;">
      <div class="spinner"></div>
    </div>
  {:else if sessions.length === 0}
    <div class="card">
      <div class="empty-state"><p>No completed sessions yet.</p></div>
    </div>
  {:else}
    <div style="display:flex; flex-direction:column; gap:6px;">
      {#each sessions as s}
        <div class="card" style="padding:0; overflow:hidden;">
          <button
            on:click={() => toggleExpand(s.id)}
            style="width:100%; text-align:left; background:transparent; border:none; padding:14px 16px; cursor:pointer;"
          >
            <div class="flex items-center justify-between">
              <div>
                <div style="font-weight:600; font-size:14px; color:var(--text);">{s.name || 'Unnamed Session'}</div>
                <div style="color:var(--text-muted); font-size:12px; margin-top:2px;">
                  {formatDate(s.started_at)}
                  {#if s.completed_at}· {sessionDuration(s)}{/if}
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span style="color:var(--text-muted); font-size:12px;">{expandedId === s.id ? '▲' : '▼'}</span>
              </div>
            </div>
          </button>

          {#if expandedId === s.id}
            <div style="border-top:1px solid var(--border); padding:16px;">
              {#if loadingDetail}
                <div class="flex items-center gap-2"><div class="spinner"></div></div>
              {:else if expandedDetail}
                {#each expandedDetail.exercises as group}
                  <div style="margin-bottom:16px;">
                    <div style="font-weight:600; font-size:13px; color:var(--primary); margin-bottom:6px;">
                      {group.exercise_name}
                    </div>
                    <table>
                      <thead>
                        <tr>
                          <th>Set</th><th>Weight</th><th>Reps</th><th>RIR</th><th>Est. 1RM</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each group.sets as ws}
                          <tr>
                            <td style="color:var(--text-muted);">{ws.set_number}</td>
                            <td>{ws.weight ?? 'BW'}</td>
                            <td>{ws.reps}</td>
                            <td>{ws.rir ?? '—'}</td>
                            <td style="color:var(--text-muted);">
                              {ws.weight && ws.reps ? epley1RM(ws.weight, ws.reps).toFixed(1) : '—'}
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/each}
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>

    {#if hasMore}
      <div style="text-align:center; margin-top:16px;">
        <button class="btn-secondary" on:click={loadMore}>Load More</button>
      </div>
    {/if}
  {/if}
</div>
