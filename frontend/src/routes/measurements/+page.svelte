<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '$lib/api.js';

  let measurements = [];
  let loading = true;
  let saving = false;
  let saved = false;
  let showOptional = false;
  let editingId = null;

  // Quick-log form
  let form = {
    date: new Date().toISOString().slice(0, 10),
    body_weight: '',
    body_fat_pct: '',
    waist_in: '',
    chest_in: '',
    hips_in: '',
    left_arm_in: '',
    right_arm_in: '',
    left_quad_in: '',
    right_quad_in: '',
    notes: '',
  };

  let chart = null;
  let chartCanvas;

  const OPTIONAL_FIELDS = [
    { key: 'body_fat_pct',  label: 'Body Fat %' },
    { key: 'waist_in',      label: 'Waist (in)' },
    { key: 'chest_in',      label: 'Chest (in)' },
    { key: 'hips_in',       label: 'Hips (in)' },
    { key: 'left_arm_in',   label: 'Left Arm (in)' },
    { key: 'right_arm_in',  label: 'Right Arm (in)' },
    { key: 'left_quad_in',  label: 'Left Quad (in)' },
    { key: 'right_quad_in', label: 'Right Quad (in)' },
  ];

  onMount(async () => {
    measurements = await api.measurements.list();
    const latest = measurements[0];
    if (latest) {
      // Pre-fill optional from latest
      for (const f of OPTIONAL_FIELDS) {
        if (latest[f.key] != null) form[f.key] = latest[f.key];
      }
    }
    loading = false;
    await renderChart();
  });

  onDestroy(() => {
    if (chart) chart.destroy();
  });

  async function renderChart() {
    if (typeof window === 'undefined') return;
    // Last 90 days of body weight
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 90);

    const data = measurements
      .filter(m => m.body_weight != null && new Date(m.date) >= cutoff)
      .reverse(); // oldest first

    if (data.length < 2) return;

    const { Chart, registerables } = await import('chart.js');
    Chart.register(...registerables);

    if (chart) chart.destroy();
    chart = new Chart(chartCanvas, {
      type: 'line',
      data: {
        labels: data.map(m => m.date),
        datasets: [{
          label: 'Body Weight',
          data: data.map(m => m.body_weight),
          borderColor: '#e8a040',
          backgroundColor: 'rgba(232, 160, 64, 0.08)',
          tension: 0.3,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: '#e8a040',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1a1a1a',
            borderColor: '#2a2a2a',
            borderWidth: 1,
            titleColor: '#888',
            bodyColor: '#e0e0e0',
          },
        },
        scales: {
          x: {
            ticks: { color: '#888', maxTicksLimit: 8 },
            grid: { color: '#2a2a2a' },
          },
          y: {
            ticks: { color: '#888' },
            grid: { color: '#2a2a2a' },
          },
        },
      },
    });
  }

  function toNum(v) {
    const n = parseFloat(v);
    return isNaN(n) ? null : n;
  }

  async function logMeasurement() {
    if (!form.date) return;
    saving = true;
    const payload = {
      date: form.date,
      body_weight: toNum(form.body_weight),
      body_fat_pct: toNum(form.body_fat_pct),
      waist_in: toNum(form.waist_in),
      chest_in: toNum(form.chest_in),
      hips_in: toNum(form.hips_in),
      left_arm_in: toNum(form.left_arm_in),
      right_arm_in: toNum(form.right_arm_in),
      left_quad_in: toNum(form.left_quad_in),
      right_quad_in: toNum(form.right_quad_in),
      notes: form.notes,
    };
    if (editingId) {
      await api.measurements.update(editingId, payload);
      editingId = null;
    } else {
      await api.measurements.create(payload);
    }
    measurements = await api.measurements.list();
    saved = true;
    setTimeout(() => (saved = false), 2500);
    saving = false;
    await renderChart();
  }

  async function deleteMeasurement(id) {
    if (!confirm('Delete this entry?')) return;
    await api.measurements.delete(id);
    measurements = measurements.filter(m => m.id !== id);
    await renderChart();
  }

  function startEdit(m) {
    editingId = m.id;
    form = {
      date: m.date,
      body_weight: m.body_weight ?? '',
      body_fat_pct: m.body_fat_pct ?? '',
      waist_in: m.waist_in ?? '',
      chest_in: m.chest_in ?? '',
      hips_in: m.hips_in ?? '',
      left_arm_in: m.left_arm_in ?? '',
      right_arm_in: m.right_arm_in ?? '',
      left_quad_in: m.left_quad_in ?? '',
      right_quad_in: m.right_quad_in ?? '',
      notes: m.notes ?? '',
    };
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function cancelEdit() {
    editingId = null;
    form = {
      date: new Date().toISOString().slice(0, 10),
      body_weight: '', body_fat_pct: '', waist_in: '', chest_in: '',
      hips_in: '', left_arm_in: '', right_arm_in: '',
      left_quad_in: '', right_quad_in: '', notes: '',
    };
  }
</script>

<svelte:head><title>Measurements — LiftForge</title></svelte:head>

<div style="max-width:800px;">
  <h2 style="font-size:20px; font-weight:700; margin-bottom:24px;">Body Measurements</h2>

  <!-- Quick-log form -->
  <div class="card mb-4">
    <div class="section-title mb-3">{editingId ? 'Edit Entry' : 'Log Today'}</div>
    <div style="display:flex; flex-wrap:wrap; gap:12px; align-items:flex-end;">
      <div style="flex:0 0 130px;">
        <label for="mDate">Date</label>
        <input id="mDate" type="date" bind:value={form.date} />
      </div>
      <div style="flex:0 0 110px;">
        <label for="mWeight">Body Weight</label>
        <input id="mWeight" type="number" min="0" step="0.1" bind:value={form.body_weight} placeholder="e.g. 185" />
      </div>
      {#if showOptional}
        {#each OPTIONAL_FIELDS as f}
          <div style="flex:0 0 110px;">
            <label for="m_{f.key}">{f.label}</label>
            <input id="m_{f.key}" type="number" min="0" step="0.1" bind:value={form[f.key]} placeholder="—" />
          </div>
        {/each}
      {/if}
      <div>
        <label style="opacity:0; pointer-events:none;">.</label>
        <button
          class="btn-ghost btn-sm"
          on:click={() => (showOptional = !showOptional)}
          style="white-space:nowrap;"
        >{showOptional ? '▲ Fewer fields' : '▼ More measurements'}</button>
      </div>
    </div>
    {#if showOptional}
      <div style="margin-top:10px;">
        <label for="mNotes">Notes</label>
        <input id="mNotes" bind:value={form.notes} placeholder="Optional notes" />
      </div>
    {/if}
    <div class="flex items-center gap-3 mt-3">
      <button class="btn-primary" on:click={logMeasurement} disabled={saving || !form.date}>
        {saving ? 'Saving...' : editingId ? 'Save Edit' : 'Log Entry'}
      </button>
      {#if editingId}
        <button class="btn-ghost" on:click={cancelEdit}>Cancel</button>
      {/if}
      {#if saved}
        <span style="color:var(--success); font-size:13px;">Saved!</span>
      {/if}
    </div>
  </div>

  <!-- Weight chart -->
  {#if !loading && measurements.filter(m => m.body_weight != null).length >= 2}
    <div class="card mb-4">
      <div class="section-title mb-2">Body Weight — Last 90 Days</div>
      <div style="height:180px; position:relative;">
        <canvas bind:this={chartCanvas}></canvas>
      </div>
    </div>
  {/if}

  <!-- History table -->
  <div class="card">
    <div class="flex items-center justify-between mb-3">
      <div class="section-title" style="margin-bottom:0;">History</div>
      <button class="btn-ghost btn-sm" on:click={() => (showOptional = !showOptional)}>
        {showOptional ? 'Hide columns' : 'Show all columns'}
      </button>
    </div>

    {#if loading}
      <div class="flex items-center gap-3" style="padding:24px 0;">
        <div class="spinner"></div>
      </div>
    {:else if measurements.length === 0}
      <div class="empty-state" style="padding:24px;">
        <p>No measurements logged yet.</p>
      </div>
    {:else}
      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Weight</th>
              {#if showOptional}
                {#each OPTIONAL_FIELDS as f}
                  <th>{f.label}</th>
                {/each}
              {/if}
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each measurements as m}
              <tr>
                <td style="color:var(--text-muted);">{m.date}</td>
                <td style="font-weight:500;">{m.body_weight ?? '—'}</td>
                {#if showOptional}
                  {#each OPTIONAL_FIELDS as f}
                    <td>{m[f.key] ?? '—'}</td>
                  {/each}
                {/if}
                <td>
                  <div class="flex gap-2">
                    <button class="btn-ghost btn-sm" on:click={() => startEdit(m)}>Edit</button>
                    <button class="btn-danger btn-sm" on:click={() => deleteMeasurement(m.id)}>✕</button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
