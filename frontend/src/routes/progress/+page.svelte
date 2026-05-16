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

  let strengthData = null;
  let strengthRatioHistory = null;
  let sweetSpotData = null;
  let chart2 = null;
  let chartCanvas2;

  const LIFT_COLORS = { squat: '#4a9eff', bench: '#e8365d', deadlift: '#8bc34a', ohp: '#cd853f' };
  const LIFT_LABELS = { squat: 'Squat', bench: 'Bench', deadlift: 'Deadlift', ohp: 'OHP' };
  const MUSCLE_LABELS = { chest: 'Chest', quads: 'Quads', back: 'Back', shoulders: 'Shoulders' };

  const SCIENCE_CARDS = [
    {
      title: 'Progressive Overload',
      body: 'The cornerstone of hypertrophy and strength. Each training block (mesocycle), aim to add either weight, reps, or sets compared to the previous one. Small consistent increases compound over months into meaningful gains.',
    },
    {
      title: 'Volume Targets (MEV → MRV)',
      body: 'MEV (floor) is the minimum sets/week to maintain muscle. MAV (target zone) is the sweet spot for growth. MRV (limit) is the ceiling — training above it stops driving gains and starts creating more fatigue than signal. Stay in the MAV range most of the time.',
    },
    {
      title: 'RIR — Reps Left in Tank',
      body: 'Reps in Reserve (RIR) tracks how close you are to failure. Staying at RIR 2–3 on most sets optimizes stimulus while limiting junk fatigue. Pushing to RIR 0–1 should be reserved for final sets of a training block.',
    },
    {
      title: 'Recovery Week (Deload)',
      body: 'After 4–8 weeks of accumulation, a recovery (deload) week (50–60% of normal volume, same weights) clears fatigue and often reveals new strength. Don\'t skip it — the next block will be more productive for it.',
    },
  ];

  const VOL_ORDER = { below_mev: 0, at_mrv: 1, above_mav: 2, in_mav: 3, unknown: 4 };

  const VOL_COLOR = {
    below_mev: 'var(--danger)',
    in_mav:    'var(--success)',
    above_mav: 'var(--accent)',
    at_mrv:    'var(--danger)',
    unknown:   'var(--muted)',
  };

  const VOL_LABEL = {
    below_mev: 'Under MEV',
    in_mav:    'On track',
    above_mav: 'Above sweet spot',
    at_mrv:    'At MRV',
    unknown:   'Not tracked',
  };

  onMount(async () => {
    [fatigueData, weekVolume, exercises, goals, strengthData, strengthRatioHistory, sweetSpotData] = await Promise.all([
      api.volume.fatigueReport().catch(() => null),
      api.volume.forWeek().catch(() => null),
      api.exercises.list().catch(() => []),
      api.goals.list().catch(() => []),
      api.profile.strengthLevel().catch(() => null),
      api.analytics.strengthRatioHistory().catch(() => null),
      api.analytics.volumeSweetSpot().catch(() => null),
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
    if (strengthRatioHistory) await drawChart2();
  });

  onDestroy(() => {
    if (chart) { chart.destroy(); chart = null; }
    if (chart2) { chart2.destroy(); chart2 = null; }
  });

  function levelColor(level) {
    if (level === 'elite')        return '#cd853f';
    if (level === 'advanced')     return 'var(--accent)';
    if (level === 'intermediate') return '#4a9eff';
    return '#6868a0';
  }
  function liftLabel(key) {
    return { squat: 'Squat', bench: 'Bench', deadlift: 'Deadlift', ohp: 'OHP' }[key] ?? key;
  }
  function nextLevelName(level) {
    return { beginner: 'Intermediate', intermediate: 'Advanced', advanced: 'Elite' }[level] ?? '';
  }

  $: overallScore = fatigueData != null ? Math.round(100 - fatigueData.fatigue_score * 10) : null;
  $: scoreColor = overallScore == null ? 'var(--muted)'
    : overallScore >= 75 ? 'var(--success)'
    : overallScore >= 45 ? 'var(--warn)'
    : 'var(--danger)';
  $: scoreLabel = fatigueData == null ? '—'
    : fatigueData.overall_fatigue === 'low' ? 'Fresh'
    : fatigueData.overall_fatigue === 'moderate' ? 'Building Fatigue'
    : fatigueData.overall_fatigue === 'high' ? 'High Fatigue'
    : 'Critical — Deload Now';

  $: sortedVolMuscles = weekVolume?.muscles
    ? [...weekVolume.muscles].sort((a, b) => (VOL_ORDER[a.status] ?? 4) - (VOL_ORDER[b.status] ?? 4))
    : [];

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

  function projectLinear(data, weeks = 8) {
    if (data.length < 3) return [];
    const pts = data.slice(-8).map(d => d.estimated_1rm);
    const n = pts.length;
    const xm = (n - 1) / 2;
    const ym = pts.reduce((a, b) => a + b, 0) / n;
    const slope = pts.map((y, i) => (i - xm) * (y - ym)).reduce((a, b) => a + b, 0)
                / pts.map((_, i) => (i - xm) ** 2).reduce((a, b) => a + b, 0);
    return Array.from({ length: weeks }, (_, w) =>
      Math.max(0, parseFloat((ym + slope * (w + 1 + (n - 1) / 2 - xm)).toFixed(1)))
    );
  }

  async function drawChart() {
    await new Promise(r => setTimeout(r, 0));
    destroyChart();
    if (!chartCanvas || !progressionData.length) return;
    const { Chart, registerables } = await import('chart.js');
    Chart.register(...registerables);

    const historicalLabels = progressionData.map(d => new Date(d.date).toLocaleDateString('en-US', { month:'short', day:'numeric' }));
    const historicalVals = progressionData.map(d => parseFloat(d.estimated_1rm.toFixed(1)));
    const projected = projectLinear(progressionData);
    const projLabels = projected.map((_, i) => `+${i + 1}w`);
    const allLabels = [...historicalLabels, ...projLabels];

    const projData = projected.length
      ? [...Array(historicalVals.length - 1).fill(null), historicalVals[historicalVals.length - 1], ...projected]
      : [];

    chart = new Chart(chartCanvas, {
      type: 'line',
      data: {
        labels: allLabels,
        datasets: [
          {
            label: 'Est. 1RM',
            data: [...historicalVals, ...Array(projLabels.length).fill(null)],
            borderColor: '#e8365d',
            backgroundColor: 'rgba(232,54,93,0.08)',
            borderWidth: 2,
            pointBackgroundColor: '#e8365d',
            pointRadius: 4,
            tension: 0.3,
            fill: true,
          },
          ...(projData.length ? [{
            label: 'Projected',
            data: projData,
            borderColor: '#6868a0',
            borderDash: [6, 4],
            borderWidth: 1.5,
            fill: false,
            pointRadius: 0,
            tension: 0.3,
          }] : []),
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: projected.length > 0, labels: { color:'#6868a0', font:{size:10}, boxWidth:16 } },
          tooltip: { backgroundColor:'#12121a', borderColor:'#22222e', borderWidth:1, titleColor:'#f8f8ff', bodyColor:'#6868a0' },
        },
        scales: {
          x: { ticks: { color:'#6868a0', font:{size:10}, maxTicksLimit:10 }, grid: { color:'rgba(255,255,255,0.03)' } },
          y: { ticks: { color:'#6868a0', font:{size:10} }, grid: { color:'rgba(255,255,255,0.03)' } },
        },
      },
    });
  }

  function destroyChart() { if (chart) { chart.destroy(); chart = null; } }

  async function drawChart2() {
    await new Promise(r => setTimeout(r, 0));
    if (chart2) { chart2.destroy(); chart2 = null; }
    if (!chartCanvas2 || !strengthRatioHistory) return;
    const lifts = strengthRatioHistory.lifts;
    const datasets = Object.entries(lifts)
      .filter(([, pts]) => pts.length >= 2)
      .map(([key, pts]) => ({
        label: LIFT_LABELS[key] ?? key,
        data: pts.map(p => p.ratio),
        borderColor: LIFT_COLORS[key] ?? '#6868a0',
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 3,
        tension: 0.3,
        fill: false,
      }));
    if (!datasets.length || !chartCanvas2) return;
    // Use the union of all dates as labels (keyed to first lift with most points)
    const longestKey = Object.entries(lifts).sort((a, b) => b[1].length - a[1].length)[0]?.[0];
    const labels = lifts[longestKey]?.map(p => p.date) ?? [];
    // Align each dataset to those labels using a sparse map
    datasets.forEach((ds, i) => {
      const key = Object.keys(lifts).filter(k => lifts[k].length >= 2)[i];
      const map = Object.fromEntries(lifts[key].map(p => [p.date, p.ratio]));
      ds.data = labels.map(l => map[l] ?? null);
    });
    const { Chart, registerables } = await import('chart.js');
    Chart.register(...registerables);
    chart2 = new Chart(chartCanvas2, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: true, labels: { color:'#6868a0', font:{size:10}, boxWidth:16 } },
          tooltip: {
            backgroundColor:'#12121a', borderColor:'#22222e', borderWidth:1,
            titleColor:'#f8f8ff', bodyColor:'#6868a0',
            callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y}×BW` },
          },
        },
        scales: {
          x: { ticks: { color:'#6868a0', font:{size:10}, maxTicksLimit:8 }, grid: { color:'rgba(255,255,255,0.03)' } },
          y: { ticks: { color:'#6868a0', font:{size:10}, callback: v => `${v}×` }, grid: { color:'rgba(255,255,255,0.03)' } },
        },
      },
    });
  }

  $: hasRatioData = strengthRatioHistory && Object.values(strengthRatioHistory.lifts ?? {}).some(pts => pts.length >= 2);
  $: sweetSpotMuscles = sweetSpotData?.muscles ? Object.entries(sweetSpotData.muscles) : [];

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

<div class="page">

  <div class="page-header">
    <h2>Progress</h2>
    <p class="subtitle">Strength trends, volume, and training readiness</p>
  </div>

  {#if loading}
    <div class="spinner-wrap"><div class="spinner"></div></div>
  {:else}

  <!-- Readiness summary card -->
  <div class="summary-card">
    <div class="summary-top">
      <div>
        <div class="sum-label">Training Readiness</div>
        <div class="sum-level" style="color:{scoreColor}">{scoreLabel}</div>
      </div>
      <div class="score-badge" style="color:{scoreColor}; border-color:{scoreColor}44">
        <span class="score-num">{overallScore ?? '—'}</span><span class="score-denom">/100</span>
      </div>
    </div>

    <div class="gauge-wrap">
      <div class="gauge-track">
        <div class="gz gz-crit" style="width:25%"></div>
        <div class="gz gz-high" style="left:25%;width:20%"></div>
        <div class="gz gz-mod"  style="left:45%;width:20%"></div>
        <div class="gz gz-low"  style="left:65%;width:35%"></div>
        <div class="gauge-fill" style="width:{overallScore ?? 0}%;background:{scoreColor}"></div>
      </div>
      <div class="gauge-legend">
        <span>Critical</span>
        <span>High</span>
        <span>Building</span>
        <span>Fresh</span>
      </div>
    </div>

    {#if fatigueData?.deload_recommended}
      <div class="deload-pill">Recovery week recommended</div>
    {/if}

    {#if fatigueData?.muscles_at_risk?.length}
      <ul class="flag-list">
        <li>Muscles at risk: {fatigueData.muscles_at_risk.join(', ')}</li>
        {#each (fatigueData.reasons ?? []) as r}<li>{r}</li>{/each}
      </ul>
    {:else if fatigueData}
      <p class="no-flags">No fatigue flags — training load looks healthy.</p>
    {/if}
  </div>

  <!-- Strength Level -->
  {#if strengthData}
  <div class="card section-card">
    <div class="card-hdr">Strength Level</div>
    {#if !strengthData.has_body_weight}
      <p class="prompt-text">Add body weight in your weekly check-in to unlock strength grading.</p>
    {:else if !strengthData.lifts.some(l => l.level !== null)}
      <p class="prompt-text">Log Squat, Bench, Deadlift, and OHP to calibrate your strength level.</p>
    {:else}
      <div class="strength-overall">
        <span class="level-badge" style="background:{levelColor(strengthData.overall_level)}">
          {strengthData.overall_level ?? '—'}
        </span>
        <span class="strength-method">Symmetric Strength · weakest lift scores</span>
      </div>
      <div class="lift-list">
        {#each strengthData.lifts as lift}
          <div class="lift-row">
            <div class="dot" style="background:{levelColor(lift.level ?? 'beginner')}"></div>
            <div class="lift-top">
              <span class="lift-name">{liftLabel(lift.lift_key)}</span>
              {#if lift.level}
                <span class="lift-level" style="color:{levelColor(lift.level)}">{lift.level}</span>
                <span class="lift-e1rm">{lift.e1rm} · {lift.ratio}×BW</span>
              {:else}
                <span class="no-data">no data</span>
              {/if}
            </div>
            {#if lift.level}
              <div class="lift-bar-track">
                <div class="lift-bar-fill" style="width:{lift.pct_to_next}%;background:{levelColor(lift.level)}"></div>
              </div>
              {#if lift.level !== 'elite'}
                <div class="lift-bar-label">{lift.pct_to_next}% to {nextLevelName(lift.level)} · {lift.next_threshold}×BW</div>
              {:else}
                <div class="lift-bar-label" style="color:#cd853f">Elite — top tier</div>
              {/if}
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>
  {/if}

  <!-- Strength / Bodyweight Over Time -->
  <div class="card section-card">
    <div class="card-hdr">Strength / Bodyweight Over Time</div>
    {#if !hasRatioData}
      <p class="prompt-text">Log PRs and body weight measurements to unlock this chart.</p>
    {:else}
      <div class="chart-wrap"><canvas bind:this={chartCanvas2}></canvas></div>
    {/if}
  </div>

  <!-- Volume Sweet Spot -->
  <div class="card section-card">
    <div class="card-hdr">Volume Sweet Spot</div>
    <p class="card-sub">Weekly sets that preceded your best PRs most often.</p>
    {#if sweetSpotMuscles.length === 0}
      <p class="prompt-text">Need 3+ PRs per lift to detect patterns.</p>
    {:else}
      <div class="sweet-list">
        {#each sweetSpotMuscles as [muscle, data]}
          <div class="sweet-row">
            <span class="sweet-muscle">{MUSCLE_LABELS[muscle] ?? muscle}</span>
            <span class="sweet-mid">best results at</span>
            <span class="sweet-val">{data.peak_bucket} sets/week</span>
            <span class="sweet-count">{data.buckets.find(b => b.label === data.peak_bucket)?.count ?? 0} / {data.pr_count} PRs</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <!-- 1RM Trend -->
  <div class="card section-card">
    <div class="card-hdr">Max Lift Trend (1RM)</div>

    {#if quickExercises.length > 0}
      <div class="seg-ctrl">
        {#each quickExercises as ex}
          <button class:active={selectedExId === ex.id} on:click={() => selectedExId = ex.id}>
            {ex.name.split(' ').slice(0, 2).join(' ')}
          </button>
        {/each}
      </div>
    {/if}

    <select bind:value={selectedExId}>
      <option value={null}>Select exercise…</option>
      {#each exercises as ex}
        <option value={ex.id}>{ex.name}</option>
      {/each}
    </select>

    {#if selectedExId && (bestOneRM || latestOneRM)}
      <div class="rm-stats">
        <div class="rm-stat">
          <div class="rm-val">{bestOneRM}<span class="rm-unit"> lb</span></div>
          <div class="rm-lbl">Best est. 1RM</div>
        </div>
        <div class="rm-stat">
          <div class="rm-val">{latestOneRM}<span class="rm-unit"> lb</span></div>
          <div class="rm-lbl">Latest</div>
        </div>
      </div>
    {/if}

    {#if loadingChart}
      <div class="chart-placeholder"><div class="spinner"></div></div>
    {:else if selectedExId && !progressionData.length}
      <div class="chart-placeholder">No data yet.</div>
    {:else if selectedExId}
      <div class="chart-wrap"><canvas bind:this={chartCanvas}></canvas></div>
    {:else}
      <div class="chart-placeholder">Select an exercise to see 1RM trend</div>
    {/if}
  </div>

  <!-- Goals -->
  <div class="card section-card">
    <div class="card-hdr-row">
      <div class="card-hdr" style="margin:0">Goals</div>
      <button class="ghost-btn" on:click={() => showGoalForm = !showGoalForm}>
        {showGoalForm ? 'Cancel' : '+ Add Goal'}
      </button>
    </div>

    {#if showGoalForm}
      <div class="goal-form">
        <div class="goal-form-row">
          <input placeholder="Search exercise…" bind:value={goalSearch} />
          {#if filteredExercises.length}
            <div class="ex-dropdown">
              {#each filteredExercises as ex}
                <button class="ex-opt" on:click={() => { goalExerciseId = ex.id; goalSearch = ex.name; filteredExercises = []; }}>
                  {ex.name}
                </button>
              {/each}
            </div>
          {/if}
        </div>
        <div class="seg-ctrl">
          {#each [['e1rm','Est. 1RM'],['weight','Max Weight'],['reps','Max Reps']] as [val, lbl]}
            <button class:active={goalType === val} on:click={() => goalType = val}>{lbl}</button>
          {/each}
        </div>
        <div class="goal-form-row">
          <input type="number" min="1" placeholder="{goalType === 'reps' ? 'Reps target' : 'Weight (lbs)'}" bind:value={goalTarget} />
          <input type="date" bind:value={goalDeadline} />
        </div>
        <button class="btn-primary" on:click={saveGoal} disabled={savingGoal || !goalExerciseId || !goalTarget}>
          {savingGoal ? 'Saving…' : 'Save Goal'}
        </button>
      </div>
    {/if}

    {#if activeGoals.length === 0 && !showGoalForm}
      <p class="prompt-text">No active goals. Add one to track your progress.</p>
    {/if}

    {#each activeGoals as g}
      {@const barColor = g.pct >= 100 ? 'var(--success)' : 'var(--accent)'}
      <div class="goal-item">
        <div class="goal-item-hdr">
          <div class="goal-name">{g.exercise_name}</div>
          <div class="goal-right">
            <span class="goal-type-tag">{g.goal_type}</span>
            <button class="del-btn" on:click={() => deleteGoal(g.id)}>×</button>
          </div>
        </div>
        <div class="bar-track-thin">
          <div class="bar-fill-thin" style="width:{g.pct}%;background:{barColor}"></div>
        </div>
        <div class="goal-meta">
          <span class="muted-text">{g.current_value ?? '—'} → <strong style="color:var(--text)">{g.target_value}</strong> {g.goal_type === 'reps' ? 'reps' : 'lbs'}</span>
          <span style="color:{barColor};font-weight:600">{g.pct}%</span>
        </div>
        {#if g.deadline}
          <div class="goal-deadline">by {new Date(g.deadline + 'T00:00:00').toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' })}</div>
        {/if}
      </div>
    {/each}

    {#if achievedGoals.length > 0}
      <div class="sub-hdr">Achieved</div>
      {#each achievedGoals as g}
        <div class="goal-item achieved">
          <div class="goal-item-hdr">
            <div class="goal-name">{g.exercise_name} <span class="achieved-mark">✓</span></div>
            <button class="del-btn" on:click={() => deleteGoal(g.id)}>×</button>
          </div>
          <div class="goal-meta">
            <span class="muted-text">{g.target_value} {g.goal_type === 'reps' ? 'reps' : 'lbs'}</span>
            {#if g.achieved_at}
              <span class="muted-text">{new Date(g.achieved_at).toLocaleDateString('en-US', { month:'short', day:'numeric' })}</span>
            {/if}
          </div>
        </div>
      {/each}
    {/if}
  </div>

  <!-- Week-over-Week Volume -->
  {#if wowData.length > 0}
  <div class="card section-card">
    <div class="card-hdr">Week-over-Week Volume</div>
    <div class="wow-legend">
      <span class="dot" style="background:var(--accent);border-radius:2px;width:10px;height:10px"></span><span>This week</span>
      <span class="dot" style="background:var(--bdr-2);border-radius:2px;width:10px;height:10px"></span><span>Last week</span>
    </div>
    <div class="wow-list">
      {#each wowData as row}
        {@const curW = (row.current / wowMax) * 100}
        {@const prvW = (row.prev / wowMax) * 100}
        {@const gained = row.current >= row.prev}
        <div class="wow-row">
          <div class="wow-muscle">{row.muscle}</div>
          <div class="wow-bars">
            <div class="wow-bar" style="width:{curW}%; background:{gained ? 'var(--accent)' : 'var(--warn)'}"></div>
            <div class="wow-bar wow-prev" style="width:{prvW}%"></div>
          </div>
          <div class="wow-delta" style="color:{gained ? 'var(--success)' : 'var(--warn)'}">
            {row.current > row.prev ? '+' : ''}{row.current - row.prev}
          </div>
        </div>
      {/each}
    </div>
  </div>
  {/if}

  <!-- Training Principles -->
  <div class="card-hdr standalone-hdr">Training Principles</div>
  {#each SCIENCE_CARDS as card, i}
    <div class="accordion" class:open={expandedCard === i}>
      <button class="accordion-hdr" on:click={() => expandedCard = expandedCard === i ? null : i}>
        <span class="accordion-title">{card.title}</span>
        <span class="accordion-chevron">{expandedCard === i ? '▲' : '▼'}</span>
      </button>
      {#if expandedCard === i}
        <div class="accordion-body">{card.body}</div>
      {/if}
    </div>
  {/each}

  <!-- Weekly Volume by muscle group -->
  <div class="card-hdr standalone-hdr" style="margin-top:1.25rem">
    Weekly Volume
    {#if weekVolume?.goal}
      <span class="goal-chip">{weekVolume.goal.replace('_', ' ')}</span>
    {/if}
    <span class="hdr-sub">sets vs targets</span>
  </div>

  <div class="muscle-list">
    {#each sortedVolMuscles as m}
      {@const lm = m.landmarks}
      <div class="vol-row">
        <div class="dot" style="background:{VOL_COLOR[m.status] ?? 'var(--muted)'}"></div>
        <div class="vol-name">{m.muscle.charAt(0).toUpperCase() + m.muscle.slice(1)}</div>
        <div class="vol-count">{m.sets}<span class="vol-mrv">{lm ? ` / ${lm.mrv}` : ''}</span></div>
        <div class="vol-status" style="color:{VOL_COLOR[m.status] ?? 'var(--muted)'}">{VOL_LABEL[m.status] ?? '—'}</div>
      </div>
    {/each}
  </div>

  {/if}
</div>

<style>
  .page {
    padding: 1.5rem 1.25rem 3rem;
    max-width: 780px;
    margin: 0 auto;
  }

  /* Page header */
  .page-header { margin-bottom: 1.5rem; }

  h2 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text);
    margin: 0 0 0.2rem;
  }

  .subtitle {
    font-size: 0.82rem;
    color: var(--muted);
    margin: 0;
  }

  /* Summary card — matches Recovery */
  .summary-card {
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-radius: 12px;
    padding: 1.25rem 1.5rem 1rem;
    margin-bottom: 1rem;
  }

  .summary-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.25rem;
  }

  .sum-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--muted);
    margin-bottom: 0.25rem;
  }

  .sum-level { font-size: 1.25rem; font-weight: 700; }

  .score-badge {
    display: flex;
    align-items: baseline;
    gap: 1px;
    border: 2px solid;
    border-radius: 10px;
    padding: 4px 12px 4px 10px;
  }

  .score-num  { font-size: 1.6rem; font-weight: 700; line-height: 1; }
  .score-denom { font-size: 0.85rem; font-weight: 500; color: var(--muted); }

  /* Gauge — matches Recovery */
  .gauge-wrap { margin-bottom: 0.75rem; }

  .gauge-track {
    position: relative;
    height: 8px;
    border-radius: 4px;
    background: var(--bdr);
    overflow: hidden;
    margin-bottom: 4px;
  }

  .gz { position: absolute; top: 0; height: 100%; }
  .gz-crit { background: var(--danger); opacity: 0.15; }
  .gz-high { background: #e07b39; opacity: 0.15; }
  .gz-mod  { background: var(--warn); opacity: 0.15; }
  .gz-low  { background: var(--success); opacity: 0.15; }

  .gauge-fill {
    position: absolute;
    top: 0; left: 0;
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
  }

  .gauge-legend {
    display: grid;
    grid-template-columns: 25fr 20fr 20fr 35fr;
    font-size: 0.65rem;
    color: var(--muted);
  }

  .gauge-legend span:not(:first-child) { text-align: center; }
  .gauge-legend span:last-child { text-align: right; }

  .deload-pill {
    display: inline-block;
    background: var(--danger);
    color: #fff;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 100px;
    margin: 0.75rem 0 0.5rem;
  }

  .flag-list {
    margin: 0.75rem 0 0;
    padding: 0 0 0 1.1rem;
    list-style: disc;
  }

  .flag-list li { font-size: 0.8rem; color: var(--muted); line-height: 1.5; padding: 0.1rem 0; }

  .no-flags { font-size: 0.82rem; color: var(--muted); margin: 0.5rem 0 0; }

  /* Section cards */
  .section-card { margin-bottom: 0.75rem; }

  /* Card header — matches Recovery's group-hdr style */
  .card-hdr {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 1rem;
  }

  .card-hdr-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
  }

  .standalone-hdr {
    padding: 0.9rem 0 0.4rem;
    border-top: 1px solid var(--bdr);
    margin-bottom: 0.5rem;
  }

  .goal-chip {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 100px;
    background: var(--accent-bg);
    color: var(--accent);
    text-transform: capitalize;
    letter-spacing: 0.02em;
    margin-left: 0.5rem;
    vertical-align: middle;
  }

  .hdr-sub {
    font-size: 0.65rem;
    color: var(--muted);
    text-transform: none;
    letter-spacing: 0;
    margin-left: 0.5rem;
    font-weight: 400;
  }

  .card-sub {
    font-size: 0.78rem;
    color: var(--muted);
    margin: -0.5rem 0 0.75rem;
  }

  .prompt-text { font-size: 0.82rem; color: var(--muted); }

  /* Strength level */
  .strength-overall {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 1rem;
  }

  .level-badge {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 700;
    color: #fff;
    text-transform: capitalize;
  }

  .strength-method { font-size: 0.72rem; color: var(--muted); }

  .lift-list { display: flex; flex-direction: column; gap: 0; }

  .lift-row {
    display: grid;
    grid-template-columns: 10px 1fr;
    grid-template-rows: auto auto auto;
    column-gap: 0.75rem;
    row-gap: 0;
    padding: 0.65rem 0;
    border-bottom: 1px solid var(--bdr);
    align-items: center;
  }

  .lift-top {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    grid-column: 2;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    grid-row: 1;
    align-self: center;
  }

  .lift-name {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    width: 52px;
    flex-shrink: 0;
  }

  .lift-level { font-size: 0.82rem; font-weight: 600; text-transform: capitalize; }
  .lift-e1rm  { font-size: 0.82rem; color: var(--text); margin-left: auto; }
  .no-data    { font-size: 0.78rem; color: var(--muted); }

  .lift-bar-track {
    grid-column: 2;
    height: 4px;
    background: rgba(255,255,255,0.06);
    border-radius: 2px;
    overflow: hidden;
    margin-top: 6px;
  }

  .lift-bar-fill { height: 100%; border-radius: 2px; transition: width .4s; }

  .lift-bar-label {
    grid-column: 2;
    font-size: 0.68rem;
    color: var(--muted);
    margin-top: 3px;
  }

  /* Seg control — matches Recovery */
  .seg-ctrl {
    display: flex;
    background: var(--surf-2);
    border: 1px solid var(--bdr);
    border-radius: 8px;
    padding: 3px;
    gap: 2px;
    margin-bottom: 0.75rem;
    width: fit-content;
  }

  .seg-ctrl button {
    background: none;
    border: none;
    padding: 5px 16px;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--muted);
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .seg-ctrl button.active {
    background: var(--accent);
    color: #fff;
  }

  /* Charts */
  .chart-wrap { height: 200px; position: relative; margin-top: 0.5rem; }
  .chart-placeholder { height: 80px; display: flex; align-items: center; justify-content: center; font-size: 0.82rem; color: var(--muted); }

  /* 1RM stats */
  .rm-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0.75rem 0; }

  .rm-stat {
    background: var(--surf-2);
    border: 1px solid var(--bdr-2);
    border-radius: var(--radius);
    padding: 10px 12px;
  }

  .rm-val  { font-size: 1.4rem; font-weight: 700; color: var(--accent); line-height: 1; }
  .rm-unit { font-size: 0.72rem; color: var(--muted); }
  .rm-lbl  { font-size: 0.68rem; color: var(--muted); margin-top: 3px; }

  /* Goals */
  .ghost-btn {
    font-size: 0.78rem;
    padding: 4px 12px;
    background: transparent;
    border: 1px solid var(--bdr-2);
    border-radius: 6px;
    color: var(--muted);
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }

  .ghost-btn:hover { border-color: var(--accent); color: var(--accent); }

  .goal-form {
    background: var(--surf-2);
    border: 1px solid var(--bdr-2);
    border-radius: var(--radius);
    padding: 14px;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .goal-form-row { display: flex; gap: 8px; position: relative; }
  .goal-form-row input { flex: 1; }

  .ex-dropdown {
    position: absolute;
    top: 100%;
    left: 0; right: 0;
    z-index: 20;
    background: var(--surf);
    border: 1px solid var(--bdr-2);
    border-radius: var(--radius);
    margin-top: 2px;
  }

  .ex-opt {
    display: block;
    width: 100%;
    text-align: left;
    padding: 8px 12px;
    background: transparent;
    border: none;
    font-size: 0.82rem;
    color: var(--text);
    cursor: pointer;
  }

  .ex-opt:hover { background: var(--surf-2); }

  .goal-item {
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--bdr);
  }

  .goal-item-hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .goal-name { font-size: 0.9rem; font-weight: 500; color: var(--text); }

  .goal-right { display: flex; align-items: center; gap: 8px; }

  .goal-type-tag {
    font-size: 0.68rem;
    padding: 2px 7px;
    border-radius: 3px;
    background: var(--accent-bg);
    color: var(--accent);
    border: 1px solid rgba(232,54,93,0.25);
    text-transform: uppercase;
    font-weight: 600;
  }

  .del-btn {
    background: none;
    border: none;
    color: var(--muted);
    font-size: 1rem;
    cursor: pointer;
    padding: 0 2px;
    line-height: 1;
  }

  .del-btn:hover { color: var(--danger); }

  .bar-track-thin { height: 5px; background: var(--bdr-2); border-radius: 3px; overflow: hidden; margin-bottom: 6px; }
  .bar-fill-thin  { height: 100%; border-radius: 3px; transition: width 0.4s ease; }

  .goal-meta { display: flex; justify-content: space-between; font-size: 0.78rem; }
  .goal-deadline { font-size: 0.72rem; color: var(--muted); margin-top: 4px; }
  .muted-text { color: var(--muted); }

  .sub-hdr {
    font-size: 0.68rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin: 1rem 0 0.5rem;
  }

  .achieved { opacity: 0.6; }
  .achieved-mark { font-size: 0.78rem; color: var(--success); font-weight: 600; }

  /* WoW volume */
  .wow-legend { display: flex; gap: 12px; align-items: center; font-size: 0.78rem; color: var(--muted); margin-bottom: 0.75rem; }

  .wow-list { display: flex; flex-direction: column; gap: 8px; }

  .wow-row { display: flex; align-items: center; gap: 8px; }
  .wow-muscle { width: 84px; font-size: 0.78rem; color: var(--muted); text-transform: capitalize; flex-shrink: 0; }
  .wow-bars { flex: 1; display: flex; flex-direction: column; gap: 3px; }
  .wow-bar { height: 6px; border-radius: 3px; min-width: 2px; transition: width 0.4s ease; }
  .wow-prev { background: var(--bdr-2); }
  .wow-delta { width: 30px; text-align: right; font-size: 0.78rem; font-weight: 600; flex-shrink: 0; }

  /* Sweet spot */
  .sweet-list { display: flex; flex-direction: column; gap: 8px; }
  .sweet-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; flex-wrap: wrap; }
  .sweet-muscle { font-weight: 600; color: var(--text); text-transform: capitalize; }
  .sweet-mid { color: var(--muted); }
  .sweet-val { color: var(--accent); font-weight: 600; }
  .sweet-count { font-size: 0.72rem; color: var(--muted); margin-left: auto; }

  /* Science accordion */
  .accordion {
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-radius: var(--radius-lg);
    margin-bottom: 6px;
    overflow: hidden;
  }

  .accordion.open { border-color: var(--accent); }

  .accordion-hdr {
    width: 100%;
    text-align: left;
    background: transparent;
    border: none;
    padding: 14px 16px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .accordion-title { font-size: 0.9rem; font-weight: 500; color: var(--text); }
  .accordion-chevron { font-size: 0.65rem; color: var(--muted); }

  .accordion-body {
    padding: 12px 16px 16px;
    font-size: 0.82rem;
    color: var(--muted);
    line-height: 1.7;
    border-top: 1px solid var(--bdr);
  }

  /* Weekly volume rows (mirrors Recovery's rec-row) */
  .muscle-list { border-top: 1px solid var(--bdr); margin-top: 0.25rem; }

  .vol-row {
    display: grid;
    grid-template-columns: 10px 140px 1fr 120px;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0;
    border-bottom: 1px solid var(--bdr);
  }

  .vol-name   { font-size: 0.9rem; font-weight: 500; color: var(--text); }
  .vol-count  { font-size: 0.9rem; font-weight: 600; color: var(--text); }
  .vol-mrv    { font-size: 0.78rem; font-weight: 400; color: var(--muted); }
  .vol-status { font-size: 0.82rem; font-weight: 600; text-align: right; }

  /* Spinner */
  .spinner-wrap { display: flex; justify-content: center; padding: 4rem 0; }

  .spinner {
    width: 24px; height: 24px;
    border: 2px solid var(--bdr-2);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  @media (max-width: 600px) {
    .page { padding: 1rem 1rem 3rem; }
    .lift-row { grid-template-columns: 10px 1fr; }
    .gauge-legend span:not(:first-child):not(:last-child) { display: none; }
    .rm-stats { grid-template-columns: 1fr 1fr; }
  }
</style>
