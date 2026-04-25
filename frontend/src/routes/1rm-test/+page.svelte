<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { api } from '$lib/api.js';

  let step = 1;

  // Step 1
  let searchQuery = '';
  let searchResults = [];
  let searchLoading = false;
  let selectedExercise = null;
  let existingPR = null;
  let searchTimer;

  // Step 2
  let startMode = 'estimate';
  let estimatedMax = '';
  let repSetWeight = '';
  let repSetReps = 5;

  // Step 3
  let sessionId = null;
  let currentSetIdx = 0;
  let actualWeight = '';
  let actualReps = 5;
  let logging = false;
  let maxAttemptSet = null;

  const WARMUP_STEPS = [
    { pct: 0.40, reps: 5, type: 'warmup' },
    { pct: 0.50, reps: 5, type: 'warmup' },
    { pct: 0.60, reps: 3, type: 'warmup' },
    { pct: 0.70, reps: 2, type: 'warmup' },
    { pct: 0.80, reps: 1, type: 'warmup' },
    { pct: 0.90, reps: 1, type: 'warmup' },
    { pct: 1.00, reps: 1, type: 'straight' },
  ];

  const REST_HINT = ['1 min', '1 min', '90 sec', '2 min', '3 min', '4 min', '5+ min'];

  // Step 4
  let e1rm = null;
  let newPRs = [];
  let isNewPR = false;

  onMount(async () => {
    const exerciseId = $page.url.searchParams.get('exercise');
    if (exerciseId) {
      try {
        const ex = await api.exercises.get(Number(exerciseId));
        await selectExercise(ex);
      } catch {}
    }
  });

  function round25(val) {
    return Math.round(val / 2.5) * 2.5;
  }

  function epley(weight, reps) {
    if (reps <= 1) return weight;
    return weight * (1 + reps / 30);
  }

  $: workingMax = (() => {
    if (startMode === 'estimate') return parseFloat(estimatedMax) || 0;
    return epley(parseFloat(repSetWeight) || 0, parseInt(repSetReps) || 1);
  })();

  $: warmupRamp = WARMUP_STEPS.map(s => ({
    ...s,
    targetWeight: round25(workingMax * s.pct),
  }));

  function onSearchInput() {
    clearTimeout(searchTimer);
    if (!searchQuery.trim()) { searchResults = []; return; }
    searchTimer = setTimeout(async () => {
      searchLoading = true;
      try { searchResults = await api.exercises.list({ search: searchQuery }); }
      catch { searchResults = []; }
      searchLoading = false;
    }, 300);
  }

  async function selectExercise(ex) {
    selectedExercise = ex;
    existingPR = null;
    try {
      const history = await api.history.exerciseProgression(ex.id);
      if (history.length) existingPR = Math.max(...history.map(d => d.estimated_1rm)).toFixed(1);
    } catch {}
    step = 2;
  }

  async function buildWarmup() {
    if (workingMax <= 0) return;
    try {
      const sess = await api.sessions.create({ name: `1RM Test — ${selectedExercise.name}` });
      sessionId = sess.id;
    } catch { return; }
    resetCurrentSet(0);
    step = 3;
  }

  function resetCurrentSet(idx) {
    actualWeight = String(warmupRamp[idx].targetWeight);
    actualReps = String(warmupRamp[idx].reps);
  }

  async function logSet() {
    logging = true;
    const s = warmupRamp[currentSetIdx];
    try {
      await api.sessions.addSet(sessionId, {
        exercise_id: selectedExercise.id,
        set_number: currentSetIdx + 1,
        weight: parseFloat(actualWeight),
        reps: parseInt(actualReps),
        rir: s.type === 'warmup' ? 4 : 0,
        set_type: s.type,
      });
      if (s.type === 'straight') {
        maxAttemptSet = { weight: parseFloat(actualWeight), reps: parseInt(actualReps) };
        await finishTest();
      } else {
        currentSetIdx += 1;
        resetCurrentSet(currentSetIdx);
      }
    } catch {}
    logging = false;
  }

  function skipSet() {
    currentSetIdx += 1;
    resetCurrentSet(currentSetIdx);
  }

  async function finishTest() {
    try {
      await api.sessions.finish(sessionId);
      const result = await api.prs.checkSession(sessionId);
      newPRs = result || [];
      isNewPR = newPRs.some(pr => pr.exercise_id === selectedExercise.id);
      e1rm = epley(maxAttemptSet.weight, maxAttemptSet.reps);
    } catch {}
    step = 4;
  }
</script>

<svelte:head><title>1RM Test — LiftForge</title></svelte:head>

<div style="max-width:560px;">
  <div class="flex items-center gap-3 mb-5">
    {#if step === 1}
      <a href="/exercises" class="btn-ghost btn-sm">← Back</a>
    {:else if step === 2}
      <button class="btn-ghost btn-sm" on:click={() => step = 1}>← Back</button>
    {/if}
    <h2 style="font-size:20px; font-weight:700;">1RM Test Protocol</h2>
  </div>

  <!-- Step indicator -->
  <div style="display:flex; align-items:center; gap:0; margin-bottom:28px;">
    {#each [1,2,3,4] as n}
      <div style="display:flex; align-items:center; flex:1;">
        <div style="width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700;
          background:{step > n ? 'var(--primary)' : step === n ? 'var(--primary)' : 'var(--surface-2)'};
          color:{step >= n ? '#000' : 'var(--text-muted)'};
          border:2px solid {step >= n ? 'var(--primary)' : 'var(--border)'};
          flex-shrink:0; transition:all 0.2s;">
          {step > n ? '✓' : n}
        </div>
        {#if n < 4}
          <div style="flex:1; height:2px; background:{step > n ? 'var(--primary)' : 'var(--border)'}; transition:background 0.2s;"></div>
        {/if}
      </div>
    {/each}
  </div>

  <!-- ── Step 1: Pick exercise ── -->
  {#if step === 1}
    <div class="card">
      <div class="section-title mb-4">Select an Exercise</div>
      <div class="search-wrap" style="margin-bottom:12px;">
        <span class="search-icon">⊞</span>
        <input
          bind:value={searchQuery}
          on:input={onSearchInput}
          placeholder="Search exercises…"
          autofocus
        />
      </div>

      {#if searchLoading}
        <div class="flex items-center gap-2" style="padding:8px 0;"><div class="spinner"></div></div>
      {:else if searchResults.length}
        <div class="result-list">
          {#each searchResults.slice(0, 12) as ex}
            <button class="result-row" on:click={() => selectExercise(ex)}>
              <div>
                <div style="font-weight:600; font-size:14px;">{ex.name}</div>
                <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">{ex.primary_muscles?.join(', ')}</div>
              </div>
              <span style="font-size:12px; color:var(--text-faint);">→</span>
            </button>
          {/each}
        </div>
      {:else if searchQuery.length > 1}
        <div style="font-size:13px; color:var(--text-muted); padding:8px 0;">No exercises found.</div>
      {:else}
        <div style="font-size:12px; color:var(--text-faint); padding:8px 0;">Type to search the exercise library.</div>
      {/if}
    </div>

  <!-- ── Step 2: Starting point ── -->
  {:else if step === 2}
    <div class="card">
      <div class="section-title mb-1">{selectedExercise.name}</div>
      {#if existingPR}
        <div style="font-size:12px; color:var(--text-muted); margin-bottom:20px;">Current best: <strong style="color:var(--primary);">{existingPR} lbs</strong> est. 1RM</div>
      {:else}
        <div style="font-size:12px; color:var(--text-muted); margin-bottom:20px;">No previous 1RM on record.</div>
      {/if}

      <!-- Mode toggle -->
      <div style="display:flex; gap:8px; margin-bottom:20px;">
        <button
          on:click={() => startMode = 'estimate'}
          style="flex:1; padding:10px; border-radius:6px; border:2px solid {startMode === 'estimate' ? 'var(--primary)' : 'var(--border)'}; background:{startMode === 'estimate' ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:{startMode === 'estimate' ? 'var(--primary)' : 'var(--text)'}; font-size:12px; font-weight:600; cursor:pointer; transition:all 0.15s;">
          I have an estimate
        </button>
        <button
          on:click={() => startMode = 'repset'}
          style="flex:1; padding:10px; border-radius:6px; border:2px solid {startMode === 'repset' ? 'var(--primary)' : 'var(--border)'}; background:{startMode === 'repset' ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:{startMode === 'repset' ? 'var(--primary)' : 'var(--text)'}; font-size:12px; font-weight:600; cursor:pointer; transition:all 0.15s;">
          Start from a rep set
        </button>
      </div>

      {#if startMode === 'estimate'}
        <div style="margin-bottom:20px;">
          <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:6px;">Estimated 1RM (lbs)</label>
          <input type="number" bind:value={estimatedMax} placeholder="e.g. 225" style="width:140px; font-size:22px; font-weight:700;" />
        </div>
      {:else}
        <div style="margin-bottom:12px;">
          <label style="font-size:12px; color:var(--text-muted); display:block; margin-bottom:6px;">A weight you can lift for multiple reps</label>
          <div class="flex items-center gap-3">
            <div>
              <input type="number" bind:value={repSetWeight} placeholder="135" style="width:100px; font-size:18px; font-weight:700;" />
              <div style="font-size:10px; color:var(--text-faint); margin-top:2px;">lbs</div>
            </div>
            <div style="font-size:18px; color:var(--text-faint);">×</div>
            <div>
              <input type="number" bind:value={repSetReps} min="2" max="20" style="width:70px; font-size:18px; font-weight:700;" />
              <div style="font-size:10px; color:var(--text-faint); margin-top:2px;">reps</div>
            </div>
          </div>
        </div>
      {/if}

      {#if workingMax > 0}
        <div style="background:var(--surface-2); border:1px solid var(--border); border-radius:8px; padding:14px 16px; margin-bottom:20px;">
          <div style="font-size:11px; color:var(--text-muted); margin-bottom:2px;">Working max</div>
          <div style="font-size:28px; font-weight:800; color:var(--primary);">{workingMax.toFixed(1)} <span style="font-size:14px; font-weight:400;">lbs</span></div>
          <div style="font-size:11px; color:var(--text-faint); margin-top:4px;">Warmup ramp: {warmupRamp.map(s => s.targetWeight).join(' → ')} lbs</div>
        </div>

        <button class="btn-primary" on:click={buildWarmup} style="width:100%; padding:13px; font-size:15px;">
          Build Warmup →
        </button>
      {/if}
    </div>

  <!-- ── Step 3: Guided warmup ── -->
  {:else if step === 3}
    {@const currentStep = warmupRamp[currentSetIdx]}
    {@const isMaxAttempt = currentStep.type === 'straight'}

    <div class="card">
      <!-- Progress dots -->
      <div style="display:flex; align-items:center; gap:6px; margin-bottom:20px;">
        {#each warmupRamp as s, i}
          <div style="flex:1; height:4px; border-radius:2px; background:{i < currentSetIdx ? 'var(--primary)' : i === currentSetIdx ? 'var(--primary)' : 'var(--border)'}; opacity:{i === currentSetIdx ? 1 : i < currentSetIdx ? 0.6 : 0.3}; transition:all 0.2s;"></div>
        {/each}
      </div>

      <div style="font-size:11px; color:var(--text-muted); margin-bottom:4px;">
        {isMaxAttempt ? 'MAX ATTEMPT' : `Warmup set ${currentSetIdx + 1} of 6`}
      </div>
      <div style="font-size:13px; font-weight:600; color:var(--text); margin-bottom:20px;">
        {selectedExercise.name}
      </div>

      <!-- Set card -->
      <div style="background:{isMaxAttempt ? 'rgba(232,160,64,0.08)' : 'var(--surface-2)'}; border:2px solid {isMaxAttempt ? 'var(--primary)' : 'var(--border)'}; border-radius:10px; padding:20px; margin-bottom:20px;">
        <div style="font-size:11px; color:var(--text-muted); margin-bottom:14px; text-transform:uppercase; letter-spacing:0.06em;">
          Target: {currentStep.targetWeight} lbs × {currentStep.reps} rep{currentStep.reps > 1 ? 's' : ''}
          {#if !isMaxAttempt}
            · Rest {REST_HINT[currentSetIdx]}
          {/if}
        </div>

        <div class="flex items-center gap-4">
          <div>
            <label style="font-size:10px; color:var(--text-muted); display:block; margin-bottom:4px;">ACTUAL WEIGHT</label>
            <input type="number" bind:value={actualWeight} style="width:110px; font-size:24px; font-weight:800; color:{isMaxAttempt ? 'var(--primary)' : 'var(--text)'};" />
            <span style="font-size:12px; color:var(--text-faint); margin-left:4px;">lbs</span>
          </div>
          <div style="font-size:20px; color:var(--text-faint);">×</div>
          <div>
            <label style="font-size:10px; color:var(--text-muted); display:block; margin-bottom:4px;">ACTUAL REPS</label>
            <input type="number" bind:value={actualReps} min="1" style="width:70px; font-size:24px; font-weight:800; color:{isMaxAttempt ? 'var(--primary)' : 'var(--text)'};" />
          </div>
        </div>
      </div>

      <div class="flex gap-3">
        <button
          class="btn-primary"
          on:click={logSet}
          disabled={logging}
          style="flex:1; padding:13px; font-size:14px; font-weight:700;">
          {logging ? '...' : isMaxAttempt ? 'Log Max Attempt ✓' : 'Done →'}
        </button>
        {#if !isMaxAttempt}
          <button class="btn-ghost" on:click={skipSet} style="padding:13px 16px; font-size:13px;">
            Skip
          </button>
        {/if}
      </div>
    </div>

  <!-- ── Step 4: Result ── -->
  {:else if step === 4}
    <div class="card" style="text-align:center;">
      {#if isNewPR}
        <div style="font-size:13px; font-weight:700; color:var(--primary); background:rgba(232,160,64,0.12); border:1px solid rgba(232,160,64,0.3); border-radius:6px; padding:6px 14px; display:inline-block; margin-bottom:16px; letter-spacing:0.06em;">
          NEW PR
        </div>
      {/if}

      <div style="font-size:13px; color:var(--text-muted); margin-bottom:6px;">{selectedExercise.name}</div>
      <div style="font-size:60px; font-weight:900; color:var(--primary); line-height:1; margin-bottom:4px;">
        {e1rm ? e1rm.toFixed(1) : '—'}
      </div>
      <div style="font-size:14px; color:var(--text-muted); margin-bottom:6px;">lbs estimated 1RM</div>
      <div style="font-size:12px; color:var(--text-faint); margin-bottom:4px;">
        from {maxAttemptSet?.weight} lbs × {maxAttemptSet?.reps} rep{maxAttemptSet?.reps > 1 ? 's' : ''}
      </div>

      {#if existingPR}
        <div style="font-size:12px; color:var(--text-muted); margin-top:8px; margin-bottom:24px;">
          Previous best: {existingPR} lbs
          {#if e1rm && parseFloat(existingPR) > 0}
            <span style="color:{e1rm >= parseFloat(existingPR) ? 'var(--primary)' : 'var(--text-faint)'};">
              ({e1rm >= parseFloat(existingPR) ? '+' : ''}{(e1rm - parseFloat(existingPR)).toFixed(1)} lbs)
            </span>
          {/if}
        </div>
      {:else}
        <div style="margin-bottom:24px;"></div>
      {/if}

      <div style="display:flex; flex-direction:column; gap:10px;">
        <a href="/exercises" class="btn-primary" style="display:block; text-align:center; padding:13px; text-decoration:none; font-size:14px;">
          Done
        </a>
        <a href="/program/builder" class="btn-ghost" style="display:block; text-align:center; padding:13px; text-decoration:none; font-size:14px;">
          Start New Mesocycle →
        </a>
      </div>
    </div>
  {/if}
</div>

<style>
  .result-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    max-height: 380px;
    overflow-y: auto;
  }
  .result-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 8px;
    border-radius: 6px;
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: left;
    width: 100%;
    transition: background 0.1s;
  }
  .result-row:hover { background: var(--surface-2); }
</style>
