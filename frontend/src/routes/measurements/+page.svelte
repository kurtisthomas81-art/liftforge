<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '$lib/api.js';

  let measurements = [];
  let loading = true;
  let saving = false;
  let saved = false;
  let showForm = false;
  let showOptional = false;
  let editingId = null;

  let form = {
    date: new Date().toISOString().slice(0, 10),
    body_weight: '', body_fat_pct: '',
    waist_in: '', chest_in: '', hips_in: '',
    left_arm_in: '', right_arm_in: '',
    left_quad_in: '', right_quad_in: '',
    notes: '',
  };

  let chart = null;
  let chartCanvas;

  const OPTIONAL_FIELDS = [
    { key: 'waist_in', label: 'Waist' },
    { key: 'chest_in', label: 'Chest' },
    { key: 'hips_in', label: 'Hips' },
    { key: 'left_arm_in', label: 'L Arm' },
    { key: 'right_arm_in', label: 'R Arm' },
    { key: 'left_quad_in', label: 'L Quad' },
    { key: 'right_quad_in', label: 'R Quad' },
    { key: 'body_fat_pct', label: 'BF%' },
  ];

  onMount(async () => {
    measurements = await api.measurements.list();
    loading = false;
    await renderChart();
  });

  onDestroy(() => { if (chart) chart.destroy(); });

  async function renderChart() {
    if (typeof window === 'undefined') return;
    const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - 90);
    const data = measurements.filter(m => m.body_weight != null && new Date(m.date) >= cutoff).reverse();
    if (data.length < 2) return;
    const { Chart, registerables } = await import('chart.js');
    Chart.register(...registerables);
    if (chart) chart.destroy();
    chart = new Chart(chartCanvas, {
      type: 'line',
      data: {
        labels: data.map(m => m.date),
        datasets: [{
          data: data.map(m => m.body_weight),
          borderColor: '#e8365d',
          backgroundColor: 'rgba(232,54,93,0.08)',
          tension: 0.3, fill: true,
          pointRadius: 3, pointBackgroundColor: '#e8365d',
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { backgroundColor:'#12121a', borderColor:'#22222e', borderWidth:1, titleColor:'#6868a0', bodyColor:'#f8f8ff' } },
        scales: {
          x: { ticks: { color:'#6868a0', maxTicksLimit:6 }, grid: { color:'#1a1a24' } },
          y: { ticks: { color:'#6868a0' }, grid: { color:'#1a1a24' } },
        },
      },
    });
  }

  function toNum(v) { const n = parseFloat(v); return isNaN(n) ? null : n; }

  async function logMeasurement() {
    if (!form.date) return;
    saving = true;
    const payload = {
      date: form.date,
      body_weight: toNum(form.body_weight),
      body_fat_pct: toNum(form.body_fat_pct),
      waist_in: toNum(form.waist_in), chest_in: toNum(form.chest_in), hips_in: toNum(form.hips_in),
      left_arm_in: toNum(form.left_arm_in), right_arm_in: toNum(form.right_arm_in),
      left_quad_in: toNum(form.left_quad_in), right_quad_in: toNum(form.right_quad_in),
      notes: form.notes,
    };
    if (editingId) { await api.measurements.update(editingId, payload); editingId = null; }
    else { await api.measurements.create(payload); }
    measurements = await api.measurements.list();
    saved = true; setTimeout(() => saved = false, 2500);
    saving = false; showForm = false;
    await renderChart();
  }

  async function deleteMeasurement(id) {
    if (!confirm('Delete this entry?')) return;
    await api.measurements.delete(id);
    measurements = measurements.filter(m => m.id !== id);
    await renderChart();
  }

  function startEdit(m) {
    editingId = m.id; showForm = true;
    form = { date:m.date, body_weight:m.body_weight??'', body_fat_pct:m.body_fat_pct??'', waist_in:m.waist_in??'', chest_in:m.chest_in??'', hips_in:m.hips_in??'', left_arm_in:m.left_arm_in??'', right_arm_in:m.right_arm_in??'', left_quad_in:m.left_quad_in??'', right_quad_in:m.right_quad_in??'', notes:m.notes??'' };
  }

  function cancelEdit() {
    editingId = null; showForm = false;
    form = { date:new Date().toISOString().slice(0,10), body_weight:'', body_fat_pct:'', waist_in:'', chest_in:'', hips_in:'', left_arm_in:'', right_arm_in:'', left_quad_in:'', right_quad_in:'', notes:'' };
  }

  $: latest = measurements[0];
  $: prev = measurements[1];
  $: weightDelta = latest?.body_weight != null && prev?.body_weight != null
    ? (latest.body_weight - prev.body_weight).toFixed(1) : null;
</script>

<svelte:head><title>Measurements — LiftForge</title></svelte:head>

<div class="page-title">Body <em>Measurements</em></div>

<!-- Weight sparkline card -->
{#if !loading && measurements.filter(m => m.body_weight != null).length >= 2}
  <div class="weight-card">
    <div class="weight-main">
      <div class="weight-val">{latest?.body_weight ?? '—'}<span class="weight-unit">lb</span></div>
      {#if weightDelta !== null}
        <div class="weight-delta" style="color:{parseFloat(weightDelta) > 0 ? 'var(--danger)' : 'var(--success)'}">
          {parseFloat(weightDelta) > 0 ? '+' : ''}{weightDelta} lb
        </div>
      {/if}
    </div>
    <div class="chart-wrap"><canvas bind:this={chartCanvas}></canvas></div>
  </div>
{:else if loading}
  <div class="flex items-center gap-3" style="padding:24px 0;"><div class="spinner"></div></div>
{/if}

<!-- Body stats grid -->
{#if latest}
  <div class="stats-grid">
    {#each OPTIONAL_FIELDS.filter(f => latest[f.key] != null) as f}
      {@const delta = prev?.[f.key] != null ? (latest[f.key] - prev[f.key]).toFixed(1) : null}
      <div class="stat-cell">
        <div class="stat-cell-lbl">{f.label}</div>
        <div class="stat-cell-val">{latest[f.key]}</div>
        {#if delta !== null}
          <div class="stat-cell-delta" style="color:{parseFloat(delta) > 0 ? 'var(--danger)' : 'var(--success)'}">
            {parseFloat(delta) > 0 ? '+' : ''}{delta}
          </div>
        {/if}
      </div>
    {/each}
  </div>
{/if}

<!-- Log Measurements button / form -->
<button class="log-btn" on:click={() => showForm = !showForm}>
  {showForm ? '▲ Hide Form' : '+ Log Measurements'}
</button>

{#if showForm}
  <div class="log-form card mt-3">
    <div class="section-title">{editingId ? 'Edit Entry' : 'New Entry'}</div>
    <div class="form-grid">
      <div>
        <label for="mDate">Date</label>
        <input id="mDate" type="date" bind:value={form.date} />
      </div>
      <div>
        <label for="mWeight">Body Weight (lb)</label>
        <input id="mWeight" type="number" min="0" step="0.1" bind:value={form.body_weight} placeholder="e.g. 185" />
      </div>
    </div>

    <button class="btn-ghost btn-sm" style="margin:10px 0 6px;"
      on:click={() => showOptional = !showOptional}>
      {showOptional ? '▲ Fewer fields' : '▼ Add measurements'}
    </button>

    {#if showOptional}
      <div class="form-grid">
        {#each OPTIONAL_FIELDS.slice(0, 6) as f}
          <div>
            <label for="m_{f.key}">{f.label}</label>
            <input id="m_{f.key}" type="number" min="0" step="0.1" bind:value={form[f.key]} placeholder="—" />
          </div>
        {/each}
      </div>
      <label for="mNotes" style="margin-top:8px;">Notes</label>
      <input id="mNotes" bind:value={form.notes} placeholder="Optional" />
    {/if}

    <div class="flex gap-2 mt-3">
      <button class="btn-primary" on:click={logMeasurement} disabled={saving || !form.date}>
        {saving ? 'Saving…' : editingId ? 'Save Edit' : 'Save Entry'}
      </button>
      {#if editingId}
        <button class="btn-ghost" on:click={cancelEdit}>Cancel</button>
      {/if}
      {#if saved}<span style="color:var(--success);font-size:12px;">Saved!</span>{/if}
    </div>
  </div>
{/if}

<!-- History table -->
{#if measurements.length > 0}
  <div class="section-title mt-4">History</div>
  <div class="history-rows">
    {#each measurements as m}
      <div class="hist-row">
        <div class="hist-date">{m.date}</div>
        <div class="hist-weight">{m.body_weight ?? '—'} lb</div>
        <div class="hist-actions">
          <button class="hist-action" on:click={() => startEdit(m)}>Edit</button>
          <button class="hist-action del" on:click={() => deleteMeasurement(m.id)}>✕</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<style>
  .page-title { font-family:var(--serif); font-size:26px; color:var(--text); margin-bottom:16px; line-height:1; }
  .page-title em { font-style:italic; color:var(--accent); }

  .weight-card {
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:14px 16px; margin-bottom:12px;
  }
  .weight-main { display:flex; align-items:baseline; gap:10px; margin-bottom:10px; }
  .weight-val { font-family:var(--serif); font-size:26px; color:var(--text); }
  .weight-unit { font-size:13px; color:var(--muted); margin-left:3px; }
  .weight-delta { font-size:13px; font-weight:600; }
  .chart-wrap { height:80px; position:relative; }

  .stats-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:12px; }
  .stat-cell {
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:10px 12px;
  }
  .stat-cell-lbl { font-size:9px; color:var(--muted); text-transform:uppercase; letter-spacing:0.08em; }
  .stat-cell-val { font-family:var(--serif); font-size:22px; color:var(--text); margin-top:2px; }
  .stat-cell-delta { font-size:10px; font-weight:600; margin-top:2px; }

  .log-btn {
    width:100%; background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:13px;
    font-size:13px; color:var(--muted); cursor:pointer;
    transition:border-color 0.15s, color 0.15s;
    font-family:var(--serif); font-size:15px;
  }
  .log-btn:hover { border-color:var(--accent); color:var(--accent); }

  .log-form { margin-top:8px; }
  .form-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:10px; }

  .history-rows { display:flex; flex-direction:column; }
  .hist-row {
    display:flex; align-items:center; gap:12px;
    padding:10px 0; border-bottom:1px solid var(--bdr);
  }
  .hist-row:last-child { border-bottom:none; }
  .hist-date { font-size:12px; color:var(--muted); flex:1; }
  .hist-weight { font-family:var(--serif); font-size:15px; color:var(--text); }
  .hist-actions { display:flex; gap:6px; }
  .hist-action {
    background:transparent; border:1px solid var(--bdr-2);
    border-radius:var(--radius); padding:3px 10px;
    font-size:11px; color:var(--muted); cursor:pointer;
    transition:all 0.15s;
  }
  .hist-action:hover { border-color:var(--accent); color:var(--accent); }
  .hist-action.del:hover { border-color:var(--danger); color:var(--danger); }
</style>
