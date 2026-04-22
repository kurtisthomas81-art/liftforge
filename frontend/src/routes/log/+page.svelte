<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { activeSession, refreshActiveSession, getElapsed } from '$lib/stores.js';
  import { autoSessionName, formatDate } from '$lib/utils.js';

  let session = null;
  let exercises = [];        // grouped: { exercise_id, exercise_name, sets[] }
  let loading = true;
  let elapsed = '0:00';
  let intervalId;
  let editingName = false;
  let sessionName = '';
  let finishing = false;

  // Exercise search modal
  let showExerciseModal = false;
  let exerciseSearch = '';
  let exerciseFilter = '';
  let allExercises = [];
  let filteredExercises = [];
  let searchTimeout;

  // Previous session reference per exercise (lazy-loaded)
  let prevSessions = {}; // exercise_id → data
  let showPrev = {};     // exercise_id → bool

  // Inline editing state
  let editingSet = null; // { sessionId, setId, field }

  onMount(async () => {
    await refreshActiveSession();
    session = $activeSession;

    if (session) {
      await loadSession();
      intervalId = setInterval(() => {
        elapsed = getElapsed(session.started_at);
      }, 1000);
    }

    loading = false;
  });

  onDestroy(() => clearInterval(intervalId));

  async function loadSession() {
    if (!session) return;
    const detail = await api.sessions.get(session.id);
    session = { ...session, ...detail };
    exercises = detail.exercises || [];
    sessionName = session.name || '';
    elapsed = getElapsed(session.started_at);
  }

  async function startSession() {
    const s = await api.sessions.create({ name: autoSessionName() });
    await refreshActiveSession();
    session = $activeSession;
    exercises = [];
    sessionName = session.name || '';
    elapsed = getElapsed(session.started_at);
    intervalId = setInterval(() => {
      elapsed = getElapsed(session.started_at);
    }, 1000);
  }

  async function finishSession() {
    if (!confirm('Finish this session?')) return;
    finishing = true;
    await api.sessions.finish(session.id);
    await refreshActiveSession();
    session = null;
    exercises = [];
    clearInterval(intervalId);
    finishing = false;
    goto('/');
  }

  async function saveName() {
    if (!session) return;
    await api.sessions.update(session.id, { name: sessionName });
    session = { ...session, name: sessionName };
    editingName = false;
  }

  // ── Exercise search modal ──
  async function openExerciseModal() {
    if (allExercises.length === 0) {
      allExercises = await api.exercises.list();
    }
    filteredExercises = allExercises;
    exerciseSearch = '';
    exerciseFilter = '';
    showExerciseModal = true;
  }

  function filterExercises() {
    let list = allExercises;
    if (exerciseFilter) {
      list = list.filter(e =>
        e.primary_muscles.includes(exerciseFilter) ||
        e.secondary_muscles.includes(exerciseFilter)
      );
    }
    if (exerciseSearch) {
      const q = exerciseSearch.toLowerCase();
      list = list.filter(e =>
        e.name.toLowerCase().includes(q) ||
        e.aliases.some(a => a.toLowerCase().includes(q))
      );
    }
    filteredExercises = list;
  }

  $: {
    exerciseSearch; exerciseFilter;
    filterExercises();
  }

  async function addExerciseToSession(ex) {
    if (!session) return;
    showExerciseModal = false;

    // Check if exercise already in session
    const existing = exercises.find(e => e.exercise_id === ex.id);
    if (existing) return; // already added

    // Add first set
    await api.sessions.addSet(session.id, {
      exercise_id: ex.id,
      set_number: 1,
      reps: 0,
    });
    await loadSession();
  }

  // ── Set management ──
  async function addSet(exerciseId) {
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
    });
    await loadSession();
  }

  async function deleteSet(setId) {
    if (!session) return;
    await api.sessions.deleteSet(session.id, setId);
    await loadSession();
  }

  async function updateSetField(setId, field, value) {
    if (!session) return;
    const parsed = field === 'reps' || field === 'rir' || field === 'set_number'
      ? (value === '' ? null : parseInt(value))
      : (value === '' ? null : parseFloat(value));
    await api.sessions.updateSet(session.id, setId, { [field]: parsed });
    // Optimistic update in local state
    for (const group of exercises) {
      const s = group.sets.find(s => s.id === setId);
      if (s) { s[field] = parsed; break; }
    }
    exercises = [...exercises];
  }

  // ── Previous session reference ──
  async function togglePrev(exerciseId) {
    showPrev[exerciseId] = !showPrev[exerciseId];
    if (showPrev[exerciseId] && !prevSessions[exerciseId]) {
      prevSessions[exerciseId] = await api.history.lastSession(exerciseId);
    }
    prevSessions = { ...prevSessions };
    showPrev = { ...showPrev };
  }

  const MUSCLES = ['chest','back','shoulders','biceps','triceps','quads','hamstrings','glutes','calves','abs'];
</script>

<svelte:head><title>Log Workout — LiftForge</title></svelte:head>

{#if loading}
  <div class="flex items-center gap-3" style="padding:48px 0;">
    <div class="spinner"></div>
    <span style="color:var(--text-muted);">Loading...</span>
  </div>

{:else if !session}
  <!-- No active session -->
  <div style="max-width:600px;">
    <h2 style="font-size:20px; font-weight:700; margin-bottom:24px;">Log Workout</h2>
    <div class="card">
      <div class="empty-state">
        <div class="empty-icon">✦</div>
        <p>No active session. Start one to begin logging.</p>
        <button class="btn-primary" on:click={startSession} style="padding:12px 32px; font-size:15px;">
          Start Workout
        </button>
      </div>
    </div>
  </div>

{:else}
  <!-- Active session -->
  <div style="max-width:800px;">
    <!-- Session header -->
    <div class="flex items-center justify-between mb-4" style="flex-wrap:wrap; gap:12px;">
      <div>
        {#if editingName}
          <div class="flex items-center gap-2">
            <input
              bind:value={sessionName}
              style="font-size:16px; font-weight:600; width:260px;"
              on:keydown={e => e.key === 'Enter' && saveName()}
              on:blur={saveName}
              autofocus
            />
          </div>
        {:else}
          <button
            class="btn-ghost"
            on:click={() => { editingName = true; }}
            style="font-size:16px; font-weight:600; padding:4px 8px; border:none; background:transparent; color:var(--text);"
          >
            {session.name || 'Unnamed Session'} ✎
          </button>
        {/if}
        <div style="color:var(--text-muted); font-size:13px; margin-top:2px;">
          {elapsed} elapsed
        </div>
      </div>
      <div class="flex gap-2">
        <button class="btn-secondary" on:click={openExerciseModal}>+ Add Exercise</button>
        <button class="btn-danger" on:click={finishSession} disabled={finishing}
          style="background:transparent; color:var(--danger); border:1px solid var(--danger); padding:7px 14px; border-radius:4px;">
          {finishing ? 'Finishing...' : 'Finish'}
        </button>
      </div>
    </div>

    <!-- Exercise groups -->
    {#if exercises.length === 0}
      <div class="card">
        <div class="empty-state" style="padding:32px;">
          <p style="color:var(--text-muted);">No exercises yet.</p>
          <button class="btn-secondary mt-3" on:click={openExerciseModal}>+ Add Exercise</button>
        </div>
      </div>
    {/if}

    {#each exercises as group (group.exercise_id)}
      <div class="card mb-3">
        <!-- Exercise header -->
        <div class="flex items-center justify-between mb-3">
          <div style="font-weight:600; font-size:15px;">{group.exercise_name}</div>
          <button class="btn-ghost btn-sm" on:click={() => togglePrev(group.exercise_id)}>
            {showPrev[group.exercise_id] ? '▲ Hide ref' : '▼ Previous'}
          </button>
        </div>

        <!-- Previous session reference -->
        {#if showPrev[group.exercise_id]}
          <div style="background:var(--surface-2); border:1px solid var(--border); border-radius:4px; padding:10px 12px; margin-bottom:12px;">
            {#if prevSessions[group.exercise_id]}
              <div style="font-size:11px; color:var(--text-faint); margin-bottom:6px;">
                Last logged: {formatDate(prevSessions[group.exercise_id].date)}
              </div>
              <table style="width:auto;">
                <thead>
                  <tr>
                    <th>Set</th><th>Weight</th><th>Reps</th><th>RIR</th>
                  </tr>
                </thead>
                <tbody>
                  {#each prevSessions[group.exercise_id].sets as ps}
                    <tr>
                      <td style="color:var(--text-muted);">{ps.set_number}</td>
                      <td>{ps.weight ?? 'BW'}</td>
                      <td>{ps.reps}</td>
                      <td>{ps.rir ?? '—'}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {:else}
              <span style="color:var(--text-faint); font-size:12px;">No previous data for this exercise.</span>
            {/if}
          </div>
        {/if}

        <!-- Sets table -->
        <table>
          <thead>
            <tr>
              <th style="width:40px;">Set</th>
              <th>Weight</th>
              <th>Reps</th>
              <th>RIR</th>
              <th style="width:32px;"></th>
            </tr>
          </thead>
          <tbody>
            {#each group.sets as s (s.id)}
              <tr>
                <td style="color:var(--text-muted);">{s.set_number}</td>
                <td>
                  <input
                    type="number"
                    min="0"
                    step="2.5"
                    value={s.weight ?? ''}
                    placeholder="BW"
                    style="width:70px;"
                    on:change={e => updateSetField(s.id, 'weight', e.target.value)}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={s.reps}
                    style="width:55px;"
                    on:change={e => updateSetField(s.id, 'reps', e.target.value)}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min="0"
                    max="4"
                    step="1"
                    value={s.rir ?? ''}
                    placeholder="—"
                    style="width:50px;"
                    on:change={e => updateSetField(s.id, 'rir', e.target.value)}
                  />
                </td>
                <td>
                  <button class="btn-danger btn-sm" on:click={() => deleteSet(s.id)}
                    style="padding:3px 7px; font-size:13px;">✕</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>

        <button class="btn-ghost btn-sm mt-3" on:click={() => addSet(group.exercise_id)}>
          + Add Set
        </button>
      </div>
    {/each}

    {#if exercises.length > 0}
      <div style="text-align:center; margin-top:16px;">
        <button class="btn-secondary" on:click={openExerciseModal}>+ Add Another Exercise</button>
      </div>
    {/if}
  </div>
{/if}

<!-- Exercise search modal -->
{#if showExerciseModal}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="modal-overlay" on:click|self={() => (showExerciseModal = false)}>
    <div class="modal" style="max-height:75vh;">
      <div class="modal-header">
        <h3>Add Exercise</h3>
        <button class="btn-ghost btn-sm" on:click={() => (showExerciseModal = false)}>✕</button>
      </div>
      <div class="modal-body" style="display:flex; flex-direction:column; gap:12px; overflow:hidden;">
        <!-- Search -->
        <div class="search-wrap">
          <span class="search-icon">⊞</span>
          <input
            bind:value={exerciseSearch}
            placeholder="Search exercises..."
            autofocus
          />
        </div>

        <!-- Muscle filter chips -->
        <div class="filter-chips">
          <button class="chip" class:active={exerciseFilter === ''} on:click={() => (exerciseFilter = '')}>All</button>
          {#each MUSCLES as m}
            <button class="chip" class:active={exerciseFilter === m} on:click={() => (exerciseFilter = m)}>
              {m}
            </button>
          {/each}
        </div>

        <!-- Exercise list -->
        <div style="overflow-y:auto; flex:1;">
          {#if filteredExercises.length === 0}
            <div style="text-align:center; padding:32px; color:var(--text-muted);">No exercises found</div>
          {:else}
            {#each filteredExercises as ex}
              <button
                on:click={() => addExerciseToSession(ex)}
                style="width:100%; text-align:left; background:transparent; border:none; border-bottom:1px solid var(--border); padding:10px 4px; cursor:pointer; transition:background 0.1s;"
                on:mouseenter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                on:mouseleave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div style="font-weight:500; color:var(--text); font-size:14px;">{ex.name}</div>
                <div style="color:var(--text-muted); font-size:12px; margin-top:2px;">
                  {ex.primary_muscles.join(', ')} · {ex.movement_pattern}
                </div>
              </button>
            {/each}
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}
