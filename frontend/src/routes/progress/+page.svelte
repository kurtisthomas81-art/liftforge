<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '$lib/api.js';

  let loading = true;
  let fatigueData = null;
  let weekVolume = null;
  let prevWeekVolume = null;
  let exercises = [];
  let selectedExId = null;
  let progressionData = [];
  let loadingChart = false;
  let chart = null;
  let chartCanvas;
  let heatSide = 'front';
  let expandedCard = null;

  let goals = [];
  let showGoalForm = false;
  let goalExerciseId = null;
  let goalType = 'e1rm';
  let goalTarget = '';
  let goalDeadline = '';
  let savingGoal = false;
  let goalSearch = '';

  // Key exercise shortcuts — look up by name fragment
  let quickExercises = [];

  const SCIENCE_CARDS = [
    {
      title: 'Progressive Overload',
      body: 'The cornerstone of hypertrophy and strength. Each mesocycle, aim to add either weight, reps, or sets compared to the previous one. Small consistent increases compound over months into meaningful gains.',
    },
    {
      title: 'Volume Landmarks (MEV → MRV)',
      body: 'MEV is the minimum sets/week to maintain muscle. MAV is the sweet spot for growth. MRV is the ceiling — training above it stops driving gains and starts creating more fatigue than signal. Stay in the MAV range most of the time.',
    },
    {
      title: 'RIR & Proximity to Failure',
      body: 'Reps in Reserve (RIR) tracks how close you are to failure. Staying at RIR 2–3 on most sets optimizes stimulus while limiting junk fatigue. Pushing to RIR 0–1 should be reserved for final sets of a mesocycle.',
    },
    {
      title: 'Deload Strategy',
      body: 'After 4–8 weeks of accumulation, a deload week (50–60% of normal volume, same weights) clears fatigue and often reveals new strength. Don\'t skip it — the next block will be more productive for it.',
    },
  ];

  const FRONT_MUSCLES = ['chest', 'shoulders', 'biceps', 'abs', 'quads', 'calves'];
  const BACK_MUSCLES  = ['traps', 'lats', 'rear_delts', 'triceps', 'glutes', 'hamstrings'];

  onMount(async () => {
    [fatigueData, weekVolume, exercises, goals] = await Promise.all([
      api.volume.fatigueReport().catch(() => null),
      api.volume.forWeek().catch(() => null),
      api.exercises.list().catch(() => []),
      api.goals.list().catch(() => []),
    ]);

    // Get prev-week data for WoW comparison
    const prevDate = new Date(); prevDate.setDate(prevDate.getDate() - 7);
    prevWeekVolume = await api.volume.forWeek(prevDate.toISOString().slice(0,10)).catch(() => null);

    // Build quick-select exercises: Bench, Squat, Deadlift, OHP
    const keyNames = ['bench press', 'back squat', 'deadlift', 'overhead press'];
    quickExercises = keyNames
      .map(k => exercises.find(e => e.name.toLowerCase().includes(k.toLowerCase().split(' ')[0]) && (k.split(' ').length < 2 || e.name.toLowerCase().includes(k.toLowerCase().split(' ')[1]))))
      .filter(Boolean);

    loading = false;
  });

  onDestroy(() => { if (chart) { chart.destroy(); chart = null; } });

  $: overallScore = fatigueData != null ? Math.round(100 - fatigueData.fatigue_score * 10) : null;
  $: scoreColor = overallScore == null ? 'var(--muted)'
    : overallScore >= 75 ? 'var(--success)'
    : overallScore >= 45 ? 'var(--warn)'
    : 'var(--danger)';
  $: scoreLabel = fatigueData == null ? '—'
    : fatigueData.overall_fatigue === 'low' ? 'Fresh'
    : fatigueData.overall_fatigue === 'moderate' ? 'Building Fatigue'
    : fatigueData.overall_fatigue === 'high' ? 'High Fatigue'
    : 'Critical — Deload';

  // Heat map: normalize sets to 0–1 relative to ~20 sets (rough MRV)
  function heatValue(muscle) {
    if (!weekVolume?.muscles) return 0;
    const key = muscle.replace('_', ' ');
    const entry = weekVolume.muscles.find(m => m.muscle === key || m.muscle === muscle);
    if (!entry) return 0;
    const mrv = entry.landmarks?.mrv ?? 20;
    return Math.min(1, entry.sets / mrv);
  }

  function heatFill(muscle) {
    const v = heatValue(muscle);
    if (v <= 0) return 'rgba(255,255,255,0.03)';
    return `rgba(232,54,93,${(v * 0.82).toFixed(2)})`;
  }

  // WoW data: top muscles, this week vs prev week sets
  $: wowData = (() => {
    if (!weekVolume?.muscles) return [];
    const muscles = weekVolume.muscles
      .filter(m => m.sets > 0)
      .sort((a, b) => b.sets - a.sets)
      .slice(0, 6)
      .map(m => {
        const prev = prevWeekVolume?.muscles?.find(p => p.muscle === m.muscle);
        return { muscle: m.muscle, current: m.sets, prev: prev?.sets ?? 0 };
      });
    return muscles;
  })();

  $: wowMax = wowData.reduce((mx, d) => Math.max(mx, d.current, d.prev), 1);

  async function loadChart(exId) {
    if (!exId) { progressionData = []; destroyChart(); return; }
    loadingChart = true;
    progressionData = await api.history.exerciseProgression(exId).catch(() => []);
    loadingChart = false;
    await drawChart();
  }

  $: if (selectedExId !== undefined) loadChart(selectedExId);

  async function drawChart() {
    await new Promise(r => setTimeout(r, 0));
    destroyChart();
    if (!chartCanvas || !progressionData.length) return;
    const { Chart, registerables } = await import('chart.js');
    Chart.register(...registerables);
    chart = new Chart(chartCanvas, {
      type: 'line',
      data: {
        labels: progressionData.map(d => new Date(d.date).toLocaleDateString('en-US', { month:'short', day:'numeric' })),
        datasets: [{
          label: 'Est. 1RM',
          data: progressionData.map(d => parseFloat(d.estimated_1rm.toFixed(1))),
          borderColor: '#e8365d',
          backgroundColor: 'rgba(232,54,93,0.08)',
          borderWidth: 2,
          pointBackgroundColor: '#e8365d',
          pointRadius: 4,
          tension: 0.3,
          fill: true,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { backgroundColor:'#12121a', borderColor:'#22222e', borderWidth:1, titleColor:'#f8f8ff', bodyColor:'#6868a0' },
        },
        scales: {
          x: { ticks: { color:'#6868a0', font:{size:10}, maxTicksLimit:8 }, grid: { color:'rgba(255,255,255,0.03)' } },
          y: { ticks: { color:'#6868a0', font:{size:10} }, grid: { color:'rgba(255,255,255,0.03)' } },
        },
      },
    });
  }

  function destroyChart() { if (chart) { chart.destroy(); chart = null; } }

  async function saveGoal() {
    if (!goalExerciseId || !goalTarget) return;
    savingGoal = true;
    try {
      const g = await api.goals.create({
        exercise_id: goalExerciseId,
        goal_type: goalType,
        target_value: parseFloat(goalTarget),
        deadline: goalDeadline || null,
      });
      goals = [...goals, g];
      showGoalForm = false;
      goalExerciseId = null; goalTarget = ''; goalDeadline = ''; goalSearch = '';
    } catch {}
    savingGoal = false;
  }

  async function deleteGoal(id) {
    await api.goals.delete(id).catch(() => {});
    goals = goals.filter(g => g.id !== id);
  }

  $: filteredExercises = goalSearch
    ? exercises.filter(e => e.name.toLowerCase().includes(goalSearch.toLowerCase())).slice(0, 8)
    : [];

  $: activeGoals = goals.filter(g => g.status === 'active');
  $: achievedGoals = goals.filter(g => g.status === 'achieved');

  $: bestOneRM = progressionData.length
    ? Math.max(...progressionData.map(d => d.estimated_1rm)).toFixed(1)
    : null;
  $: latestOneRM = progressionData.length
    ? progressionData[progressionData.length - 1].estimated_1rm.toFixed(1)
    : null;
</script>

<svelte:head><title>Progress — LiftForge</title></svelte:head>

<div class="page-title">Training <em>Progress</em></div>

{#if loading}
  <div class="flex items-center gap-3" style="padding:32px 0;"><div class="spinner"></div></div>
{:else}

<!-- Score card -->
<div class="score-card">
  <div class="score-main">
    <div class="score-num" style="color:{scoreColor}">{overallScore ?? '—'}</div>
    <div class="score-label">{scoreLabel}</div>
    {#if fatigueData?.deload_recommended}
      <div class="deload-badge">Deload Recommended</div>
    {/if}
  </div>
  <div class="score-detail">
    <div class="score-detail-row">
      <span class="score-detail-lbl">Fatigue Score</span>
      <span class="score-detail-val">{fatigueData?.fatigue_score ?? '—'} / 10</span>
    </div>
    {#if fatigueData?.muscles_at_risk?.length}
      <div class="score-detail-row">
        <span class="score-detail-lbl">At Risk</span>
        <span class="score-detail-val" style="color:var(--danger)">{fatigueData.muscles_at_risk.join(', ')}</span>
      </div>
    {/if}
    {#if fatigueData?.last_deload_days_ago != null}
      <div class="score-detail-row">
        <span class="score-detail-lbl">Last Deload</span>
        <span class="score-detail-val">{fatigueData.last_deload_days_ago}d ago</span>
      </div>
    {/if}
  </div>
</div>

<!-- 1RM Trend -->
<div class="card section-card">
  <div class="section-title">1RM Trend</div>

  <!-- Quick-select shortcuts -->
  {#if quickExercises.length > 0}
    <div class="quick-pills">
      {#each quickExercises as ex}
        <button class="quick-pill" class:active={selectedExId === ex.id}
          on:click={() => selectedExId = ex.id}>
          {ex.name.split(' ').slice(0, 2).join(' ')}
        </button>
      {/each}
    </div>
  {/if}

  <select class="ex-select" bind:value={selectedExId}>
    <option value={null}>Select exercise…</option>
    {#each exercises as ex}
      <option value={ex.id}>{ex.name}</option>
    {/each}
  </select>

  {#if selectedExId && (bestOneRM || latestOneRM)}
    <div class="rm-stats">
      <div class="rm-stat">
        <div class="rm-val">{bestOneRM}<span class="rm-unit">lb</span></div>
        <div class="rm-lbl">Best est. 1RM</div>
      </div>
      <div class="rm-stat">
        <div class="rm-val">{latestOneRM}<span class="rm-unit">lb</span></div>
        <div class="rm-lbl">Latest</div>
      </div>
    </div>
  {/if}

  {#if loadingChart}
    <div class="chart-placeholder"><div class="spinner"></div></div>
  {:else if selectedExId && !progressionData.length}
    <div class="chart-placeholder" style="color:var(--muted);font-size:13px;">No data yet.</div>
  {:else if selectedExId}
    <div class="chart-wrap"><canvas bind:this={chartCanvas}></canvas></div>
  {:else}
    <div class="chart-placeholder" style="color:var(--faint);font-size:12px;">Select an exercise to see 1RM trend</div>
  {/if}
</div>

<!-- Goals -->
<div class="card section-card">
  <div class="goals-hdr">
    <div class="section-title" style="margin-bottom:0">Goals</div>
    <button class="add-goal-btn" on:click={() => showGoalForm = !showGoalForm}>
      {showGoalForm ? 'Cancel' : '+ Add Goal'}
    </button>
  </div>

  {#if showGoalForm}
    <div class="goal-form">
      <div class="goal-form-row">
        <input class="goal-input" placeholder="Search exercise…" bind:value={goalSearch} />
        {#if filteredExercises.length}
          <div class="goal-ex-dropdown">
            {#each filteredExercises as ex}
              <button class="goal-ex-opt" on:click={() => { goalExerciseId = ex.id; goalSearch = ex.name; filteredExercises = []; }}>
                {ex.name}
              </button>
            {/each}
          </div>
        {/if}
      </div>
      <div class="goal-type-row">
        {#each [['e1rm','Est. 1RM'],['weight','Max Weight'],['reps','Max Reps']] as [val, lbl]}
          <button class="goal-type-btn" class:active={goalType === val} on:click={() => goalType = val}>{lbl}</button>
        {/each}
      </div>
      <div class="goal-form-row">
        <input class="goal-input" type="number" min="1" placeholder="{goalType === 'reps' ? 'Reps target' : 'Weight target (lbs)'}" bind:value={goalTarget} style="flex:1" />
        <input class="goal-input" type="date" bind:value={goalDeadline} style="flex:1" />
      </div>
      <button class="btn-primary" on:click={saveGoal} disabled={savingGoal || !goalExerciseId || !goalTarget}>
        {savingGoal ? 'Saving…' : 'Save Goal'}
      </button>
    </div>
  {/if}

  {#if activeGoals.length === 0 && !showGoalForm}
    <p class="goals-empty">No active goals. Add one to track your progress.</p>
  {/if}

  {#each activeGoals as g}
    {@const barColor = g.pct >= 100 ? 'var(--success)' : 'var(--accent)'}
    <div class="goal-card">
      <div class="goal-card-hdr">
        <div class="goal-ex-name">{g.exercise_name}</div>
        <div class="goal-right">
          <span class="goal-type-badge">{g.goal_type}</span>
          <button class="goal-del" on:click={() => deleteGoal(g.id)}>×</button>
        </div>
      </div>
      <div class="goal-bar-track">
        <div class="goal-bar-fill" style="width:{g.pct}%;background:{barColor}"></div>
      </div>
      <div class="goal-meta">
        <span style="color:var(--muted)">{g.current_value ?? '—'} → <strong style="color:var(--text)">{g.target_value}</strong> {g.goal_type === 'reps' ? 'reps' : 'lbs'}</span>
        <span style="color:{barColor};font-weight:600">{g.pct}%</span>
      </div>
      {#if g.deadline}
        <div class="goal-deadline">by {new Date(g.deadline + 'T00:00:00').toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' })}</div>
      {/if}
    </div>
  {/each}

  {#if achievedGoals.length > 0}
    <div class="achieved-hdr">Achieved</div>
    {#each achievedGoals as g}
      <div class="goal-card achieved-card">
        <div class="goal-card-hdr">
          <div class="goal-ex-name">{g.exercise_name} <span class="achieved-badge">✓ Achieved</span></div>
          <button class="goal-del" on:click={() => deleteGoal(g.id)}>×</button>
        </div>
        <div class="goal-meta">
          <span style="color:var(--muted)">{g.target_value} {g.goal_type === 'reps' ? 'reps' : 'lbs'} ({g.goal_type})</span>
          {#if g.achieved_at}
            <span style="color:var(--muted)">{new Date(g.achieved_at).toLocaleDateString('en-US', { month:'short', day:'numeric' })}</span>
          {/if}
        </div>
      </div>
    {/each}
  {/if}
</div>

<!-- Week-over-Week Volume -->
{#if wowData.length > 0}
  <div class="card section-card">
    <div class="section-title">Week-over-Week Volume</div>
    <div class="wow-legend">
      <span class="wow-dot" style="background:var(--accent)"></span><span>This week</span>
      <span class="wow-dot" style="background:var(--bdr-2)"></span><span>Last week</span>
    </div>
    <div class="wow-bars">
      {#each wowData as row}
        {@const curW = (row.current / wowMax) * 100}
        {@const prvW = (row.prev / wowMax) * 100}
        {@const gained = row.current >= row.prev}
        <div class="wow-row">
          <div class="wow-muscle">{row.muscle}</div>
          <div class="wow-bar-wrap">
            <div class="wow-bar current" style="width:{curW}%; background:{gained ? 'var(--accent)' : 'var(--warn)'}"></div>
            <div class="wow-bar prev" style="width:{prvW}%"></div>
          </div>
          <div class="wow-num" style="color:{gained ? 'var(--success)' : 'var(--warn)'}">
            {row.current > row.prev ? '+' : ''}{row.current - row.prev}
          </div>
        </div>
      {/each}
    </div>
  </div>
{/if}

<!-- Science cards -->
<div class="section-title mt-4">Training Principles</div>
{#each SCIENCE_CARDS as card, i}
  <div class="science-card" class:open={expandedCard === i}>
    <button class="science-hdr" on:click={() => expandedCard = expandedCard === i ? null : i}>
      <span class="science-title">{card.title}</span>
      <span class="science-chevron">{expandedCard === i ? '▲' : '▼'}</span>
    </button>
    {#if expandedCard === i}
      <div class="science-body">{card.body}</div>
    {/if}
  </div>
{/each}

<!-- Muscle Heatmap -->
<div class="section-title mt-4">Muscle Volume Map <span style="font-size:11px;color:var(--muted);font-family:var(--sans)">this week</span></div>
<div class="heatmap-card">
  <div class="heatmap-toggle">
    <button class="toggle-btn" class:active={heatSide === 'front'} on:click={() => heatSide = 'front'}>Front</button>
    <button class="toggle-btn" class:active={heatSide === 'back'}  on:click={() => heatSide = 'back'}>Back</button>
  </div>

  <div class="body-wrap">
    {#if heatSide === 'front'}
      <!-- Front body SVG -->
      <svg viewBox="0 0 120 268" xmlns="http://www.w3.org/2000/svg" class="body-svg">
        <!-- silhouette -->
        <circle cx="60" cy="18" r="14" fill="#1a1a24" />
        <rect x="54" y="31" width="12" height="10" rx="3" fill="#1a1a24" />
        <rect x="35" y="40" width="50" height="82" rx="10" fill="#1a1a24" />
        <rect x="17" y="44" width="18" height="46" rx="9" fill="#1a1a24" />
        <rect x="85" y="44" width="18" height="46" rx="9" fill="#1a1a24" />
        <rect x="20" y="88" width="14" height="36" rx="7" fill="#1a1a24" />
        <rect x="86" y="88" width="14" height="36" rx="7" fill="#1a1a24" />
        <rect x="38" y="124" width="20" height="62" rx="9" fill="#1a1a24" />
        <rect x="62" y="124" width="20" height="62" rx="9" fill="#1a1a24" />
        <rect x="40" y="184" width="16" height="46" rx="7" fill="#1a1a24" />
        <rect x="64" y="184" width="16" height="46" rx="7" fill="#1a1a24" />
        <!-- chest -->
        <rect x="36" y="41" width="48" height="34" rx="8" fill={heatFill('chest')} />
        <!-- shoulders -->
        <ellipse cx="26" cy="50" rx="11" ry="10" fill={heatFill('shoulders')} />
        <ellipse cx="94" cy="50" rx="11" ry="10" fill={heatFill('shoulders')} />
        <!-- biceps -->
        <rect x="18" y="45" width="16" height="44" rx="8" fill={heatFill('biceps')} />
        <rect x="86" y="45" width="16" height="44" rx="8" fill={heatFill('biceps')} />
        <!-- abs -->
        <rect x="36" y="75" width="48" height="47" rx="8" fill={heatFill('abs')} />
        <!-- quads -->
        <rect x="39" y="125" width="18" height="60" rx="8" fill={heatFill('quads')} />
        <rect x="63" y="125" width="18" height="60" rx="8" fill={heatFill('quads')} />
        <!-- calves -->
        <rect x="41" y="185" width="14" height="44" rx="6" fill={heatFill('calves')} />
        <rect x="65" y="185" width="14" height="44" rx="6" fill={heatFill('calves')} />
      </svg>

    {:else}
      <!-- Back body SVG -->
      <svg viewBox="0 0 120 268" xmlns="http://www.w3.org/2000/svg" class="body-svg">
        <!-- silhouette -->
        <circle cx="60" cy="18" r="14" fill="#1a1a24" />
        <rect x="54" y="31" width="12" height="10" rx="3" fill="#1a1a24" />
        <rect x="35" y="40" width="50" height="82" rx="10" fill="#1a1a24" />
        <rect x="17" y="44" width="18" height="46" rx="9" fill="#1a1a24" />
        <rect x="85" y="44" width="18" height="46" rx="9" fill="#1a1a24" />
        <rect x="20" y="88" width="14" height="36" rx="7" fill="#1a1a24" />
        <rect x="86" y="88" width="14" height="36" rx="7" fill="#1a1a24" />
        <rect x="38" y="124" width="20" height="62" rx="9" fill="#1a1a24" />
        <rect x="62" y="124" width="20" height="62" rx="9" fill="#1a1a24" />
        <rect x="40" y="184" width="16" height="46" rx="7" fill="#1a1a24" />
        <rect x="64" y="184" width="16" height="46" rx="7" fill="#1a1a24" />
        <!-- traps -->
        <rect x="40" y="40" width="40" height="24" rx="6" fill={heatFill('traps')} />
        <!-- rear delts -->
        <ellipse cx="26" cy="50" rx="11" ry="10" fill={heatFill('rear_delts')} />
        <ellipse cx="94" cy="50" rx="11" ry="10" fill={heatFill('rear_delts')} />
        <!-- lats -->
        <rect x="36" y="56" width="14" height="50" rx="6" fill={heatFill('lats')} />
        <rect x="70" y="56" width="14" height="50" rx="6" fill={heatFill('lats')} />
        <!-- triceps -->
        <rect x="18" y="45" width="16" height="44" rx="8" fill={heatFill('triceps')} />
        <rect x="86" y="45" width="16" height="44" rx="8" fill={heatFill('triceps')} />
        <!-- glutes -->
        <rect x="36" y="122" width="48" height="30" rx="8" fill={heatFill('glutes')} />
        <!-- hamstrings -->
        <rect x="39" y="152" width="18" height="34" rx="8" fill={heatFill('hamstrings')} />
        <rect x="63" y="152" width="18" height="34" rx="8" fill={heatFill('hamstrings')} />
      </svg>
    {/if}

    <!-- Muscle labels -->
    <div class="heat-labels">
      {#each (heatSide === 'front' ? FRONT_MUSCLES : BACK_MUSCLES) as muscle}
        {@const v = heatValue(muscle)}
        <div class="heat-label">
          <div class="heat-swatch" style="background:rgba(232,54,93,{Math.max(0.1, v * 0.82).toFixed(2)});opacity:{v > 0 ? 1 : 0.3}"></div>
          <span style="color:{v > 0 ? 'var(--text)' : 'var(--muted)'}">{muscle.replace('_', ' ')}</span>
          {#if v > 0}
            <span class="heat-sets">{(weekVolume.muscles.find(m => m.muscle === muscle || m.muscle === muscle.replace('_',' '))?.sets ?? 0)} sets</span>
          {/if}
        </div>
      {/each}
    </div>
  </div>
</div>

{/if}

<style>
  .page-title { font-family:var(--serif); font-size:26px; color:var(--text); margin-bottom:16px; line-height:1; }
  .page-title em { font-style:italic; color:var(--accent); }

  /* Score card */
  .score-card {
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:20px 18px;
    margin-bottom:12px; display:flex; gap:20px; align-items:flex-start;
  }
  .score-main { flex-shrink:0; text-align:center; }
  .score-num { font-family:var(--serif); font-size:52px; line-height:1; }
  .score-label { font-size:11px; color:var(--muted); margin-top:4px; text-transform:uppercase; letter-spacing:0.07em; }
  .deload-badge {
    margin-top:8px; font-size:10px; font-weight:600;
    color:var(--danger); border:1px solid var(--danger);
    border-radius:4px; padding:2px 8px;
    background:rgba(232,54,93,0.1);
  }
  .score-detail { flex:1; display:flex; flex-direction:column; gap:8px; padding-top:4px; }
  .score-detail-row { display:flex; justify-content:space-between; align-items:baseline; }
  .score-detail-lbl { font-size:11px; color:var(--muted); }
  .score-detail-val { font-size:13px; color:var(--text); }

  /* Sections */
  .section-card { margin-bottom:12px; }
  .mt-4 { margin-top:16px; }

  /* Quick pills */
  .quick-pills { display:flex; gap:6px; flex-wrap:wrap; margin:10px 0 6px; }
  .quick-pill {
    padding:4px 12px; background:transparent;
    border:1px solid var(--bdr-2); border-radius:4px;
    font-size:11px; color:var(--muted); cursor:pointer;
    transition:all 0.15s;
  }
  .quick-pill.active { border-color:var(--accent); color:var(--accent); background:var(--accent-bg); }

  .ex-select { margin-top:8px; margin-bottom:10px; max-width:300px; }
  .chart-placeholder { height:100px; display:flex; align-items:center; justify-content:center; }
  .chart-wrap { height:200px; position:relative; }

  /* 1RM stats */
  .rm-stats { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:12px; }
  .rm-stat {
    background:var(--surf-2); border:1px solid var(--bdr-2);
    border-radius:var(--radius); padding:10px 12px;
  }
  .rm-val { font-family:var(--serif); font-size:22px; color:var(--accent); line-height:1; }
  .rm-unit { font-size:11px; color:var(--muted); margin-left:3px; }
  .rm-lbl { font-size:10px; color:var(--muted); margin-top:3px; }

  /* Goals */
  .goals-hdr { display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; }
  .add-goal-btn {
    font-size:11px; padding:4px 12px; background:transparent;
    border:1px solid var(--bdr-2); border-radius:4px;
    color:var(--muted); cursor:pointer; transition:all 0.15s;
  }
  .add-goal-btn:hover { border-color:var(--accent); color:var(--accent); }
  .goals-empty { font-size:12px; color:var(--muted); padding:8px 0; }

  .goal-form { background:var(--surf-2); border:1px solid var(--bdr-2); border-radius:var(--radius); padding:14px; margin-bottom:14px; display:flex; flex-direction:column; gap:10px; }
  .goal-form-row { display:flex; gap:8px; position:relative; }
  .goal-input {
    flex:1; background:var(--surf); border:1px solid var(--bdr-2);
    border-radius:var(--radius); padding:8px 10px;
    font-size:12px; color:var(--text); outline:none;
  }
  .goal-ex-dropdown {
    position:absolute; top:100%; left:0; right:0; z-index:20;
    background:var(--surf); border:1px solid var(--bdr-2); border-radius:var(--radius);
    margin-top:2px; overflow:hidden;
  }
  .goal-ex-opt {
    display:block; width:100%; text-align:left; padding:8px 12px;
    background:transparent; border:none; font-size:12px; color:var(--text);
    cursor:pointer; transition:background 0.1s;
  }
  .goal-ex-opt:hover { background:var(--surf-2); }
  .goal-type-row { display:flex; gap:6px; }
  .goal-type-btn {
    flex:1; padding:5px; background:transparent;
    border:1px solid var(--bdr-2); border-radius:4px;
    font-size:11px; color:var(--muted); cursor:pointer; transition:all 0.15s;
  }
  .goal-type-btn.active { border-color:var(--accent); color:var(--accent); background:var(--accent-bg); }

  .goal-card {
    background:var(--surf-2); border:1px solid var(--bdr-2);
    border-radius:var(--radius); padding:12px 14px; margin-bottom:8px;
  }
  .goal-card-hdr { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
  .goal-ex-name { font-family:var(--serif); font-size:16px; color:var(--text); }
  .goal-right { display:flex; align-items:center; gap:8px; }
  .goal-type-badge {
    font-size:9px; padding:2px 7px; border-radius:3px;
    background:var(--accent-bg); color:var(--accent);
    border:1px solid rgba(232,54,93,0.25); text-transform:uppercase; font-weight:600;
  }
  .goal-del { background:none; border:none; color:var(--muted); font-size:16px; cursor:pointer; padding:0 2px; line-height:1; }
  .goal-del:hover { color:var(--danger); }
  .goal-bar-track { height:5px; background:var(--faint); border-radius:3px; overflow:hidden; margin-bottom:6px; }
  .goal-bar-fill { height:100%; border-radius:3px; transition:width 0.4s ease; }
  .goal-meta { display:flex; justify-content:space-between; font-size:11px; }
  .goal-deadline { font-size:10px; color:var(--muted); margin-top:4px; }

  .achieved-hdr { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:0.08em; font-weight:600; margin:14px 0 8px; }
  .achieved-card { opacity:0.6; }
  .achieved-badge { font-size:10px; color:var(--success); font-weight:600; margin-left:8px; font-family:var(--sans); }

  /* WoW bars */
  .wow-legend { display:flex; gap:12px; align-items:center; font-size:11px; color:var(--muted); margin-bottom:12px; }
  .wow-dot { width:8px; height:8px; border-radius:2px; flex-shrink:0; }
  .wow-bars { display:flex; flex-direction:column; gap:8px; }
  .wow-row { display:flex; align-items:center; gap:8px; }
  .wow-muscle { width:84px; font-size:11px; color:var(--muted); text-transform:capitalize; flex-shrink:0; }
  .wow-bar-wrap { flex:1; display:flex; flex-direction:column; gap:3px; }
  .wow-bar { height:6px; border-radius:3px; min-width:2px; transition:width 0.4s ease; }
  .wow-bar.prev { background:var(--bdr-2); }
  .wow-num { width:30px; text-align:right; font-size:11px; font-weight:600; flex-shrink:0; }

  /* Science cards */
  .science-card {
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); margin-bottom:6px;
    overflow:hidden; transition:border-color 0.15s;
  }
  .science-card.open { border-color:var(--accent); }
  .science-hdr {
    width:100%; text-align:left; background:transparent; border:none;
    padding:14px 16px; cursor:pointer;
    display:flex; justify-content:space-between; align-items:center;
  }
  .science-title { font-family:var(--serif); font-size:16px; color:var(--text); }
  .science-chevron { font-size:10px; color:var(--muted); }
  .science-body {
    padding:0 16px 16px;
    font-size:13px; color:var(--muted); line-height:1.7;
    border-top:1px solid var(--bdr);
    padding-top:12px;
  }

  /* Heatmap */
  .heatmap-card {
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:16px;
    margin-bottom:12px;
  }
  .heatmap-toggle { display:flex; gap:6px; margin-bottom:16px; }
  .toggle-btn {
    padding:5px 16px; background:transparent;
    border:1px solid var(--bdr-2); border-radius:4px;
    font-size:12px; color:var(--muted); cursor:pointer;
    transition:all 0.15s;
  }
  .toggle-btn.active { border-color:var(--accent); color:var(--accent); background:var(--accent-bg); }

  .body-wrap { display:flex; gap:16px; align-items:flex-start; }
  .body-svg { width:120px; flex-shrink:0; }

  .heat-labels { flex:1; display:flex; flex-direction:column; gap:6px; padding-top:4px; }
  .heat-label { display:flex; align-items:center; gap:8px; font-size:12px; text-transform:capitalize; }
  .heat-swatch { width:10px; height:10px; border-radius:2px; flex-shrink:0; }
  .heat-sets { margin-left:auto; font-size:10px; color:var(--muted); }
</style>
