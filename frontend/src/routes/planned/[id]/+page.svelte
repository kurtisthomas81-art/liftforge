<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let ps = null;
  let loading = true;
  let starting = false;
  let error = null;
  let editMode = false;
  let allExercises = [];
  let showSwapModal = false;
  let swapTargetIdx = null;
  let swapSearch = '';
  let swapFilter = '';
  let filteredSwap = [];

  const MUSCLES = ['chest','back','shoulders','biceps','triceps','quads','hamstrings','glutes','calves','abs'];

  onMount(async () => {
    const id = $page.params.id;
    try {
      ps = await api.programs.getPlannedSession(id);
    } catch (e) {
      error = e.message;
    }
    loading = false;
  });

  async function startWorkout() {
    if (!ps) return;
    starting = true;
    try {
      const result = await api.programs.startPlannedSession(ps.id);
      goto('/log');
    } catch (e) {
      error = e.message;
      starting = false;
    }
  }

  function goalColor(goal) {
    return 'var(--primary)';
  }

  async function openSwap(idx) {
    swapTargetIdx = idx;
    swapSearch = '';
    swapFilter = '';
    if (allExercises.length === 0) {
      allExercises = await api.exercises.list();
    }
    filteredSwap = allExercises;
    showSwapModal = true;
  }

  function filterSwap() {
    let list = allExercises;
    if (swapFilter) {
      list = list.filter(e =>
        e.primary_muscles.includes(swapFilter) ||
        e.secondary_muscles.includes(swapFilter)
      );
    }
    if (swapSearch) {
      const q = swapSearch.toLowerCase();
      list = list.filter(e =>
        e.name.toLowerCase().includes(q) ||
        e.aliases.some(a => a.toLowerCase().includes(q))
      );
    }
    filteredSwap = list;
  }

  $: { swapSearch; swapFilter; filterSwap(); }

  async function confirmSwap(ex) {
    if (swapTargetIdx === null || !ps) return;
    const updated = ps.exercises.map((e, i) => {
      if (i === swapTargetIdx) {
        return { ...e, exercise_id: ex.id, exercise_name: ex.name };
      }
      return e;
    });
    ps = { ...ps, exercises: updated };
    showSwapModal = false;

    // Persist
    await api.programs.updatePlannedExercises(ps.id, updated.map(e => ({
      exercise_id: e.exercise_id,
      order_in_session: e.order_in_session,
      target_sets: e.target_sets,
      target_reps_min: e.target_reps_min,
      target_reps_max: e.target_reps_max,
      target_rir: e.target_rir,
      notes: e.notes || '',
    })));
  }
</script>

<svelte:head>
  <title>{ps ? ps.split_day_name : 'Session'} — LiftForge</title>
</svelte:head>

<div style="max-width:700px;">
  {#if loading}
    <div class="flex items-center gap-3" style="padding:32px 0;">
      <div class="spinner"></div>
    </div>

  {:else if error}
    <div class="card" style="color:var(--danger);">{error}</div>

  {:else if ps}
    <!-- Header -->
    <div class="flex items-center gap-3 mb-4" style="flex-wrap:wrap;">
      <a href="/program/{ps.mesocycle_name ? '' : ''}" class="btn-ghost btn-sm" on:click|preventDefault={() => history.back()}>← Back</a>
      <div style="flex:1;">
        <h2 style="font-size:20px; font-weight:700; display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          {ps.base_session_name ?? ps.split_day_name ?? 'Session'}
          {#if ps.variant}
            <span style="display:inline-block; padding:2px 9px; border-radius:10px; background:rgba(232,160,64,0.18); color:var(--accent); font-size:12px; font-weight:700;">{ps.variant}</span>
          {/if}
        </h2>
        <div style="color:var(--text-muted); font-size:13px; margin-top:2px;">
          {#if ps.mesocycle_name}{ps.mesocycle_name} · {/if}
          Week {ps.week_number}
        </div>
      </div>
    </div>

    <!-- Muscles -->
    {#if ps.muscles && ps.muscles.length > 0}
      <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:16px;">
        {#each ps.muscles as muscle}
          <span style="background:rgba(232,160,64,0.1); border:1px solid rgba(232,160,64,0.25); border-radius:3px; padding:2px 8px; font-size:11px; color:var(--primary); text-transform:capitalize;">
            {muscle}
          </span>
        {/each}
      </div>
    {/if}

    <!-- Start button -->
    {#if !ps.session_id}
      <button class="btn-primary" on:click={startWorkout} disabled={starting}
        style="width:100%; padding:14px; font-size:16px; margin-bottom:20px; border-radius:8px;">
        {starting ? 'Starting...' : 'Start Workout'}
      </button>
    {:else}
      <div style="background:rgba(76,175,106,0.1); border:1px solid rgba(76,175,106,0.3); border-radius:6px; padding:10px 14px; margin-bottom:20px; font-size:13px; color:#4caf6a;">
        Session completed
      </div>
    {/if}

    <!-- Exercise list -->
    <div style="display:flex; flex-direction:column; gap:10px;">
      {#each ps.exercises as ex, i}
        <div class="card">
          <div class="flex items-center justify-between mb-2">
            <div>
              <span style="font-size:11px; color:var(--text-faint); margin-right:8px;">{ex.order_in_session}.</span>
              <span style="font-weight:600; font-size:14px;">{ex.exercise_name}</span>
            </div>
            <button class="btn-ghost btn-sm" style="font-size:11px;" on:click={() => openSwap(i)}>
              Swap
            </button>
          </div>

          <!-- Target -->
          <div style="font-size:13px; color:var(--text-muted); margin-bottom:8px;">
            <strong style="color:var(--primary);">{ex.target_sets} sets</strong>
            × {ex.target_reps_min}–{ex.target_reps_max} reps
            @ RIR {ex.target_rir}
          </div>

          <!-- Last week reference + overload suggestion -->
          {#if ex.last_week}
            <div style="background:var(--surface-2); border-left:2px solid var(--border); padding:6px 10px; border-radius:2px; font-size:12px; color:var(--text-muted);">
              Last week: {ex.last_week.max_weight} lbs × {ex.last_week.reps}
              {#if ex.last_week.rir !== null && ex.last_week.rir !== undefined}
                @ RIR {ex.last_week.rir}
              {/if}
              {#if ex.suggestion}
                <span style="color:var(--primary); margin-left:8px;">→ {ex.suggestion}</span>
              {/if}
            </div>
          {/if}

          {#if ex.notes}
            <div style="font-size:11px; color:var(--text-faint); margin-top:6px;">{ex.notes}</div>
          {/if}
        </div>
      {/each}
    </div>

    {#if ps.exercises.length === 0}
      <div class="card">
        <div class="empty-state">
          <p>No exercises planned for this session.</p>
        </div>
      </div>
    {/if}
  {/if}
</div>

<!-- Swap exercise modal -->
{#if showSwapModal}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="modal-overlay" on:click|self={() => (showSwapModal = false)}>
    <div class="modal" style="max-height:70vh;">
      <div class="modal-header">
        <h3>Swap Exercise</h3>
        <button class="btn-ghost btn-sm" on:click={() => (showSwapModal = false)}>✕</button>
      </div>
      <div class="modal-body" style="display:flex; flex-direction:column; gap:10px; overflow:hidden;">
        <div class="search-wrap">
          <span class="search-icon">⊞</span>
          <input bind:value={swapSearch} placeholder="Search..." />
        </div>
        <div class="filter-chips">
          <button class="chip" class:active={swapFilter === ''} on:click={() => (swapFilter = '')}>All</button>
          {#each MUSCLES as m}
            <button class="chip" class:active={swapFilter === m} on:click={() => (swapFilter = m)}>{m}</button>
          {/each}
        </div>
        <div style="overflow-y:auto; flex:1;">
          {#each filteredSwap as ex}
            <button
              on:click={() => confirmSwap(ex)}
              style="width:100%; text-align:left; background:transparent; border:none; border-bottom:1px solid var(--border); padding:10px 4px; cursor:pointer;"
              on:mouseenter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
              on:mouseleave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style="font-weight:500; color:var(--text); font-size:13px;">{ex.name}</div>
              <div style="color:var(--text-muted); font-size:11px; margin-top:2px;">
                {ex.primary_muscles.join(', ')} · {ex.mechanics}
              </div>
            </button>
          {/each}
        </div>
      </div>
    </div>
  </div>
{/if}
