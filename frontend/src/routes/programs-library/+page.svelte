<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let programs = [];
  let loading = true;
  let error = null;

  // Customizer state
  let customizing = null;       // slug of program being customized
  let preview = null;           // preview data from backend
  let previewLoading = false;

  // Editable config
  let cfgWeeks = 4;
  let cfgDeload = 4;
  let cfgDaySlots = [];         // indices 0–6 (Mon=0)
  let cfgSessions = [];         // [{label, exercises:[{exercise_id, exercise_name, sets, reps_min, reps_max, rir, notes}]}]

  // Exercise picker
  let pickerOpen = false;
  let pickerSessionIdx = -1;
  let pickerExIdx = -1;         // -1 = add new
  let allExercises = [];
  let exSearch = '';
  let exLoading = false;

  let installing = false;
  let installError = null;

  const DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
  const DAY_FULL = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  onMount(async () => {
    try { programs = await api.programs.listLibrary(); }
    catch (e) { error = e.message; }
    loading = false;

    // Auto-open customizer if ?open=slug was passed (e.g. from program tab)
    const openSlug = new URLSearchParams(window.location.search).get('open');
    if (openSlug) {
      const prog = programs.find(p => p.slug === openSlug);
      if (prog) openCustomizer(prog);
    }
  });

  async function openCustomizer(prog) {
    customizing = prog.slug;
    preview = null;
    previewLoading = true;
    installError = null;
    try {
      preview = await api.programs.previewLibraryProgram(prog.slug);
      cfgWeeks  = preview.weeks;
      cfgDeload = preview.deload_week;
      cfgDaySlots = [...preview.day_slots];
      cfgSessions = preview.session_types.map(s => ({
        label: s.label,
        exercises: s.exercises.map(e => ({ ...e })),
      }));
    } catch (e) {
      installError = e.message;
    }
    previewLoading = false;
  }

  function closeCustomizer() {
    customizing = null;
    preview = null;
    pickerOpen = false;
  }

  function toggleDay(idx) {
    if (cfgDaySlots.includes(idx)) {
      if (cfgDaySlots.length > 1) cfgDaySlots = cfgDaySlots.filter(d => d !== idx);
    } else {
      cfgDaySlots = [...cfgDaySlots, idx].sort((a, b) => a - b);
    }
  }

  function updateExField(si, ei, field, val) {
    cfgSessions = cfgSessions.map((s, i) =>
      i !== si ? s : {
        ...s,
        exercises: s.exercises.map((e, j) =>
          j !== ei ? e : { ...e, [field]: field === 'notes' ? val : Number(val) }
        ),
      }
    );
  }

  function removeEx(si, ei) {
    cfgSessions = cfgSessions.map((s, i) =>
      i !== si ? s : { ...s, exercises: s.exercises.filter((_, j) => j !== ei) }
    );
  }

  async function openPicker(si, ei) {
    pickerSessionIdx = si;
    pickerExIdx = ei;
    exSearch = '';
    pickerOpen = true;
    if (allExercises.length === 0) {
      exLoading = true;
      try { allExercises = await api.exercises.list(); }
      catch {}
      exLoading = false;
    }
  }

  function selectExercise(ex) {
    const newEx = {
      exercise_id: ex.id,
      exercise_name: ex.name,
      sets: 3,
      reps_min: 8,
      reps_max: 12,
      rir: 2,
      notes: '',
    };
    cfgSessions = cfgSessions.map((s, i) => {
      if (i !== pickerSessionIdx) return s;
      const exs = [...s.exercises];
      if (pickerExIdx === -1) {
        exs.push(newEx);
      } else {
        exs[pickerExIdx] = { ...exs[pickerExIdx], exercise_id: ex.id, exercise_name: ex.name };
      }
      return { ...s, exercises: exs };
    });
    pickerOpen = false;
  }

  $: filteredExercises = allExercises.filter(e =>
    !exSearch || e.name.toLowerCase().includes(exSearch.toLowerCase())
  ).slice(0, 60);

  async function quickInstall(slug) {
    installing = slug + '_quick';
    installError = null;
    try {
      await api.programs.installLibraryProgram(slug);
      goto('/program');
    } catch (e) {
      installError = e.message;
      installing = null;
    }
  }

  async function installCustomized() {
    installing = customizing + '_custom';
    installError = null;
    const overrides = {};
    for (const s of cfgSessions) overrides[s.label] = s.exercises;
    try {
      await api.programs.installLibraryProgram(customizing, {
        weeks: cfgWeeks,
        deload_week: cfgDeload,
        day_slots: cfgDaySlots,
        session_overrides: overrides,
      });
      goto('/program');
    } catch (e) {
      installError = e.message;
      installing = null;
    }
  }

  function diffColor(d) {
    if (d === 'beginner') return '#50c880';
    if (d === 'intermediate') return 'var(--accent)';
    return '#e8365d';
  }
  function goalColor(g) { return g === 'strength' ? '#5090e8' : '#cd853f'; }

  $: isInstalling = installing !== null;
</script>

<div class="page">
  <div class="page-header">
    <h1 class="page-title">Programs Library</h1>
    <p class="page-sub">Pick a program and run it, or customize before you start.</p>
  </div>

  {#if error}
    <div class="banner err">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">Loading…</div>
  {:else}
    <div class="cards">
      {#each programs as prog}
        {@const isOpen = customizing === prog.slug}
        <div class="card" class:expanded={isOpen}>

          <!-- Card header (always visible) -->
          <div class="card-top">
            <div class="card-title-row">
              <div>
                <div class="card-name">{prog.name}</div>
                <div class="card-author">{prog.author}</div>
              </div>
              <div class="card-badges">
                <span class="badge" style="color:{goalColor(prog.goal)};border-color:{goalColor(prog.goal)}">{prog.goal}</span>
                <span class="badge" style="color:{diffColor(prog.difficulty)};border-color:{diffColor(prog.difficulty)}">{prog.difficulty}</span>
              </div>
            </div>
            <p class="card-desc">{prog.description}</p>
            <div class="card-meta">
              <span class="meta-pill">{prog.days_per_week} days/week</span>
              <span class="meta-pill">{prog.weeks} weeks</span>
            </div>
          </div>

          {#if !isOpen}
            <div class="card-actions">
              <button class="btn-outline" disabled={isInstalling} on:click={() => openCustomizer(prog)}>Customize</button>
              <button class="btn-primary" disabled={isInstalling} on:click={() => quickInstall(prog.slug)}>
                {installing === prog.slug + '_quick' ? 'Starting…' : 'Start'}
              </button>
            </div>
            <div style="padding: 0 1.1rem 0.85rem;">
              <button class="btn-custom-sched" on:click={() => goto(`/program/builder?template=${prog.slug}`)}>
                ↗ Run as custom schedule (choose days & rotation)
              </button>
            </div>
          {:else}
            <!-- ── Customizer ── -->
            <div class="customizer">
              {#if previewLoading}
                <div class="loading" style="padding:1rem 0">Loading program…</div>
              {:else if preview}

                <!-- Duration -->
                <div class="section-label">Duration</div>
                <div class="row-2">
                  <label class="field">
                    <span>Total weeks</span>
                    <input type="number" min="1" max="52" bind:value={cfgWeeks}
                      on:change={() => { if (cfgDeload > cfgWeeks) cfgDeload = cfgWeeks; }} />
                  </label>
                  <label class="field">
                    <span>Recovery (deload) on week</span>
                    <input type="number" min="1" max={cfgWeeks} bind:value={cfgDeload} />
                  </label>
                </div>

                <!-- Training days -->
                <div class="section-label">Training Days</div>
                <div class="day-toggles">
                  {#each DAYS as d, i}
                    <button
                      class="day-btn"
                      class:active={cfgDaySlots.includes(i)}
                      on:click={() => toggleDay(i)}
                      title={DAY_FULL[i]}
                    >{d}</button>
                  {/each}
                </div>
                <div class="day-hint">{cfgDaySlots.length} day{cfgDaySlots.length !== 1 ? 's' : ''}/week selected</div>

                <!-- Sessions -->
                <div class="section-label">Sessions</div>
                {#each cfgSessions as sess, si}
                  <div class="session-block">
                    <div class="session-label">{sess.label}</div>
                    {#each sess.exercises as ex, ei}
                      <div class="ex-row">
                        <div class="ex-name" title={ex.exercise_name}>{ex.exercise_name}</div>
                        <div class="ex-fields">
                          <label class="mini-field">
                            <span>Sets</span>
                            <input type="number" min="1" max="10" value={ex.sets}
                              on:change={e => updateExField(si, ei, 'sets', e.target.value)} />
                          </label>
                          <label class="mini-field">
                            <span>Reps</span>
                            <input type="text" value="{ex.reps_min}–{ex.reps_max}"
                              on:blur={e => {
                                const m = e.target.value.match(/^(\d+)[–\-](\d+)$/);
                                if (m) { updateExField(si, ei, 'reps_min', m[1]); updateExField(si, ei, 'reps_max', m[2]); }
                              }} />
                          </label>
                          <label class="mini-field">
                            <span title="Reps In Reserve — reps left before failure">RIR</span>
                            <input type="number" min="0" max="5" value={ex.rir}
                              on:change={e => updateExField(si, ei, 'rir', e.target.value)} />
                          </label>
                        </div>
                        <div class="ex-btns">
                          <button class="icon-btn" title="Swap exercise" on:click={() => openPicker(si, ei)}>⇄</button>
                          <button class="icon-btn danger" title="Remove" on:click={() => removeEx(si, ei)}>✕</button>
                        </div>
                      </div>
                    {/each}
                    <button class="add-ex-btn" on:click={() => openPicker(si, -1)}>+ Add Exercise</button>
                  </div>
                {/each}
              {/if}

              {#if installError}
                <div class="banner err" style="margin-top:0.75rem">{installError}</div>
              {/if}

              <div class="customizer-actions">
                <button class="btn-outline" on:click={closeCustomizer}>Cancel</button>
                <button class="btn-primary" disabled={isInstalling || previewLoading} on:click={installCustomized}>
                  {installing === customizing + '_custom' ? 'Starting…' : 'Start Program'}
                </button>
              </div>
            </div>
          {/if}

        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Exercise picker modal -->
{#if pickerOpen}
  <div class="overlay" on:click|self={() => pickerOpen = false}>
    <div class="picker-sheet">
      <div class="picker-title">
        {pickerExIdx === -1 ? 'Add Exercise' : 'Swap Exercise'}
      </div>
      <input class="picker-search" type="text" placeholder="Search exercises…" bind:value={exSearch} autofocus />
      {#if exLoading}
        <div class="loading" style="padding:1rem">Loading…</div>
      {:else}
        <div class="picker-list">
          {#each filteredExercises as ex}
            <button class="picker-item" on:click={() => selectExercise(ex)}>
              <span class="picker-name">{ex.name}</span>
              <span class="picker-meta">{ex.primary_muscles?.[0] ?? ''}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .page {
    padding: 1rem 1rem 6rem;
    max-width: 640px;
    margin: 0 auto;
  }

  .page-header { margin-bottom: 1.5rem; }
  .page-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.6rem;
    color: var(--text);
    margin: 0 0 0.25rem;
  }
  .page-sub { font-size: 0.85rem; color: var(--muted); margin: 0; }

  .loading { color: var(--muted); font-size: 0.9rem; text-align: center; padding: 2rem 0; }

  .banner { padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 1rem; }
  .banner.err { background: rgba(232,54,93,.12); color: #e8365d; border: 1px solid rgba(232,54,93,.3); }

  .cards { display: flex; flex-direction: column; gap: 1rem; }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.2s;
  }
  .card.expanded { border-color: var(--accent); }

  .card-top { padding: 1.1rem 1.1rem 0.75rem; }

  .card-title-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }
  .card-name { font-family: 'DM Serif Display', serif; font-size: 1.1rem; color: var(--text); }
  .card-author { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }

  .card-badges { display: flex; flex-direction: column; gap: 0.25rem; align-items: flex-end; }

  .badge {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .05em;
    padding: 0.15rem 0.45rem;
    border-radius: 20px;
    border: 1px solid currentColor;
    white-space: nowrap;
  }

  .card-desc { font-size: 0.82rem; color: var(--text-dim, #999); line-height: 1.5; margin: 0 0 0.6rem; }

  .card-meta { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .meta-pill {
    font-size: 0.72rem;
    color: var(--muted);
    background: rgba(255,255,255,.05);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 0.15rem 0.45rem;
  }

  .card-actions {
    display: flex;
    gap: 0.5rem;
    padding: 0 1.1rem 1rem;
  }

  .btn-primary {
    flex: 1;
    padding: 0.65rem;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity .15s;
  }
  .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
  .btn-primary:not(:disabled):active { opacity: .8; }

  .btn-outline {
    flex: 0 0 auto;
    padding: 0.65rem 1rem;
    background: transparent;
    color: var(--muted);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: border-color .15s, color .15s;
  }
  .btn-outline:hover { border-color: var(--accent); color: var(--accent); }
  .btn-outline:disabled { opacity: .5; cursor: not-allowed; }

  .btn-custom-sched {
    display: block;
    width: 100%;
    padding: 0.55rem 1rem;
    background: rgba(232,160,64,0.08);
    border: 1px solid rgba(232,160,64,0.3);
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--accent);
    cursor: pointer;
    text-align: center;
    transition: background .15s, border-color .15s;
  }
  .btn-custom-sched:hover { background: rgba(232,160,64,0.16); border-color: var(--accent); }

  /* ── Customizer ── */
  .customizer {
    padding: 0.75rem 1.1rem 1rem;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .section-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--muted);
    margin-bottom: -0.25rem;
  }

  .row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }

  .field { display: flex; flex-direction: column; gap: 0.2rem; }
  .field span { font-size: 0.75rem; color: var(--muted); }
  .field input {
    background: var(--surface-2, #111);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 0.9rem;
    padding: 0.45rem 0.6rem;
    width: 100%;
    box-sizing: border-box;
  }
  .field input:focus { outline: none; border-color: var(--accent); }

  .day-toggles { display: flex; gap: 0.35rem; }
  .day-btn {
    width: 34px; height: 34px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--muted);
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: background .15s, color .15s, border-color .15s;
  }
  .day-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }
  .day-hint { font-size: 0.72rem; color: var(--muted); margin-top: -0.25rem; }

  .session-block {
    background: rgba(255,255,255,.03);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.7rem;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }
  .session-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.15rem;
  }

  .ex-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .ex-name {
    flex: 1;
    font-size: 0.78rem;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }
  .ex-fields { display: flex; gap: 0.3rem; flex-shrink: 0; }
  .mini-field {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.1rem;
  }
  .mini-field span { font-size: 0.6rem; color: var(--muted); text-transform: uppercase; }
  .mini-field input {
    width: 44px;
    text-align: center;
    background: var(--surface-2, #111);
    border: 1px solid var(--border);
    border-radius: 5px;
    color: var(--text);
    font-size: 0.78rem;
    padding: 0.25rem 0;
  }
  .mini-field input:focus { outline: none; border-color: var(--accent); }

  .ex-btns { display: flex; gap: 0.2rem; flex-shrink: 0; }
  .icon-btn {
    width: 26px; height: 26px;
    border-radius: 5px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--muted);
    font-size: 0.75rem;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: border-color .15s, color .15s;
  }
  .icon-btn:hover { border-color: var(--accent); color: var(--accent); }
  .icon-btn.danger:hover { border-color: #e8365d; color: #e8365d; }

  .add-ex-btn {
    align-self: flex-start;
    background: transparent;
    border: 1px dashed var(--border);
    border-radius: 6px;
    color: var(--muted);
    font-size: 0.75rem;
    padding: 0.3rem 0.7rem;
    cursor: pointer;
    transition: border-color .15s, color .15s;
  }
  .add-ex-btn:hover { border-color: var(--accent); color: var(--accent); }

  .customizer-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.25rem;
  }

  /* ── Exercise picker ── */
  .overlay {
    position: fixed; inset: 0;
    background: rgba(0,0,0,.6);
    z-index: 200;
    display: flex; align-items: flex-end; justify-content: center;
  }
  .picker-sheet {
    background: var(--surface);
    border-radius: 16px 16px 0 0;
    width: 100%;
    max-width: 600px;
    max-height: 70vh;
    display: flex;
    flex-direction: column;
    padding: 1rem 1rem 0;
  }
  .picker-title { font-size: 1rem; font-weight: 600; color: var(--text); margin-bottom: 0.75rem; }
  .picker-search {
    background: var(--surface-2, #111);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 0.9rem;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.75rem;
    width: 100%;
    box-sizing: border-box;
  }
  .picker-search:focus { outline: none; border-color: var(--accent); }
  .picker-list {
    overflow-y: auto;
    flex: 1;
    padding-bottom: 1rem;
  }
  .picker-item {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.65rem 0.5rem;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    font-size: 0.875rem;
    cursor: pointer;
    text-align: left;
    transition: background .1s;
  }
  .picker-item:hover { background: rgba(255,255,255,.04); }
  .picker-meta { font-size: 0.72rem; color: var(--muted); }
</style>
