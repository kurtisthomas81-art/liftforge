<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let step = 1;
  let loading = true;
  let creating = false;
  let error = null;

  // Step 1
  let selectedDays = null;

  // Step 2
  let splitGroups = [];
  let selectedSplit = null;
  let isCustom = false;
  let customDays = [];   // [{ name: '', muscle_focus: [] }]

  // Step 3
  let selectedGoal = 'hypertrophy';
  let selectedWeeks = 5;
  let selectedPeriodization = 'standard';
  let selectedDuration = 60;
  let startDate = new Date().toISOString().slice(0, 10);
  let mesoName = '';
  let daysOfWeek = [];   // array of 0-6 per split day
  let experienceLevel = 'intermediate';

  // Step 3 (variant picker — new)
  let numVariants = 2;   // 1=A only, 2=A/B, 3=A/B/C

  // Step 5 (review — was step 4)
  let previewData = [];
  let previewLoading = false;
  let previewError = '';
  let editedDays = {};   // { dayIndex: [exerciseId, ...] } — tracks swaps

  // Swap modal
  let showSwapModal = false;
  let swapDayIdx = null;
  let swapExIdx = null;
  let swapMuscle = '';
  let swapSearch = '';
  let swapExercises = [];
  let allExercises = [];
  let loadingAllExercises = false;

  const DOW_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const ALL_MUSCLES = ['chest', 'back', 'quads', 'hamstrings', 'glutes', 'shoulders',
                       'biceps', 'triceps', 'calves', 'abs', 'lats', 'traps'];
  const GOALS = [
    { key: 'hypertrophy', label: 'Hypertrophy', desc: '8-12 reps, RIR 2' },
    { key: 'strength',    label: 'Strength',    desc: '3-6 reps, RIR 1' },
    { key: 'recomp',      label: 'Recomp',      desc: '10-15 reps, RIR 2-3' },
  ];
  const PERIODIZATIONS = [
    { key: 'standard', label: 'Standard',  desc: 'Fixed rep ranges, volume progresses week to week' },
    { key: 'linear',   label: 'Linear',    desc: 'High reps week 1 descend to low reps by final week' },
    { key: 'dup',      label: 'DUP',       desc: 'Rep ranges rotate session to session (hypertrophy / strength / volume)' },
    { key: 'block',    label: 'Block',     desc: 'Accumulation → Intensification → Peak phases' },
  ];

  onMount(async () => {
    try {
      const [raw, profile] = await Promise.all([
        api.programs.getSplits(),
        api.profile.get().catch(() => null),
      ]);
      splitGroups = raw;
      if (profile) {
        selectedDuration = profile.preferred_session_minutes ?? 60;
        experienceLevel = profile.experience_level ?? 'intermediate';
        if (experienceLevel === 'beginner') selectedPeriodization = 'linear';
      }
    } catch (e) {
      error = e.message;
    }
    loading = false;
    const now = new Date();
    mesoName = `Mesocycle ${now.toLocaleString('default', { month: 'long' })} ${now.getFullYear()}`;
  });

  function selectDays(n) {
    selectedDays = n;
    selectedSplit = null;
    isCustom = false;
    customDays = Array.from({ length: n }, (_, i) => ({ name: `Day ${i + 1}`, muscle_focus: [] }));
    daysOfWeek = Array.from({ length: n }, (_, i) => Math.min(i * Math.floor(7 / n), 6));
    step = 2;
  }

  function selectSplit(split) {
    isCustom = false;
    selectedSplit = split;
    step = 3;  // step 3 = variant picker
  }

  function selectCustom() {
    isCustom = true;
    selectedSplit = null;
    customDays = Array.from({ length: selectedDays }, (_, i) => ({ name: `Day ${i + 1}`, muscle_focus: [] }));
  }

  function toggleMuscleForDay(dayIdx, muscle) {
    const day = customDays[dayIdx];
    if (day.muscle_focus.includes(muscle)) {
      day.muscle_focus = day.muscle_focus.filter(m => m !== muscle);
    } else {
      day.muscle_focus = [...day.muscle_focus, muscle];
    }
    customDays = [...customDays];
  }

  function filteredSplits() {
    const group = splitGroups.find(g => g.days_per_week === selectedDays);
    return group ? group.templates : [];
  }

  function buildPayload() {
    const p = {
      goal: selectedGoal,
      weeks: selectedWeeks,
      periodization_type: selectedPeriodization,
      session_minutes: selectedDuration,
      start_date: startDate,
      name: mesoName,
      days_of_week: daysOfWeek,
      num_variants: numVariants,
    };
    if (isCustom) {
      p.custom_days = customDays;
    } else {
      p.split_slug = selectedSplit.slug;
    }
    return p;
  }

  async function goToReview() {
    step = 5;
    previewData = [];
    editedDays = {};
    previewError = '';
    previewLoading = true;
    try {
      previewData = await api.programs.previewMesocycle(buildPayload());
    } catch (e) {
      previewError = e.message;
    }
    previewLoading = false;
  }

  async function createMesocycle() {
    creating = true;
    error = null;
    try {
      const payload = buildPayload();
      if (Object.keys(editedDays).length > 0) {
        payload.day_exercises = editedDays;
      }
      await api.programs.createMesocycle(payload);
      goto('/program');
    } catch (e) {
      error = e.message;
    }
    creating = false;
  }

  async function openSwapModal(dayIdx, exIdx, muscle) {
    swapDayIdx = dayIdx;
    swapExIdx = exIdx;
    swapMuscle = muscle || '';
    swapSearch = '';
    showSwapModal = true;
    if (allExercises.length === 0) {
      loadingAllExercises = true;
      try {
        allExercises = await api.exercises.list();
      } catch (e) { /* ignore */ }
      loadingAllExercises = false;
    }
    filterSwap();
  }

  function filterSwap() {
    swapExercises = allExercises.filter(ex => {
      let muscles = ex.primary_muscles;
      if (typeof muscles === 'string') { try { muscles = JSON.parse(muscles); } catch { muscles = []; } }
      if (!Array.isArray(muscles)) muscles = [];
      const matchesMuscle = !swapMuscle || muscles.includes(swapMuscle);
      const matchesSearch = !swapSearch || ex.name.toLowerCase().includes(swapSearch.toLowerCase());
      return matchesMuscle && matchesSearch;
    });
  }

  function confirmSwap(newEx) {
    let muscles = newEx.primary_muscles;
    if (typeof muscles === 'string') { try { muscles = JSON.parse(muscles); } catch { muscles = []; } }
    if (!Array.isArray(muscles)) muscles = [];
    const primaryMuscle = muscles[0] || null;

    const day = previewData[swapDayIdx];
    const newExercises = day.exercises.map((ex, i) =>
      i === swapExIdx
        ? { ...ex, exercise_id: newEx.id, exercise_name: newEx.name, primary_muscle: primaryMuscle }
        : ex
    );

    previewData = previewData.map((d, i) =>
      i === swapDayIdx ? { ...d, exercises: newExercises } : d
    );

    editedDays = { ...editedDays, [swapDayIdx]: newExercises.map(e => e.exercise_id) };
    showSwapModal = false;
  }

  function stepLabel(n) {
    if (step > n) return '✓';
    return n;
  }
</script>

<svelte:head><title>Build Program — LiftForge</title></svelte:head>

<div style="max-width:720px;">
  <div class="flex items-center gap-3 mb-5">
    <a href="/program" class="btn-ghost btn-sm">← Back</a>
    <h2 style="font-size:20px; font-weight:700;">Build Mesocycle</h2>
  </div>

  <!-- Step indicator -->
  <div style="display:flex; align-items:center; gap:0; margin-bottom:28px;">
    {#each [1,2,3,4,5] as n}
      <div style="display:flex; align-items:center; flex:1;">
        <div style="width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; background:{step >= n ? 'var(--primary)' : 'var(--surface-2)'}; color:{step >= n ? '#000' : 'var(--text-muted)'}; border:2px solid {step >= n ? 'var(--primary)' : 'var(--border)'}; flex-shrink:0; transition:all 0.2s;">
          {stepLabel(n)}
        </div>
        {#if n < 5}
          <div style="flex:1; height:2px; background:{step > n ? 'var(--primary)' : 'var(--border)'}; transition:background 0.2s;"></div>
        {/if}
      </div>
    {/each}
  </div>

  {#if loading}
    <div class="flex items-center gap-3" style="padding:32px 0;">
      <div class="spinner"></div>
    </div>

  {:else if step === 1}
    <!-- Step 1: Days per week -->
    <div class="card">
      <div class="section-title mb-4">How many days per week?</div>
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        {#each [2, 3, 4, 5] as n}
          <button
            on:click={() => selectDays(n)}
            style="flex:1; min-width:80px; padding:20px 12px; border-radius:8px; border:2px solid {selectedDays === n ? 'var(--primary)' : 'var(--border)'}; background:{selectedDays === n ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:{selectedDays === n ? 'var(--primary)' : 'var(--text)'}; font-size:24px; font-weight:700; cursor:pointer; transition:all 0.15s;"
          >
            {n}
            <div style="font-size:11px; font-weight:400; margin-top:4px; color:var(--text-muted);">days / week</div>
          </button>
        {/each}
      </div>
    </div>

  {:else if step === 2}
    <!-- Step 2: Choose split -->
    <div class="card">
      <div class="flex items-center gap-3 mb-4">
        <button class="btn-ghost btn-sm" on:click={() => step = 1}>← Back</button>
        <div class="section-title">{selectedDays}-Day Splits</div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
        {#each filteredSplits() as split}
          <button
            on:click={() => selectSplit(split)}
            style="text-align:left; padding:16px; border-radius:8px; border:2px solid {selectedSplit?.slug === split.slug ? 'var(--primary)' : 'var(--border)'}; background:{selectedSplit?.slug === split.slug ? 'rgba(232,160,64,0.07)' : 'var(--surface-2)'}; cursor:pointer; transition:all 0.15s; position:relative;"
          >
            {#if split.is_recommended}
              <span style="position:absolute; top:8px; right:8px; font-size:14px;" title="Recommended">⭐</span>
            {/if}
            <div style="font-weight:600; font-size:13px; color:var(--text); margin-bottom:4px;">{split.name}</div>
            <div style="font-size:11px; color:var(--primary); margin-bottom:6px;">{split.frequency_note}</div>
            <div style="font-size:11px; color:var(--text-muted); line-height:1.5;">{split.description}</div>
          </button>
        {/each}

        <!-- Custom option -->
        <button
          on:click={selectCustom}
          style="text-align:left; padding:16px; border-radius:8px; border:2px solid {isCustom ? 'var(--primary)' : 'var(--border)'}; background:{isCustom ? 'rgba(232,160,64,0.07)' : 'var(--surface-2)'}; cursor:pointer; transition:all 0.15s;"
        >
          <div style="font-weight:600; font-size:13px; color:var(--text); margin-bottom:4px;">Custom Split →</div>
          <div style="font-size:11px; color:var(--text-muted);">Design your own day structure</div>
        </button>
      </div>

      <!-- Custom day editor -->
      {#if isCustom}
        <div style="margin-top:20px; border-top:1px solid var(--border); padding-top:20px;">
          <div class="section-title mb-3">Configure Days</div>
          {#each customDays as day, i}
            <div style="margin-bottom:16px; padding:12px; background:var(--surface-2); border-radius:6px; border:1px solid var(--border);">
              <input
                bind:value={day.name}
                placeholder="Day name (e.g. Push)"
                style="font-weight:600; margin-bottom:10px; width:100%;"
              />
              <div style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">Muscle focus:</div>
              <div style="display:flex; flex-wrap:wrap; gap:6px;">
                {#each ALL_MUSCLES as muscle}
                  <button
                    on:click={() => toggleMuscleForDay(i, muscle)}
                    style="padding:4px 10px; border-radius:3px; border:1px solid {day.muscle_focus.includes(muscle) ? 'var(--primary)' : 'var(--border)'}; background:{day.muscle_focus.includes(muscle) ? 'rgba(232,160,64,0.15)' : 'transparent'}; color:{day.muscle_focus.includes(muscle) ? 'var(--primary)' : 'var(--text-muted)'}; font-size:11px; cursor:pointer; text-transform:capitalize;"
                  >
                    {muscle}
                  </button>
                {/each}
              </div>
            </div>
          {/each}
          <button class="btn-primary" on:click={() => step = 3}>Continue →</button>
          <!-- step 3 is variant picker; custom flow also goes through it -->
        </div>
      {/if}
    </div>

  {:else if step === 3}
    <!-- Step 3: Variation style -->
    <div class="card">
      <div class="flex items-center gap-3 mb-4">
        <button class="btn-ghost btn-sm" on:click={() => step = 2}>← Back</button>
        <div class="section-title">Workout Variation</div>
      </div>

      <div style="margin-bottom:24px;">
        <label style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">How much exercise variety do you want?</label>
        <div style="display:flex; gap:10px; flex-direction:column;">
          {#each [
            { val: 1, label: 'A — No variation', desc: 'Same exercises every session. Best for pure beginners learning movement patterns.' },
            { val: 2, label: 'A/B rotation', desc: 'Two alternating workouts. Horizontal push/pull one session, vertical the next. Recommended.' },
            { val: 3, label: 'A/B/C rotation', desc: 'Three unique workouts cycling continuously. More variety across the mesocycle.' },
          ] as opt}
            <button
              on:click={() => numVariants = opt.val}
              style="text-align:left; padding:14px 16px; border-radius:8px; border:2px solid {numVariants === opt.val ? 'var(--primary)' : 'var(--border)'}; background:{numVariants === opt.val ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:var(--text); cursor:pointer; transition:all 0.15s;"
            >
              <div style="font-weight:700; font-size:13px; color:{numVariants === opt.val ? 'var(--primary)' : 'var(--text)'}; margin-bottom:3px;">{opt.label}</div>
              <div style="font-size:11px; color:var(--text-muted); line-height:1.5;">{opt.desc}</div>
            </button>
          {/each}
        </div>
        <div style="font-size:11px; color:var(--text-faint); margin-top:10px;">
          Sessions loop continuously by workout index — A/B with 3 days/week gives A→B→A, then B→A→B the next week.
        </div>
      </div>

      <button class="btn-primary" on:click={() => step = 4}>Continue →</button>
    </div>

  {:else if step === 4}
    <!-- Step 4: Goal & duration (was step 3) -->
    <div class="card">
      <div class="flex items-center gap-3 mb-4">
        <button class="btn-ghost btn-sm" on:click={() => step = 3}>← Back</button>
        <div class="section-title">Goal & Duration</div>
      </div>

      <!-- Goal -->
      <div style="margin-bottom:20px;">
        <label style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Training Goal</label>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          {#each GOALS as goal}
            <button
              on:click={() => selectedGoal = goal.key}
              style="flex:1; min-width:100px; padding:14px 10px; border-radius:6px; border:2px solid {selectedGoal === goal.key ? 'var(--primary)' : 'var(--border)'}; background:{selectedGoal === goal.key ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:{selectedGoal === goal.key ? 'var(--primary)' : 'var(--text)'}; cursor:pointer; transition:all 0.15s; text-align:center;"
            >
              <div style="font-weight:700; margin-bottom:4px;">{goal.label}</div>
              <div style="font-size:11px; opacity:0.8;">{goal.desc}</div>
            </button>
          {/each}
        </div>
      </div>

      <!-- Session Duration -->
      <div style="margin-bottom:20px;">
        <label style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">
          Session Duration
          <span style="font-size:11px; color:var(--text-faint); margin-left:4px;">caps exercise count to fit your schedule</span>
        </label>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          {#each [30, 45, 60, 75, 90] as mins}
            <button
              on:click={() => selectedDuration = mins}
              style="padding:10px 16px; border-radius:6px; border:2px solid {selectedDuration === mins ? 'var(--primary)' : 'var(--border)'}; background:{selectedDuration === mins ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:{selectedDuration === mins ? 'var(--primary)' : 'var(--text)'}; font-weight:700; font-size:13px; cursor:pointer; transition:all 0.15s;"
            >{mins} min</button>
          {/each}
        </div>
      </div>

      <!-- Periodization -->
      <div style="margin-bottom:20px;">
        <label style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Periodization Style</label>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
          {#each PERIODIZATIONS as p}
            {@const locked = experienceLevel === 'beginner' && (p.key === 'dup' || p.key === 'block')}
            <button
              on:click={() => { if (!locked) selectedPeriodization = p.key; }}
              title={locked ? 'Unlocks at Intermediate level' : ''}
              style="text-align:left; padding:12px; border-radius:6px; border:2px solid {selectedPeriodization === p.key ? 'var(--primary)' : 'var(--border)'}; background:{selectedPeriodization === p.key ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:{locked ? 'var(--text-faint)' : selectedPeriodization === p.key ? 'var(--primary)' : 'var(--text)'}; cursor:{locked ? 'not-allowed' : 'pointer'}; transition:all 0.15s; opacity:{locked ? 0.5 : 1}; position:relative;"
            >
              <div style="font-weight:700; font-size:13px; margin-bottom:3px;">{p.label}{locked ? ' 🔒' : ''}</div>
              <div style="font-size:11px; opacity:0.75; line-height:1.4;">{p.desc}</div>
            </button>
          {/each}
        </div>
        {#if experienceLevel === 'beginner'}
          <div style="font-size:11px; color:var(--text-faint); margin-top:6px;">DUP & Block unlock at Intermediate. Linear is recommended to build your base.</div>
        {/if}
      </div>

      <!-- Weeks -->
      <div style="margin-bottom:20px;">
        <label style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Duration (weeks)</label>
        <div style="display:flex; gap:10px;">
          {#each [4, 5, 6] as w}
            <button
              on:click={() => selectedWeeks = w}
              style="padding:10px 20px; border-radius:6px; border:2px solid {selectedWeeks === w ? 'var(--primary)' : 'var(--border)'}; background:{selectedWeeks === w ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:{selectedWeeks === w ? 'var(--primary)' : 'var(--text)'}; font-weight:700; cursor:pointer; transition:all 0.15s;"
            >
              {w} weeks
            </button>
          {/each}
        </div>
        <div style="font-size:11px; color:var(--text-faint); margin-top:6px;">Week {selectedWeeks} will be a deload week</div>
      </div>

      <!-- Start date -->
      <div style="margin-bottom:20px;">
        <label for="startDate" style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Start Date</label>
        <input id="startDate" type="date" bind:value={startDate} style="width:200px;" />
      </div>

      <!-- Mesocycle name -->
      <div style="margin-bottom:20px;">
        <label for="mesoName" style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Mesocycle Name</label>
        <input id="mesoName" bind:value={mesoName} placeholder="e.g. Mesocycle April 2026" style="width:100%; max-width:400px;" />
      </div>

      <!-- Day of week assignment -->
      <div style="margin-bottom:24px;">
        <label style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Training Days</label>
        {#each (isCustom ? customDays : (selectedSplit?.days ?? [])) as day, i}
          <div class="flex items-center gap-3" style="margin-bottom:8px;">
            <span style="font-size:13px; color:var(--text); min-width:130px;">{day.name}</span>
            <select bind:value={daysOfWeek[i]} style="width:120px;">
              {#each DOW_LABELS as label, di}
                <option value={di}>{label}</option>
              {/each}
            </select>
          </div>
        {/each}
      </div>

      <button class="btn-primary" on:click={goToReview}>Review Exercises →</button>
    </div>

  {:else if step === 5}
    <!-- Step 5: Review exercises (was step 4) -->
    <div class="card">
      <div class="flex items-center gap-3 mb-4">
        <button class="btn-ghost btn-sm" on:click={() => step = 4}>← Back</button>
        <div class="section-title">Review Exercises</div>
      </div>

      <!-- Compact settings summary -->
      <div style="display:grid; grid-template-columns:auto 1fr; gap:4px 16px; margin-bottom:20px; font-size:12px; padding:12px; background:var(--surface-2); border-radius:6px; border:1px solid var(--border);">
        <span style="color:var(--text-muted);">Name</span><span style="font-weight:600; color:var(--text);">{mesoName}</span>
        <span style="color:var(--text-muted);">Split</span><span style="color:var(--text);">{isCustom ? 'Custom' : selectedSplit?.name}</span>
        <span style="color:var(--text-muted);">Goal</span><span style="text-transform:capitalize; color:var(--text);">{selectedGoal}</span>
        <span style="color:var(--text-muted);">Duration</span><span style="color:var(--text);">{selectedWeeks} weeks · week {selectedWeeks} = deload · starts {startDate}</span>
        <span style="color:var(--text-muted);">Session</span><span style="color:var(--text);">{selectedDuration} min · {experienceLevel} level</span>
        <span style="color:var(--text-muted);">Variation</span><span style="color:var(--text);">{numVariants === 1 ? 'A — same every session' : numVariants === 2 ? 'A/B rotation' : 'A/B/C rotation'}</span>
      </div>

      <!-- Exercise preview by day -->
      <div style="margin-bottom:20px;">
        <div style="font-size:13px; font-weight:600; color:var(--text); margin-bottom:12px; display:flex; align-items:center; gap:8px;">
          Exercises
          <span style="font-size:11px; font-weight:400; color:var(--text-muted);">week 1 targets · swap any before generating</span>
        </div>

        {#if previewLoading}
          <div style="display:flex; align-items:center; gap:10px; padding:20px 0; color:var(--text-muted); font-size:13px;">
            <div class="spinner" style="width:16px; height:16px;"></div>
            Building exercise plan...
          </div>
        {:else if previewError}
          <div style="color:var(--danger); font-size:12px; margin-bottom:8px;">{previewError}</div>
        {:else}
          {#each previewData as day}
            <div style="margin-bottom:18px;">
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px; padding-bottom:6px; border-bottom:1px solid var(--border);">
                <span style="font-size:12px; font-weight:700; color:var(--primary);">{day.day_name}</span>
                {#if day.variant && numVariants > 1}
                  <span style="padding:1px 7px; border-radius:10px; background:rgba(232,160,64,0.18); color:var(--primary); font-size:10px; font-weight:700; border:1px solid rgba(232,160,64,0.3);">{day.variant}</span>
                {/if}
                <div style="display:flex; gap:4px; flex-wrap:wrap;">
                  {#each day.muscle_focus as m}
                    <span style="padding:2px 6px; border-radius:3px; background:var(--surface-2); color:var(--text-muted); font-size:10px; text-transform:capitalize;">{m}</span>
                  {/each}
                </div>
              </div>
              {#if day.exercises.length === 0}
                <div style="font-size:12px; color:var(--text-faint); padding:6px 0;">No exercises matched your equipment for this day.</div>
              {:else}
                {#each day.exercises as ex, exIdx}
                  <div style="display:flex; align-items:center; gap:8px; padding:7px 0; border-bottom:1px solid var(--border-faint);">
                    <span style="flex:1; font-size:13px; color:var(--text);">{ex.exercise_name}</span>
                    <span style="font-size:11px; color:var(--text-muted); white-space:nowrap;">{ex.target_sets}×{ex.target_reps_min}–{ex.target_reps_max} @RIR{ex.target_rir}</span>
                    <button
                      on:click={() => openSwapModal(day.day_index, exIdx, ex.primary_muscle)}
                      title="Swap exercise"
                      style="padding:3px 8px; border-radius:4px; border:1px solid var(--border); background:var(--surface-2); color:var(--text-muted); font-size:12px; cursor:pointer; flex-shrink:0;"
                    >⇄</button>
                  </div>
                {/each}
              {/if}
            </div>
          {/each}
        {/if}
      </div>

      {#if error}
        <div style="color:var(--danger); font-size:13px; margin-bottom:12px;">{error}</div>
      {/if}

      <button class="btn-primary" on:click={createMesocycle} disabled={creating || previewLoading}
        style="padding:12px 28px; font-size:15px;">
        {creating ? 'Building...' : 'Generate Mesocycle'}
      </button>
    </div>
  {/if}
</div>

<!-- Swap exercise modal -->
{#if showSwapModal}
  <div
    style="position:fixed; inset:0; background:rgba(0,0,0,0.7); z-index:1000; display:flex; align-items:flex-end; justify-content:center;"
    on:click|self={() => showSwapModal = false}
    role="dialog" aria-modal="true"
  >
    <div style="background:var(--surface); border-radius:12px 12px 0 0; width:100%; max-width:600px; max-height:72vh; display:flex; flex-direction:column; padding:20px;">
      <div style="font-size:14px; font-weight:700; color:var(--text); margin-bottom:14px;">Swap Exercise</div>

      <input
        bind:value={swapSearch}
        on:input={filterSwap}
        placeholder="Search exercises..."
        style="margin-bottom:10px;"
      />

      <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px;">
        <button
          on:click={() => { swapMuscle = ''; filterSwap(); }}
          style="padding:3px 10px; border-radius:12px; border:1px solid {swapMuscle === '' ? 'var(--primary)' : 'var(--border)'}; background:{swapMuscle === '' ? 'rgba(232,160,64,0.15)' : 'transparent'}; color:{swapMuscle === '' ? 'var(--primary)' : 'var(--text-muted)'}; font-size:11px; cursor:pointer;"
        >All</button>
        {#each ALL_MUSCLES as m}
          <button
            on:click={() => { swapMuscle = m; filterSwap(); }}
            style="padding:3px 10px; border-radius:12px; border:1px solid {swapMuscle === m ? 'var(--primary)' : 'var(--border)'}; background:{swapMuscle === m ? 'rgba(232,160,64,0.15)' : 'transparent'}; color:{swapMuscle === m ? 'var(--primary)' : 'var(--text-muted)'}; font-size:11px; cursor:pointer; text-transform:capitalize;"
          >{m}</button>
        {/each}
      </div>

      {#if loadingAllExercises}
        <div class="spinner" style="width:18px; height:18px; margin:20px auto;"></div>
      {:else}
        <div style="overflow-y:auto; flex:1;">
          {#each swapExercises.slice(0, 80) as ex}
            <button
              on:click={() => confirmSwap(ex)}
              style="width:100%; text-align:left; padding:10px 8px; border-bottom:1px solid var(--border-faint); background:transparent; cursor:pointer; display:flex; gap:10px; align-items:center; border-radius:0;"
            >
              <div style="flex:1;">
                <div style="font-size:13px; font-weight:500; color:var(--text);">{ex.name}</div>
                <div style="font-size:11px; color:var(--text-muted); text-transform:capitalize;">
                  {Array.isArray(ex.primary_muscles) ? ex.primary_muscles.join(', ') : (ex.primary_muscles ?? '')}
                  {ex.mechanics ? ' · ' + ex.mechanics : ''}
                </div>
              </div>
            </button>
          {/each}
          {#if swapExercises.length === 0}
            <div style="color:var(--text-muted); font-size:13px; padding:16px 0;">No exercises found.</div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
{/if}
