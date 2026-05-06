<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { activeSession, refreshActiveSession, getElapsed, sessionPlan } from '$lib/stores.js';
  import { autoSessionName, formatDate } from '$lib/utils.js';

  let session = null;
  let exercises = [];
  let loading = true;
  let elapsed = '0:00';
  let intervalId;
  let editingName = false;
  let sessionName = '';
  let finishing = false;
  let defaultRestSeconds = 90;

  // Per-set "done" toggle (local visual state — actual data in weight/reps fields)
  let doneIds = new Set();
  let rpeSetId = null; // which set has the inline RPE picker open

  // Exercise search modal
  let showExerciseModal = false;
  let exerciseSearch = '';
  let exerciseFilter = '';
  let allExercises = [];
  let filteredExercises = [];
  let affectedExercises = {};  // { exercise_id: [body_parts] }

  // Previous session reference per exercise
  let prevSessions = {};
  let showPrev = {};

  // Overload suggestions
  let overloadSuggestions = {};

  // Rest timer (inline card)
  let restTimer = null;
  let restExerciseName = '';
  let restRemaining = 0;
  let restRunning = false;
  let restDismissTimeout = null;

  // Readiness check-in modal
  let showReadinessModal = false;
  let readinessRating = null;
  let pendingSessionCreate = false;

  // Save as template
  let showSaveTemplateModal = false;
  let saveTemplateName = '';
  let savingTemplate = false;

  // Post-session RPE
  let showRpeModal = false;
  let finishedSessionId = null;
  let sessionRpe = null;
  let submittingRpe = false;

  // Session note
  let showNote = false;
  let sessionNote = '';

  onMount(async () => {
    await refreshActiveSession();
    session = $activeSession;

    try {
      const profile = await api.profile.get();
      defaultRestSeconds = profile.default_rest_seconds ?? 90;
    } catch {}

    if (session) {
      await loadSession();
      intervalId = setInterval(() => {
        elapsed = getElapsed(session.started_at);
      }, 1000);
    }
    loading = false;
  });

  onDestroy(() => {
    clearInterval(intervalId);
    clearRestTimer();
  });

  async function loadSession() {
    if (!session) return;
    const detail = await api.sessions.get(session.id);
    session = { ...session, ...detail };
    exercises = detail.exercises || [];
    sessionName = session.name || '';
    sessionNote = session.notes || '';
    elapsed = getElapsed(session.started_at);
    for (const group of exercises) {
      loadOverloadSuggestion(group.exercise_id, group.exercise_name);
    }
  }

  async function loadOverloadSuggestion(exerciseId) {
    try {
      const prev = await api.history.lastSession(exerciseId);
      if (!prev?.sets?.length) return;
      const workingSets = prev.sets.filter(s => s.weight && s.reps);
      if (!workingSets.length) return;
      const best = workingSets.reduce((a, b) => a.weight > b.weight ? a : b);
      let suggestion;
      if (best.rir != null) {
        if (best.rir >= 2) {
          const newW = Math.round(best.weight * 1.025 / 2.5) * 2.5;
          suggestion = `Last: ${best.weight}×${best.reps} RIR ${best.rir} → Target: ${newW} lb`;
        } else {
          suggestion = `Last: ${best.weight}×${best.reps} RIR ${best.rir} — hold or reduce reps`;
        }
      } else {
        suggestion = `Last session: ${best.weight}×${best.reps}`;
      }
      overloadSuggestions = { ...overloadSuggestions, [exerciseId]: suggestion };
    } catch {}
  }

  // ── Rest Timer ──────────────────────────────────────────────────────────────
  function startRestTimer(exerciseName) {
    clearRestTimer();
    restExerciseName = exerciseName;
    restRemaining = defaultRestSeconds;
    restRunning = true;
    restTimer = setInterval(() => {
      restRemaining -= 1;
      if (restRemaining <= 0) {
        restRemaining = 0;
        clearRestTimer();
        restDismissTimeout = setTimeout(() => { restRunning = false; }, 10000);
      }
    }, 1000);
  }

  function clearRestTimer() {
    if (restTimer) { clearInterval(restTimer); restTimer = null; }
    if (restDismissTimeout) { clearTimeout(restDismissTimeout); restDismissTimeout = null; }
  }

  function dismissRestTimer() { clearRestTimer(); restRunning = false; }

  function addRestTime(seconds) {
    restRemaining = Math.max(0, restRemaining + seconds);
    if (!restTimer && restRunning) {
      restTimer = setInterval(() => {
        restRemaining -= 1;
        if (restRemaining <= 0) {
          restRemaining = 0;
          clearRestTimer();
          restDismissTimeout = setTimeout(() => { restRunning = false; }, 10000);
        }
      }, 1000);
    }
  }

  $: restCirc = 2 * Math.PI * 24;
  $: restOffset = restCirc * (restRemaining / defaultRestSeconds);
  $: restColor = restRemaining <= 15 ? 'var(--accent)' : 'var(--success)';

  // ── Set "done" toggle ───────────────────────────────────────────────────────
  function toggleDone(setId, exerciseName, weight, reps) {
    if (doneIds.has(setId)) {
      doneIds.delete(setId);
      if (rpeSetId === setId) rpeSetId = null;
    } else {
      doneIds.add(setId);
      if (weight && reps) {
        startRestTimer(exerciseName);
        rpeSetId = setId;
      }
    }
    doneIds = new Set(doneIds);
  }

  // ── Session start ──────────────────────────────────────────────────────────
  function requestStartSession() {
    readinessRating = null;
    showReadinessModal = true;
  }

  async function confirmStartSession() {
    showReadinessModal = false;
    pendingSessionCreate = true;
    const s = await api.sessions.create({
      name: autoSessionName(),
      readiness_rating: readinessRating,
    });
    await refreshActiveSession();
    session = $activeSession;
    exercises = [];
    sessionName = session.name || '';
    elapsed = getElapsed(session.started_at);
    intervalId = setInterval(() => { elapsed = getElapsed(session.started_at); }, 1000);
    pendingSessionCreate = false;
  }

  async function finishSession() {
    if (!confirm('Finish this session?')) return;
    finishing = true;
    const sid = session.id;
    if (sessionNote) await api.sessions.update(sid, { notes: sessionNote });
    await api.sessions.finish(sid);
    try { await api.prs.checkSession(sid); } catch {}
    await refreshActiveSession();
    dismissRestTimer();
    clearInterval(intervalId);
    session = null;
    exercises = [];
    doneIds = new Set();
    finishing = false;
    finishedSessionId = sid;
    sessionRpe = null;
    showRpeModal = true;
  }

  async function submitRpe() {
    submittingRpe = true;
    if (sessionRpe !== null && finishedSessionId) {
      try { await api.sessions.update(finishedSessionId, { post_session_rpe: sessionRpe }); } catch {}
    }
    showRpeModal = false;
    submittingRpe = false;
    goto('/');
  }

  async function saveName() {
    if (!session) return;
    await api.sessions.update(session.id, { name: sessionName });
    session = { ...session, name: sessionName };
    editingName = false;
  }

  async function openSaveTemplate() {
    saveTemplateName = session?.name || '';
    showSaveTemplateModal = true;
  }

  async function confirmSaveTemplate() {
    if (!saveTemplateName.trim() || !session) return;
    savingTemplate = true;
    try { await api.templates.saveFromSession(session.id, saveTemplateName.trim()); } catch {}
    savingTemplate = false;
    showSaveTemplateModal = false;
  }

  // ── Exercise search modal ──────────────────────────────────────────────────
  async function openExerciseModal() {
    if (!allExercises.length) {
      [allExercises] = await Promise.all([
        api.exercises.list(),
        api.injuries.affectedExercises().then(r => { affectedExercises = r; }).catch(() => {}),
      ]);
    }
    filteredExercises = allExercises;
    exerciseSearch = '';
    exerciseFilter = '';
    showExerciseModal = true;
  }

  function filterExercises() {
    let list = allExercises;
    if (exerciseFilter) {
      list = list.filter(e => e.primary_muscles.includes(exerciseFilter) || e.secondary_muscles.includes(exerciseFilter));
    }
    if (exerciseSearch) {
      const q = exerciseSearch.toLowerCase();
      list = list.filter(e => e.name.toLowerCase().includes(q) || e.aliases.some(a => a.toLowerCase().includes(q)));
    }
    filteredExercises = list;
  }

  $: { exerciseSearch; exerciseFilter; filterExercises(); }

  async function addExerciseToSession(ex) {
    if (!session) return;
    showExerciseModal = false;
    if (exercises.find(e => e.exercise_id === ex.id)) return;
    await api.sessions.addSet(session.id, { exercise_id: ex.id, set_number: 1, reps: 0, set_type: 'straight' });
    await loadSession();
  }

  // ── Set management ─────────────────────────────────────────────────────────
  async function addSet(exerciseId, exerciseName) {
    if (!session) return;
    const group = exercises.find(e => e.exercise_id === exerciseId);
    const lastSet = group?.sets?.[group.sets.length - 1];
    const nextNum = (lastSet?.set_number ?? 0) + 1;
    await api.sessions.addSet(session.id, {
      exercise_id: exerciseId,
      set_number: nextNum,
      weight: lastSet?.weight ?? null,
      reps: lastSet?.reps ?? 0,
      rir: lastSet?.rir ?? null,
      set_type: 'straight',
    });
    await loadSession();
    startRestTimer(exerciseName);
  }

  async function deleteSet(setId) {
    if (!session) return;
    doneIds.delete(setId);
    doneIds = new Set(doneIds);
    if (rpeSetId === setId) rpeSetId = null;
    await api.sessions.deleteSet(session.id, setId);
    await loadSession();
  }

  async function updateSetField(setId, field, value) {
    if (!session) return;
    const parsed = field === 'reps' || field === 'rir' || field === 'set_number'
      ? (value === '' ? null : parseInt(value))
      : (value === '' ? null : parseFloat(value));
    await api.sessions.updateSet(session.id, setId, { [field]: parsed });
    for (const group of exercises) {
      const s = group.sets.find(s => s.id === setId);
      if (s) { s[field] = parsed; break; }
    }
    exercises = [...exercises];
  }

  async function toggleWarmup(setId, currentType) {
    if (!session) return;
    const newType = currentType === 'warmup' ? 'straight' : 'warmup';
    await api.sessions.updateSet(session.id, setId, { set_type: newType });
    for (const group of exercises) {
      const s = group.sets.find(s => s.id === setId);
      if (s) { s.set_type = newType; break; }
    }
    exercises = [...exercises];
  }

  // RPE per-set (maps 6-10 to RIR 4-0)
  async function setRowRpe(setId, rpe) {
    const rir = 10 - rpe;
    await updateSetField(setId, 'rir', rir);
    rpeSetId = null;
  }

  function rpeColor(n) {
    if (n <= 6) return 'var(--success)';
    if (n <= 7) return '#8bc34a';
    if (n <= 8) return 'var(--warn)';
    if (n <= 9) return '#e06830';
    return 'var(--danger)';
  }

  async function togglePrev(exerciseId) {
    showPrev[exerciseId] = !showPrev[exerciseId];
    if (showPrev[exerciseId] && !prevSessions[exerciseId]) {
      prevSessions[exerciseId] = await api.history.lastSession(exerciseId);
    }
    prevSessions = { ...prevSessions };
    showPrev = { ...showPrev };
  }

  const MUSCLES = ['chest','back','shoulders','biceps','triceps','quads','hamstrings','glutes','calves','abs'];

  // ── Exercise swap ──────────────────────────────────────────────────────────
  let showSwapModal = false;
  let swapGroup = null;
  let swapMuscle = '';
  let swapSearch = '';
  let swapExercises = [];
  let swapping = false;

  async function openSwapModal(group) {
    swapGroup = group;
    if (!allExercises.length) allExercises = await api.exercises.list();
    const ex = allExercises.find(e => e.id === group.exercise_id);
    swapMuscle = ex?.primary_muscles?.[0] ?? '';
    swapSearch = '';
    filterSwap();
    showSwapModal = true;
  }

  function filterSwap() {
    let list = allExercises.filter(e => e.id !== swapGroup?.exercise_id);
    if (swapMuscle) list = list.filter(e => e.primary_muscles.includes(swapMuscle) || e.secondary_muscles.includes(swapMuscle));
    if (swapSearch) {
      const q = swapSearch.toLowerCase();
      list = list.filter(e => e.name.toLowerCase().includes(q) || e.aliases.some(a => a.toLowerCase().includes(q)));
    }
    swapExercises = list;
  }

  $: { swapSearch; swapMuscle; if (showSwapModal) filterSwap(); }

  async function confirmSwap(newEx) {
    if (!session || !swapGroup || swapping) return;
    swapping = true;
    try {
      await api.sessions.swapExercise(session.id, swapGroup.exercise_id, newEx.id);
      showSwapModal = false;
      await loadSession();
    } catch {}
    swapping = false;
  }

  // Superset pairing
  let pairTarget = null; // exercise group currently selected for pairing

  async function startPairing(group) {
    if (pairTarget && pairTarget.exercise_id === group.exercise_id) {
      pairTarget = null;
      return;
    }
    if (pairTarget) {
      // Second click — create the pair
      try {
        await api.sessions.pairExercises(session.id, [pairTarget.exercise_id, group.exercise_id]);
        pairTarget = null;
        await loadSession();
      } catch {}
    } else {
      pairTarget = group;
    }
  }

  async function unpairGroup(group) {
    try {
      await api.sessions.unpairExercises(session.id, group);
      await loadSession();
    } catch {}
  }

  // Build display groups: solo exercises and superset pairs
  $: displayGroups = (() => {
    const groups = [];
    const seenSS = new Set();
    for (const ex of exercises) {
      if (!ex.superset_group) {
        groups.push({ type: 'solo', exercise: ex });
      } else if (!seenSS.has(ex.superset_group)) {
        seenSS.add(ex.superset_group);
        const partners = exercises.filter(e => e.superset_group === ex.superset_group);
        groups.push({ type: 'superset', group: ex.superset_group, exercises: partners });
      }
    }
    return groups;
  })();

  // Plate calculator
  let plateCalcSetId = null;
  let plateCalcWeight = '';
  let plateCalcBar = 45;
  const PLATES_LBS = [45, 35, 25, 10, 5, 2.5, 1.25];
  const PLATE_COLORS = {45:'#c0392b',35:'#f39c12',25:'#27ae60',10:'#dddddd',5:'#2980b9',2.5:'#333333',1.25:'#999999'};

  function openPlateCalc(setId, w) { plateCalcSetId = setId; plateCalcWeight = w || ''; }
  function closePlateCalc() { plateCalcSetId = null; }

  function calcPlateResult(target, bar) {
    if (!target || target <= bar) return null;
    let rem = (target - bar) / 2;
    const used = [];
    for (const p of PLATES_LBS) {
      while (rem >= p - 0.001) { used.push(p); rem -= p; rem = Math.round(rem * 1000) / 1000; }
    }
    return { used, remainder: rem };
  }

  $: plateResult = plateCalcSetId ? calcPlateResult(parseFloat(plateCalcWeight), plateCalcBar) : null;

  // Today's Plan panel
  let planOpen = true;

  function quickFocusExercise(name) {
    if (!allExercises.length) api.exercises.list().then(list => { allExercises = list; });
    exerciseSearch = name;
    exerciseFilter = '';
    showExerciseModal = true;
  }

  // Progress bar
  $: totalDone = doneIds.size;
  $: totalSets = exercises.reduce((a, g) => a + g.sets.length, 0);
  $: progressPct = totalSets ? (totalDone / totalSets * 100) : 0;
</script>

<svelte:head><title>Log — LiftForge</title></svelte:head>

{#if loading}
  <div class="loading"><div class="spinner"></div></div>

{:else if !session}
  <div class="no-session">
    <div class="no-session-icon">✦</div>
    <div class="no-session-title">No Active Session</div>
    <div class="no-session-sub">Start a workout to begin logging sets</div>
    <button class="begin-btn" on:click={requestStartSession} disabled={pendingSessionCreate}>
      {pendingSessionCreate ? 'Starting…' : 'Begin Session'}
    </button>
  </div>

{:else}
  <!-- Sticky header -->
  <div class="log-header">
    <div class="log-hdr-top">
      <div class="log-hdr-left">
        <div class="log-context-label">Active Session</div>
        {#if editingName}
          <input class="name-input" bind:value={sessionName}
            on:keydown={e => e.key === 'Enter' && saveName()}
            on:blur={saveName} autofocus />
        {:else}
          <button class="session-name-btn" on:click={() => editingName = true}>
            {session.name || 'Unnamed Session'}
          </button>
        {/if}
      </div>
      <div class="log-hdr-right">
        <div class="elapsed">{elapsed}</div>
        <div class="progress-meta">{totalDone}/{totalSets} sets</div>
      </div>
    </div>
    <div class="progress-bar-track">
      <div class="progress-bar-fill" style="width:{progressPct}%"></div>
    </div>
  </div>

  <!-- Scrollable content -->
  <div class="log-body">
    <!-- Rest timer inline card -->
    {#if restRunning}
      <div class="rest-card">
        <svg width="62" height="62" class="rest-ring" style="flex-shrink:0">
          <circle cx="31" cy="31" r="24" fill="none" stroke="var(--faint)" stroke-width="3"/>
          <circle cx="31" cy="31" r="24" fill="none"
            stroke={restColor} stroke-width="3"
            stroke-dasharray={restCirc}
            stroke-dashoffset={restCirc - restOffset}
            stroke-linecap="round"
            style="transform-origin:31px 31px;transform:rotate(-90deg);transition:stroke-dashoffset 1s linear,stroke 0.3s"/>
          <text x="31" y="36" text-anchor="middle" fill="var(--text)"
            font-size="13" font-family="var(--sans)" font-weight="600">{restRemaining}s</text>
        </svg>
        <div class="rest-info">
          <div class="rest-title">Rest Timer</div>
          <div class="rest-sub">{restRemaining > 0 ? 'Take a breath…' : 'Ready to go!'}</div>
          {#if restExerciseName}<div class="rest-label">{restExerciseName}</div>{/if}
          <div class="rest-btns">
            <button class="rest-adj" on:click={() => addRestTime(30)}>+30s</button>
            <button class="rest-adj" on:click={() => addRestTime(60)}>+60s</button>
            <button class="rest-skip" on:click={dismissRestTimer}>Skip rest</button>
          </div>
        </div>
      </div>
    {/if}

    <!-- Today's Plan panel (generated sessions) -->
    {#if $sessionPlan?.exercises?.length}
      <div class="plan-card">
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div class="plan-hdr" on:click={() => planOpen = !planOpen}>
          <div>
            <div class="plan-title">Today's Plan</div>
            <div class="plan-sub">{$sessionPlan.session_name} · {$sessionPlan.rest_seconds}s rest</div>
          </div>
          <span class="plan-toggle">{planOpen ? '▲' : '▼'}</span>
        </div>
        {#if planOpen}
          <div class="plan-exercises">
            {#each $sessionPlan.exercises as pe}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <div class="plan-ex" on:click={() => quickFocusExercise(pe.name)}>
                <span class="plan-ex-name">{pe.name}</span>
                <div style="display:flex; align-items:center; gap:6px;">
                  <span class="plan-ex-target">{pe.sets}×{pe.reps_min}–{pe.reps_max}</span>
                  {#if pe.set_technique && pe.set_technique !== 'straight'}
                    <span style="font-size:9px; font-weight:700; padding:1px 5px; border-radius:8px; background:rgba(124,140,248,0.15); color:#7c8cf8; border:1px solid rgba(124,140,248,0.3); text-transform:capitalize;">{pe.set_technique.replace('_', '-')}</span>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
          <button class="plan-dismiss" on:click={() => sessionPlan.set(null)}>Dismiss plan</button>
        {/if}
      </div>
    {/if}

    <!-- Pairing banner -->
    {#if pairTarget}
      <div class="pair-banner">
        <span>Tap "SS" on another exercise to pair with <strong>{pairTarget.exercise_name}</strong></span>
        <button class="pair-cancel-btn" on:click={() => pairTarget = null}>Cancel</button>
      </div>
    {/if}

    <!-- Exercise blocks -->
    {#each displayGroups as item (item.type === 'solo' ? 'solo-' + item.exercise.exercise_id : 'ss-' + item.group)}
      {#if item.type === 'superset'}
        <!-- Superset card -->
        <div class="superset-block">
          <div class="ss-header">
            <span class="ss-badge">SS</span>
            <span class="ss-names">{item.exercises.map(e => e.exercise_name).join(' + ')}</span>
            <button class="ss-unpair-btn" on:click={() => unpairGroup(item.group)}>Ungroup</button>
          </div>
          {#each item.exercises as group (group.exercise_id)}
            {@const ssLabel = item.exercises.map(e => e.exercise_name).join(' + ')}
            <div class="ex-block ss-ex-block">
              <div class="ex-hdr">
                <div class="ex-hdr-left">
                  <div class="ex-name">{group.exercise_name}</div>
                  {#if overloadSuggestions[group.exercise_id]}
                    <div class="overload-hint">{overloadSuggestions[group.exercise_id]}</div>
                  {/if}
                </div>
                <div class="ex-actions">
                  <button class="ex-action-btn" on:click={() => openSwapModal(group)}>⇄</button>
                  <button class="ex-action-btn" on:click={() => togglePrev(group.exercise_id)}>
                    {showPrev[group.exercise_id] ? '▲' : '▼'}
                  </button>
                </div>
              </div>
              {#if showPrev[group.exercise_id]}
                <div class="prev-ref">
                  {#if prevSessions[group.exercise_id]}
                    <div class="prev-date">Last: {formatDate(prevSessions[group.exercise_id].date)}</div>
                    <div class="prev-sets">
                      {#each prevSessions[group.exercise_id].sets as ps}
                        <span class="prev-set-chip">{ps.weight ?? 'BW'}×{ps.reps}{ps.rir != null ? ' R' + ps.rir : ''}</span>
                      {/each}
                    </div>
                  {:else}
                    <span class="prev-empty">No previous data</span>
                  {/if}
                </div>
              {/if}
              <div class="sets-block">
                <div class="sets-cols-hdr">
                  <span>#</span>
                  <span style="flex:1">Weight × Reps</span>
                  <span style="width:44px;text-align:center">RPE</span>
                  <span style="width:28px"></span>
                </div>
                {#each group.sets as s (s.id)}
                  {@const isDone = doneIds.has(s.id)}
                  <div class="set-row" class:done={isDone} class:warmup={s.set_type === 'warmup'}>
                    <div class="set-num">
                      <button class="warmup-btn" class:is-warmup={s.set_type === 'warmup'}
                        title={s.set_type === 'warmup' ? 'Working set' : 'Warm-up'}
                        on:click={() => toggleWarmup(s.id, s.set_type)}>W</button>
                    </div>
                    <div class="set-inputs">
                      <input type="number" min="0" step="2.5" value={s.weight ?? ''} placeholder="BW"
                        class="set-input weight-input"
                        on:change={e => updateSetField(s.id, 'weight', e.target.value)} />
                      <span class="set-times">×</span>
                      <input type="number" min="1" step="1" value={s.reps}
                        class="set-input reps-input"
                        on:change={e => updateSetField(s.id, 'reps', e.target.value)} />
                    </div>
                    <div class="set-rpe-cell">
                      {#if isDone}
                        <button class="rpe-val-btn" class:has-rpe={s.rir != null}
                          on:click|stopPropagation={() => rpeSetId = rpeSetId === s.id ? null : s.id}>
                          {s.rir != null ? 10 - s.rir : '—'}
                        </button>
                      {:else}
                        <span class="rpe-empty">—</span>
                      {/if}
                    </div>
                    <div class="set-check-cell">
                      <!-- svelte-ignore a11y-click-events-have-key-events -->
                      <!-- svelte-ignore a11y-no-static-element-interactions -->
                      <div class="set-check" class:checked={isDone}
                        on:click={() => toggleDone(s.id, ssLabel, s.weight, s.reps)}>
                        {#if isDone}<span class="check-mark">✓</span>{/if}
                      </div>
                      <button class="del-btn" on:click={() => deleteSet(s.id)}>✕</button>
                    </div>
                  </div>
                  {#if rpeSetId === s.id}
                    <div class="rpe-picker">
                      <div class="rpe-picker-label">Rate of perceived exertion:</div>
                      <div class="rpe-picker-btns">
                        {#each [6,7,8,9,10] as n}
                          <button class="rpe-btn" style="border-color:{rpeColor(n)};color:{rpeColor(n)};background:{rpeColor(n)}22"
                            on:click={() => setRowRpe(s.id, n)}>{n}</button>
                        {/each}
                      </div>
                    </div>
                  {/if}
                {/each}
                <button class="add-set-btn" on:click={() => addSet(group.exercise_id, group.exercise_name)}>+ Add Set</button>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        {@const group = item.exercise}
        <div class="ex-block">
          <!-- Exercise header -->
          <div class="ex-hdr">
            <div class="ex-hdr-left">
              <div class="ex-name">{group.exercise_name}</div>
              {#if overloadSuggestions[group.exercise_id]}
                <div class="overload-hint">{overloadSuggestions[group.exercise_id]}</div>
              {/if}
            </div>
            <div class="ex-actions">
              <button class="ex-action-btn ss-pair-btn"
                class:ss-pair-active={pairTarget?.exercise_id === group.exercise_id}
                title="Pair as superset"
                on:click={() => startPairing(group)}>SS</button>
              <button class="ex-action-btn" on:click={() => openSwapModal(group)}>⇄</button>
              <button class="ex-action-btn" on:click={() => togglePrev(group.exercise_id)}>
                {showPrev[group.exercise_id] ? '▲' : '▼'}
              </button>
            </div>
          </div>

          <!-- Previous session reference -->
          {#if showPrev[group.exercise_id]}
            <div class="prev-ref">
              {#if prevSessions[group.exercise_id]}
                <div class="prev-date">Last: {formatDate(prevSessions[group.exercise_id].date)}</div>
                <div class="prev-sets">
                  {#each prevSessions[group.exercise_id].sets as ps}
                    <span class="prev-set-chip">{ps.weight ?? 'BW'}×{ps.reps}{ps.rir != null ? ' R' + ps.rir : ''}</span>
                  {/each}
                </div>
              {:else}
                <span class="prev-empty">No previous data</span>
              {/if}
            </div>
          {/if}

          <!-- Set rows -->
          <div class="sets-block">
            <div class="sets-cols-hdr">
              <span>#</span>
              <span style="flex:1">Weight × Reps</span>
              <span style="width:44px;text-align:center">RPE</span>
              <span style="width:28px"></span>
            </div>

            {#each group.sets as s (s.id)}
              {@const isDone = doneIds.has(s.id)}
              <div class="set-row" class:done={isDone} class:warmup={s.set_type === 'warmup'}>
                <div class="set-num">
                  <button class="warmup-btn" class:is-warmup={s.set_type === 'warmup'}
                    title={s.set_type === 'warmup' ? 'Working set' : 'Warm-up'}
                    on:click={() => toggleWarmup(s.id, s.set_type)}>W</button>
                </div>
                <div class="set-inputs">
                  <input type="number" min="0" step="2.5"
                    value={s.weight ?? ''}
                    placeholder="BW"
                    class="set-input weight-input"
                    on:change={e => updateSetField(s.id, 'weight', e.target.value)}
                  />
                  <span class="set-times">×</span>
                  <input type="number" min="1" step="1"
                    value={s.reps}
                    class="set-input reps-input"
                    on:change={e => updateSetField(s.id, 'reps', e.target.value)}
                  />
                </div>
                <div class="set-rpe-cell">
                  {#if isDone}
                    <button class="rpe-val-btn" class:has-rpe={s.rir != null}
                      on:click|stopPropagation={() => rpeSetId = rpeSetId === s.id ? null : s.id}>
                      {s.rir != null ? 10 - s.rir : '—'}
                    </button>
                  {:else}
                    <span class="rpe-empty">—</span>
                  {/if}
                </div>
                <div class="set-check-cell">
                  <!-- svelte-ignore a11y-click-events-have-key-events -->
                  <!-- svelte-ignore a11y-no-static-element-interactions -->
                  <div class="set-check" class:checked={isDone}
                    on:click={() => toggleDone(s.id, group.exercise_name, s.weight, s.reps)}>
                    {#if isDone}<span class="check-mark">✓</span>{/if}
                  </div>
                  <button class="del-btn" on:click={() => deleteSet(s.id)}>✕</button>
                </div>
              </div>

              <!-- Inline RPE picker -->
              {#if rpeSetId === s.id}
                <div class="rpe-picker">
                  <div class="rpe-picker-label">Rate of perceived exertion:</div>
                  <div class="rpe-picker-btns">
                    {#each [6,7,8,9,10] as n}
                      <button class="rpe-btn" style="border-color:{rpeColor(n)};color:{rpeColor(n)};background:{rpeColor(n)}22"
                        on:click={() => setRowRpe(s.id, n)}>{n}</button>
                    {/each}
                  </div>
                </div>
              {/if}
            {/each}

            <button class="add-set-btn" on:click={() => addSet(group.exercise_id, group.exercise_name)}>+ Add Set</button>
          </div>
        </div>
      {/if}
    {/each}

    <!-- Empty exercises state -->
    {#if exercises.length === 0}
      <div class="no-exercises">
        <div class="no-ex-icon">⊞</div>
        <div class="no-ex-text">No exercises yet</div>
      </div>
    {/if}

    <!-- Add exercise dashed button -->
    <button class="add-ex-btn" on:click={openExerciseModal}>+ Add Exercise</button>

    <!-- Session note collapsible -->
    <div class="note-block">
      <button class="note-toggle" on:click={() => showNote = !showNote}>
        <span class="serif-15">Session Note</span>
        <span class="note-toggle-arrow">{showNote ? '▲' : '▼'}</span>
      </button>
      {#if showNote}
        <textarea class="note-area" bind:value={sessionNote}
          placeholder="How did this session feel? Any PRs, pain, or notes…"></textarea>
      {/if}
    </div>

    <!-- Action buttons row -->
    <div class="action-row">
      <button class="action-sec-btn" on:click={openSaveTemplate}>◫ Template</button>
    </div>
  </div>

  <!-- Fixed footer: Complete Session -->
  <div class="log-footer">
    <button class="complete-btn" on:click={finishSession} disabled={finishing}>
      {finishing ? 'Finishing…' : 'Complete Session'}
    </button>
  </div>
{/if}

<!-- ── Readiness Modal ──────────────────────────────────────────────────────── -->
{#if showReadinessModal}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="modal-overlay" on:click|self={() => showReadinessModal = false}>
    <div class="modal" style="max-width:380px;">
      <div class="modal-header"><h3>How are you feeling today?</h3></div>
      <div class="modal-body">
        <div class="readiness-grid">
          {#each [{val:1,label:'Terrible'},{val:2,label:'Poor'},{val:3,label:'Ok'},{val:4,label:'Good'},{val:5,label:'Great'}] as opt}
            <button class="readiness-btn" class:selected={readinessRating === opt.val}
              on:click={() => readinessRating = opt.val}>
              <div class="readiness-val">{opt.val}</div>
              <div class="readiness-lbl">{opt.label}</div>
            </button>
          {/each}
        </div>
        <div class="flex gap-2" style="justify-content:flex-end;margin-top:16px;">
          <button class="btn-ghost" on:click={() => { readinessRating = null; confirmStartSession(); }}>Skip</button>
          <button class="btn-primary" on:click={confirmStartSession} disabled={!readinessRating}>Start Workout</button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- ── Post-session RPE Modal ─────────────────────────────────────────────── -->
{#if showRpeModal}
  <div class="modal-overlay">
    <div class="modal" style="max-width:420px;">
      <div class="modal-header"><h3>How hard was that session?</h3></div>
      <div class="modal-body">
        <p class="rpe-modal-sub">Rate overall effort — 1 is a warm walk, 10 is absolute max.</p>
        <div class="rpe-modal-grid">
          {#each [1,2,3,4,5] as n}
            <button class="rpe-modal-btn" class:selected={sessionRpe === n}
              style="--rc:{rpeColor(n)}" on:click={() => sessionRpe = n}>{n}</button>
          {/each}
        </div>
        <div class="rpe-modal-grid">
          {#each [6,7,8,9,10] as n}
            <button class="rpe-modal-btn" class:selected={sessionRpe === n}
              style="--rc:{rpeColor(n)}" on:click={() => sessionRpe = n}>{n}</button>
          {/each}
        </div>
        <div class="flex gap-2" style="justify-content:flex-end;margin-top:16px;">
          <button class="btn-ghost" on:click={submitRpe} disabled={submittingRpe}>Skip</button>
          <button class="btn-primary" on:click={submitRpe} disabled={!sessionRpe || submittingRpe}>
            {submittingRpe ? 'Saving…' : 'Save & Done'}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- ── Save Template Modal ─────────────────────────────────────────────────── -->
{#if showSaveTemplateModal}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="modal-overlay" on:click|self={() => showSaveTemplateModal = false}>
    <div class="modal" style="max-width:380px;">
      <div class="modal-header">
        <h3>Save as Template</h3>
        <button class="btn-ghost btn-sm" on:click={() => showSaveTemplateModal = false}>✕</button>
      </div>
      <div class="modal-body">
        <label for="tplName">Template Name</label>
        <input id="tplName" bind:value={saveTemplateName} placeholder="e.g. Chest Day" autofocus
          on:keydown={e => e.key === 'Enter' && confirmSaveTemplate()} />
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" on:click={() => showSaveTemplateModal = false}>Cancel</button>
        <button class="btn-primary" on:click={confirmSaveTemplate}
          disabled={savingTemplate || !saveTemplateName.trim()}>
          {savingTemplate ? 'Saving…' : 'Save Template'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ── Exercise Search Modal ───────────────────────────────────────────────── -->
{#if showExerciseModal}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="modal-overlay" on:click|self={() => showExerciseModal = false}>
    <div class="modal" style="max-height:75vh;">
      <div class="modal-header">
        <h3>Add Exercise</h3>
        <button class="btn-ghost btn-sm" on:click={() => showExerciseModal = false}>✕</button>
      </div>
      <div class="modal-body" style="display:flex;flex-direction:column;gap:12px;overflow:hidden;">
        <div class="search-wrap">
          <span class="search-icon">⊞</span>
          <input bind:value={exerciseSearch} placeholder="Search exercises…" autofocus />
        </div>
        <div class="filter-chips">
          <button class="chip" class:active={exerciseFilter === ''} on:click={() => exerciseFilter = ''}>All</button>
          {#each MUSCLES as m}
            <button class="chip" class:active={exerciseFilter === m} on:click={() => exerciseFilter = m}>{m}</button>
          {/each}
        </div>
        <div style="overflow-y:auto;flex:1;">
          {#if filteredExercises.length === 0}
            <div class="empty-state" style="padding:24px;">No exercises found</div>
          {:else}
            {#each filteredExercises as ex}
              <button class="ex-list-item" on:click={() => addExerciseToSession(ex)}>
                <div style="flex:1;">
                  <div class="ex-list-name">{ex.name}</div>
                  <div class="ex-list-meta">{ex.primary_muscles.join(', ')} · {ex.movement_pattern}</div>
                </div>
                {#if affectedExercises[ex.id]}
                  <span title="Affected: {affectedExercises[ex.id].join(', ')}" style="font-size:14px; flex-shrink:0; margin-left:6px;">⚠</span>
                {/if}
              </button>
            {/each}
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- ── Swap Exercise Modal ────────────────────────────────────────────────── -->
{#if showSwapModal}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="modal-overlay" on:click|self={() => showSwapModal = false}>
    <div class="modal" style="max-height:75vh;">
      <div class="modal-header">
        <div>
          <h3>Swap Exercise</h3>
          <div style="font-size:12px;color:var(--muted);margin-top:2px;">Replacing: {swapGroup?.exercise_name}</div>
        </div>
        <button class="btn-ghost btn-sm" on:click={() => showSwapModal = false}>✕</button>
      </div>
      <div class="modal-body" style="display:flex;flex-direction:column;gap:12px;overflow:hidden;">
        <div class="search-wrap">
          <span class="search-icon">⊞</span>
          <input bind:value={swapSearch} placeholder="Search exercises…" autofocus />
        </div>
        <div class="filter-chips">
          <button class="chip" class:active={swapMuscle === ''} on:click={() => swapMuscle = ''}>All</button>
          {#each MUSCLES as m}
            <button class="chip" class:active={swapMuscle === m} on:click={() => swapMuscle = m}>{m}</button>
          {/each}
        </div>
        <div style="overflow-y:auto;flex:1;">
          {#each swapExercises as ex}
            <button class="ex-list-item" on:click={() => confirmSwap(ex)} disabled={swapping}>
              <div class="ex-list-name">{ex.name}</div>
              <div class="ex-list-meta">{ex.primary_muscles.join(', ')} · {ex.movement_pattern}</div>
            </button>
          {/each}
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- ── Plate Calculator Modal ─────────────────────────────────────────────── -->
{#if plateCalcSetId !== null}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="modal-overlay" on:click|self={closePlateCalc}>
    <div class="modal" style="max-width:380px;">
      <div class="modal-header">
        <h3>Plate Calculator</h3>
        <button class="btn-ghost btn-sm" on:click={closePlateCalc}>✕</button>
      </div>
      <div class="modal-body" style="display:flex;flex-direction:column;gap:12px;">
        <div class="flex gap-3">
          <div style="flex:1">
            <label for="pcW">Target Weight</label>
            <input id="pcW" type="number" min="0" step="2.5" bind:value={plateCalcWeight} placeholder="e.g. 185" autofocus />
          </div>
          <div style="flex:1">
            <label for="pcBar">Bar</label>
            <select id="pcBar" bind:value={plateCalcBar}>
              {#each [45,35,25,15] as b}<option value={b}>{b} lbs</option>{/each}
            </select>
          </div>
        </div>
        {#if plateResult}
          {#if plateResult.remainder < 0.001}
            <div style="background:var(--surf-2);border-radius:var(--radius);padding:12px;">
              <div style="font-size:12px;color:var(--muted);margin-bottom:6px;">{(parseFloat(plateCalcWeight)-plateCalcBar)/2} lbs per side</div>
              <div style="display:flex;flex-wrap:wrap;gap:4px;">
                {#each plateResult.used as p}
                  <div style="width:36px;height:36px;border-radius:50%;background:{PLATE_COLORS[p]||'#555'};color:{p===10?'#333':'#fff'};font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center;border:2px solid rgba(255,255,255,0.1)">{p}</div>
                {/each}
              </div>
            </div>
          {:else}
            <div style="color:var(--muted);font-size:13px;">Can't hit this weight exactly — adjust target or bar.</div>
          {/if}
        {/if}
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" on:click={closePlateCalc}>Cancel</button>
        <button class="btn-primary" on:click={() => { updateSetField(plateCalcSetId,'weight',plateCalcWeight); closePlateCalc(); }}
          disabled={!plateCalcWeight}>Use {plateCalcWeight||'?'} lbs</button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Loading / no session */
  .loading { display:flex; justify-content:center; padding:48px 0; }
  .no-session {
    display:flex; flex-direction:column; align-items:center;
    padding:60px 20px; text-align:center; gap:12px;
  }
  .no-session-icon { font-size:40px; opacity:0.3; }
  .no-session-title { font-family:var(--serif); font-size:22px; }
  .no-session-sub { font-size:13px; color:var(--muted); }
  .begin-btn {
    background:var(--accent); color:#fff; border:none;
    border-radius:var(--radius-lg); padding:16px 40px;
    font-family:var(--serif); font-size:20px; cursor:pointer;
    margin-top:8px; transition:background 0.15s;
  }
  .begin-btn:hover { background:#f05070; }
  .begin-btn:disabled { opacity:0.6; cursor:not-allowed; }

  /* Log header */
  .log-header {
    position:sticky; top:0; z-index:10;
    background:var(--surf);
    border-bottom:1px solid var(--bdr);
    padding:14px 0 0;
    margin:-20px -20px 16px;
    padding-left:20px; padding-right:20px;
  }
  .log-hdr-top { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; }
  .log-context-label { font-size:9px; color:var(--accent); text-transform:uppercase; letter-spacing:0.15em; font-weight:600; margin-bottom:3px; }
  .log-hdr-right { text-align:right; }
  .elapsed { font-family:var(--serif); font-size:26px; color:var(--accent); font-style:italic; line-height:1; }
  .progress-meta { font-size:10px; color:var(--muted); margin-top:2px; }
  .session-name-btn {
    font-family:var(--serif); font-size:22px; color:var(--text);
    background:transparent; border:none; cursor:pointer; padding:0;
    text-align:left; line-height:1.1;
  }
  .name-input {
    font-family:var(--serif); font-size:20px; width:220px;
    background:var(--surf-2); border:1px solid var(--accent);
  }
  .progress-bar-track { height:3px; background:var(--bdr); }
  .progress-bar-fill { height:100%; background:var(--accent); transition:width 0.4s ease; }

  /* Body */
  .log-body { padding-bottom:calc(var(--tab-h) + 64px); }

  /* Today's Plan panel */
  .plan-card {
    background:var(--surf); border:1px solid rgba(232,54,93,0.2);
    border-radius:var(--radius-lg); padding:12px 14px; margin-bottom:10px;
  }
  .plan-hdr { display:flex; justify-content:space-between; align-items:center; cursor:pointer; }
  .plan-title { font-family:var(--serif); font-size:14px; color:var(--text); }
  .plan-sub { font-size:10px; color:var(--muted); margin-top:2px; }
  .plan-toggle { font-size:10px; color:var(--muted); }
  .plan-exercises { margin-top:10px; display:flex; flex-direction:column; gap:6px; }
  .plan-ex {
    display:flex; justify-content:space-between; align-items:center;
    padding:6px 8px; border-radius:var(--radius);
    background:var(--surf-2); cursor:pointer; transition:background 0.15s;
  }
  .plan-ex:hover { background:var(--accent-bg); }
  .plan-ex-name { font-size:12px; color:var(--text); }
  .plan-ex-target { font-size:11px; color:var(--accent); font-weight:600; }
  .plan-dismiss {
    margin-top:8px; background:transparent; border:none;
    font-size:10px; color:var(--muted); cursor:pointer; padding:0; text-decoration:underline;
  }
  .plan-dismiss:hover { color:var(--accent); }

  /* Rest timer card */
  .rest-card {
    background:var(--surf-2); border:1px solid var(--bdr-2);
    border-radius:var(--radius-lg); padding:12px 16px;
    display:flex; align-items:center; gap:14px; margin-bottom:14px;
  }
  .rest-info { flex:1; }
  .rest-title { font-family:var(--serif); font-size:16px; color:var(--text); margin-bottom:2px; }
  .rest-sub { font-size:11px; color:var(--muted); margin-bottom:6px; }
  .rest-btns { display:flex; gap:6px; }
  .rest-adj {
    background:transparent; border:1px solid var(--bdr-2);
    border-radius:var(--radius); padding:3px 10px;
    font-size:11px; color:var(--muted); cursor:pointer;
  }
  .rest-skip { background:transparent; border:none; font-size:11px; color:var(--muted); cursor:pointer; padding:3px 6px; }
  .rest-skip:hover { color:var(--accent); }

  /* Exercise block */
  .ex-block { margin-bottom:16px; }
  .ex-hdr { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px; }
  .ex-name { font-family:var(--serif); font-size:19px; color:var(--text); line-height:1.1; }
  .overload-hint { font-size:11px; color:var(--muted); margin-top:2px; }
  .ex-actions { display:flex; gap:6px; }
  .ex-action-btn {
    background:transparent; border:1px solid var(--bdr-2);
    border-radius:var(--radius); padding:4px 8px;
    font-size:13px; color:var(--muted); cursor:pointer;
    transition:border-color 0.15s, color 0.15s;
  }
  .ex-action-btn:hover { border-color:var(--accent); color:var(--accent); }

  /* Previous session ref */
  .prev-ref {
    background:var(--surf-2); border:1px solid var(--bdr);
    border-radius:var(--radius); padding:10px 12px; margin-bottom:10px;
  }
  .prev-date { font-size:10px; color:var(--faint); margin-bottom:6px; }
  .prev-sets { display:flex; flex-wrap:wrap; gap:4px; }
  .prev-set-chip {
    font-size:10px; padding:2px 8px; border-radius:3px;
    background:var(--surf-3); border:1px solid var(--bdr-2); color:var(--muted);
  }
  .prev-empty { font-size:12px; color:var(--faint); }

  /* Sets block */
  .sets-block {
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); overflow:hidden;
  }
  .sets-cols-hdr {
    display:flex; align-items:center; gap:0;
    padding:6px 14px; background:var(--surf-2);
    border-bottom:1px solid var(--bdr);
    font-size:9px; color:var(--muted);
    text-transform:uppercase; letter-spacing:0.07em;
  }
  .sets-cols-hdr span:first-child { width:28px; }

  /* Set row */
  .set-row {
    display:flex; align-items:center; gap:0;
    padding:8px 14px; border-bottom:1px solid var(--bdr);
    background:transparent; transition:background 0.2s;
  }
  .set-row.done { background:var(--accent-bg); }
  .set-row.warmup { opacity:0.65; }
  .set-num { width:28px; }
  .warmup-btn {
    width:20px; height:20px; border-radius:3px; cursor:pointer;
    font-size:9px; font-weight:700; padding:0; line-height:1;
    border:1px solid var(--bdr-2); background:transparent; color:var(--faint);
    transition:all 0.15s;
  }
  .warmup-btn.is-warmup { background:var(--surf-2); color:var(--muted); border-color:var(--muted); }
  .set-inputs { flex:1; display:flex; align-items:center; gap:4px; }
  .set-input {
    background:transparent; border:1px solid var(--bdr);
    border-radius:var(--radius); color:var(--text);
    font-family:var(--serif); font-size:15px; padding:3px 6px;
    outline:none; width:auto;
  }
  .set-input:focus { border-color:var(--accent); }
  .weight-input { width:62px; }
  .reps-input { width:48px; }
  .set-times { font-size:12px; color:var(--muted); }
  .set-rpe-cell { width:44px; text-align:center; }
  .rpe-val-btn {
    background:transparent; border:1px solid var(--bdr-2);
    border-radius:4px; padding:2px 6px; font-size:10px;
    color:var(--muted); cursor:pointer;
  }
  .rpe-val-btn.has-rpe { border-color:var(--accent); color:var(--accent); }
  .rpe-empty { font-size:10px; color:var(--faint); }
  .set-check-cell { width:28px; display:flex; justify-content:flex-end; position:relative; }
  .set-check {
    width:20px; height:20px; border-radius:50%;
    border:1.5px solid var(--bdr-2); background:transparent;
    display:flex; align-items:center; justify-content:center;
    cursor:pointer; transition:all 0.25s;
  }
  .set-check.checked { background:var(--accent); border-color:var(--accent); }
  .check-mark { color:#fff; font-size:10px; font-weight:900; }
  .del-btn {
    position:absolute; right:-24px;
    background:transparent; border:none; cursor:pointer;
    font-size:11px; color:var(--faint); padding:0;
    transition:color 0.15s;
  }
  .del-btn:hover { color:var(--danger); }

  /* Inline RPE picker */
  .rpe-picker {
    padding:8px 14px; background:var(--surf-3);
    border-bottom:1px solid var(--bdr);
  }
  .rpe-picker-label { font-size:9px; color:var(--muted); text-transform:uppercase; letter-spacing:0.07em; margin-bottom:6px; }
  .rpe-picker-btns { display:flex; gap:4px; }
  .rpe-btn {
    flex:1; padding:5px 2px; border-radius:4px; border:1px solid;
    cursor:pointer; font-size:11px; font-weight:700; transition:opacity 0.15s;
  }

  /* Add set + add exercise */
  .add-set-btn {
    display:block; width:100%; padding:9px 14px;
    background:transparent; border:none; cursor:pointer;
    color:var(--muted); font-size:11px; text-align:left;
    border-top:1px dashed var(--faint);
    transition:color 0.15s;
  }
  .add-set-btn:hover { color:var(--accent); }
  .no-exercises {
    text-align:center; padding:32px 0;
    color:var(--muted);
  }
  .no-ex-icon { font-size:32px; opacity:0.3; margin-bottom:8px; }
  .no-ex-text { font-size:13px; }
  .add-ex-btn {
    width:100%; padding:13px;
    background:var(--surf); border:1px dashed var(--bdr-2);
    border-radius:var(--radius-lg); color:var(--muted);
    font-size:13px; cursor:pointer; margin-top:4px;
    transition:border-color 0.15s, color 0.15s;
  }
  .add-ex-btn:hover { border-color:var(--accent); color:var(--accent); }

  /* Session note */
  .note-block {
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:12px 16px; margin-top:12px;
  }
  .note-toggle {
    background:none; border:none; cursor:pointer; padding:0;
    display:flex; justify-content:space-between; width:100%; align-items:center;
  }
  .serif-15 { font-family:var(--serif); font-size:15px; color:var(--muted); }
  .note-toggle-arrow { color:var(--muted); font-size:12px; }
  .note-area {
    width:100%; margin-top:10px; resize:none; height:72px;
    background:var(--surf-2); border:1px solid var(--bdr-2);
    border-radius:var(--radius); color:var(--text);
    font-family:var(--sans); font-size:12px; padding:8px; line-height:1.5;
  }

  .action-row { display:flex; gap:8px; justify-content:flex-end; margin-top:12px; }
  .action-sec-btn {
    background:transparent; border:1px solid var(--bdr-2);
    border-radius:var(--radius); padding:6px 14px;
    font-size:12px; color:var(--muted); cursor:pointer;
  }
  .action-sec-btn:hover { border-color:var(--accent); color:var(--accent); }

  /* Fixed footer */
  .log-footer {
    position:fixed; bottom:var(--tab-h); left:0; right:0;
    padding:12px 20px; background:var(--surf);
    border-top:1px solid var(--bdr); z-index:10;
  }
  .complete-btn {
    width:100%; background:transparent;
    border:1.5px solid var(--accent); border-radius:var(--radius-lg);
    padding:14px; color:var(--accent);
    font-family:var(--serif); font-size:16px; cursor:pointer;
    transition:background 0.15s;
  }
  .complete-btn:hover { background:var(--accent-bg); }
  .complete-btn:disabled { opacity:0.6; cursor:not-allowed; }

  /* Exercise list items in modals */
  .ex-list-item {
    width:100%; text-align:left; background:transparent; border:none;
    border-bottom:1px solid var(--bdr); padding:10px 4px; cursor:pointer;
    transition:background 0.1s;
  }
  .ex-list-item:hover { background:rgba(255,255,255,0.03); }
  .ex-list-name { font-weight:500; color:var(--text); font-size:14px; }
  .ex-list-meta { color:var(--muted); font-size:12px; margin-top:2px; }

  /* Readiness */
  .readiness-grid { display:flex; gap:8px; flex-wrap:wrap; }
  .readiness-btn {
    flex:1; min-width:54px; padding:10px 6px;
    border-radius:var(--radius); border:2px solid var(--bdr);
    background:var(--surf-2); color:var(--text);
    cursor:pointer; transition:all 0.15s; text-align:center;
  }
  .readiness-btn.selected { border-color:var(--accent); background:var(--accent-bg); color:var(--accent); }
  .readiness-val { font-size:16px; margin-bottom:3px; }
  .readiness-lbl { font-size:11px; }

  /* Post-session RPE modal */
  .rpe-modal-sub { color:var(--muted); font-size:13px; margin-bottom:14px; }
  .rpe-modal-grid { display:flex; gap:6px; margin-bottom:8px; }
  .rpe-modal-btn {
    flex:1; padding:10px 0; border-radius:var(--radius);
    border:2px solid var(--bdr); background:var(--surf-2);
    color:var(--muted); font-size:16px; cursor:pointer; transition:all 0.15s;
  }
  .rpe-modal-btn.selected {
    border-color:var(--rc); background:color-mix(in srgb, var(--rc) 15%, transparent);
    color:var(--rc); font-weight:700;
  }

  /* Superset */
  .superset-block {
    border: 1px solid var(--accent);
    border-radius: var(--radius);
    margin-bottom: 12px;
    overflow: hidden;
  }
  .ss-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: color-mix(in srgb, var(--accent) 10%, transparent);
    border-bottom: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
  }
  .ss-badge {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.08em;
    color: var(--accent);
    background: color-mix(in srgb, var(--accent) 18%, transparent);
    border: 1px solid var(--accent);
    border-radius: 4px;
    padding: 2px 5px;
    flex-shrink: 0;
  }
  .ss-names {
    font-size: 11px;
    color: var(--accent);
    font-weight: 600;
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .ss-unpair-btn {
    font-size: 11px;
    padding: 3px 8px;
    border: 1px solid var(--bdr);
    border-radius: var(--radius);
    background: transparent;
    color: var(--muted);
    cursor: pointer;
    flex-shrink: 0;
  }
  .ss-ex-block {
    border: none;
    border-radius: 0;
    margin: 0;
    border-bottom: 1px solid var(--faint);
  }
  .ss-ex-block:last-child { border-bottom: none; }

  /* Pair button on solo exercises */
  .ss-pair-btn {
    font-size: 10px;
    font-weight: 700;
    color: var(--muted);
    border-color: var(--bdr);
  }
  .ss-pair-btn.ss-pair-active {
    color: var(--accent);
    border-color: var(--accent);
    background: color-mix(in srgb, var(--accent) 12%, transparent);
  }

  /* Pairing banner */
  .pair-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 14px;
    background: color-mix(in srgb, var(--accent) 10%, transparent);
    border: 1px solid var(--accent);
    border-radius: var(--radius);
    margin-bottom: 12px;
    font-size: 13px;
    color: var(--text);
  }
  .pair-cancel-btn {
    font-size: 12px;
    padding: 4px 10px;
    border: 1px solid var(--bdr);
    border-radius: var(--radius);
    background: transparent;
    color: var(--muted);
    cursor: pointer;
    flex-shrink: 0;
  }

  /* Rest label */
  .rest-label {
    font-size: 11px;
    color: var(--muted);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 180px;
  }
</style>
