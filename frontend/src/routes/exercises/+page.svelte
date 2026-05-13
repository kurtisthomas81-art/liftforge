<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let exercises = [];
  let filtered = [];
  let loading = true;
  let search = '';
  let muscleFilter = '';
  let patternFilter = '';

  let expandedId = null;
  let exDetail = null;
  let exHistory = [];
  let loadingDetail = false;
  let affectedExercises = {};

  // Edit state
  let editingId = null;
  let editForm = {};
  let editSaving = false;
  let editError = '';

  // Delete state
  let deleteConfirmId = null;
  let deleteError = '';
  let deleting = false;

  const ALL_MUSCLES = ['chest','back','shoulders','biceps','triceps','quads','hamstrings','glutes','calves','forearms','abs','traps','lats'];
  const MUSCLES = ['chest','back','shoulders','biceps','triceps','quads','hamstrings','glutes','calves','forearms','abs'];
  const PATTERNS = ['push','pull','hinge','squat','carry','core','isolation'];
  const EQUIPMENT_LIST = ['barbell','dumbbell','cable_machine','machine','kettlebell','bodyweight','bench','rack','pull_up_bar','resistance_band','leg_press','smith_machine'];
  const MOVEMENT_PATTERNS = ['push','pull','hinge','squat','carry','core','isolation'];
  const MECHANICS_LIST = ['compound','isolation'];
  const FORCE_LIST = ['push','pull','static','hinge'];

  const CAT_COLOR = { push:'var(--push)', pull:'var(--pull)', squat:'var(--squat)', hinge:'var(--hinge)', core:'var(--core)' };

  onMount(async () => {
    [exercises] = await Promise.all([
      api.exercises.list(),
      api.injuries.affectedExercises().then(r => { affectedExercises = r; }).catch(() => {}),
    ]);
    filtered = exercises;
    loading = false;
  });

  function applyFilters() {
    let list = exercises;
    if (muscleFilter) list = list.filter(e => e.primary_muscles.includes(muscleFilter) || e.secondary_muscles.includes(muscleFilter));
    if (patternFilter) list = list.filter(e => e.movement_pattern === patternFilter);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(e => e.name.toLowerCase().includes(q) || e.aliases.some(a => a.toLowerCase().includes(q)));
    }
    filtered = list;
  }

  $: { search; muscleFilter; patternFilter; applyFilters(); }

  async function toggleExpand(ex) {
    if (editingId === ex.id) return;
    if (expandedId === ex.id) { expandedId = null; exDetail = null; exHistory = []; deleteConfirmId = null; deleteError = ''; return; }
    expandedId = ex.id;
    deleteConfirmId = null;
    deleteError = '';
    editingId = null;
    loadingDetail = true;
    [exDetail, exHistory] = await Promise.all([
      api.exercises.get(ex.id).catch(() => null),
      api.history.exerciseProgression(ex.id).catch(() => []),
    ]);
    loadingDetail = false;
  }

  function catColor(p) { return CAT_COLOR[p] || 'var(--muted)'; }

  $: bestOneRM = exHistory.length ? Math.max(...exHistory.map(d => d.estimated_1rm)).toFixed(1) : null;
  $: lastSession = exHistory.length ? exHistory[exHistory.length - 1] : null;

  function startEdit(ex) {
    editingId = ex.id;
    editError = '';
    editForm = {
      name: ex.name,
      aliases: ex.aliases.join(', '),
      notes: exDetail?.notes ?? '',
      primary_muscles: [...(exDetail?.primary_muscles ?? ex.primary_muscles)],
      secondary_muscles: [...(exDetail?.secondary_muscles ?? ex.secondary_muscles)],
      equipment_required: [...(exDetail?.equipment_required ?? ex.equipment_required ?? [])],
      movement_pattern: ex.movement_pattern,
      mechanics: exDetail?.mechanics ?? ex.mechanics ?? 'compound',
      force: exDetail?.force ?? ex.force ?? 'push',
      is_bilateral: exDetail?.is_bilateral ?? true,
    };
  }

  function cancelEdit() {
    editingId = null;
    editError = '';
  }

  function toggleMuscle(list, muscle) {
    const idx = list.indexOf(muscle);
    if (idx >= 0) list.splice(idx, 1);
    else list.push(muscle);
    return [...list];
  }

  function toggleEquipment(muscle) {
    editForm.equipment_required = toggleMuscle(editForm.equipment_required, muscle);
  }

  async function saveEdit(ex) {
    editSaving = true;
    editError = '';
    try {
      const payload = {
        name: editForm.name.trim(),
        aliases: editForm.aliases.split(',').map(a => a.trim()).filter(Boolean),
        notes: editForm.notes.trim(),
        primary_muscles: editForm.primary_muscles,
        secondary_muscles: editForm.secondary_muscles,
        equipment_required: editForm.equipment_required,
        movement_pattern: editForm.movement_pattern,
        mechanics: editForm.mechanics,
        force: editForm.force,
        is_bilateral: editForm.is_bilateral,
      };
      const updated = await api.exercises.update(ex.id, payload);
      // Update local lists
      exercises = exercises.map(e => e.id === ex.id ? { ...e, ...updated } : e);
      filtered = filtered.map(e => e.id === ex.id ? { ...e, ...updated } : e);
      exDetail = updated;
      editingId = null;
    } catch (err) {
      editError = err.message || 'Save failed';
    } finally {
      editSaving = false;
    }
  }

  async function executeDelete(ex) {
    deleting = true;
    deleteError = '';
    try {
      await api.exercises.delete(ex.id);
      exercises = exercises.filter(e => e.id !== ex.id);
      filtered = filtered.filter(e => e.id !== ex.id);
      expandedId = null;
      exDetail = null;
      deleteConfirmId = null;
    } catch (err) {
      const msg = err.message || '';
      const match = msg.match(/\d+: (.+)/);
      deleteError = match ? JSON.parse(match[1]).detail : 'Could not delete exercise.';
    } finally {
      deleting = false;
    }
  }
</script>

<svelte:head><title>Exercise Library — LiftForge</title></svelte:head>

<div class="page-title">Exercise <em>Library</em></div>

<!-- Search -->
<div class="search-wrap" style="margin-bottom:12px;">
  <span class="search-icon">⊞</span>
  <input bind:value={search} placeholder="Search exercises or aliases…" />
</div>

<!-- Category filter pills -->
<div class="filter-chips" style="margin-bottom:10px;">
  <button class="chip" class:active={patternFilter === ''} on:click={() => patternFilter = ''}>All</button>
  {#each PATTERNS as p}
    <button class="chip" class:active={patternFilter === p}
      style={patternFilter === p ? `background:${catColor(p)}18;border-color:${catColor(p)};color:${catColor(p)}` : ''}
      on:click={() => patternFilter = patternFilter === p ? '' : p}>{p}</button>
  {/each}
</div>

<!-- Muscle filter pills -->
<div class="filter-chips" style="margin-bottom:14px;">
  <button class="chip" class:active={muscleFilter === ''} on:click={() => muscleFilter = ''}>All muscles</button>
  {#each MUSCLES as m}
    <button class="chip" class:active={muscleFilter === m} on:click={() => muscleFilter = muscleFilter === m ? '' : m}>{m}</button>
  {/each}
</div>

{#if loading}
  <div class="flex items-center gap-3" style="padding:24px 0;"><div class="spinner"></div></div>
{:else}
  <div class="ex-count">{filtered.length} exercise{filtered.length !== 1 ? 's' : ''}</div>

  <div class="ex-list">
    {#each filtered as ex}
      <div class="ex-row" class:is-expanded={expandedId === ex.id}>
        <button class="ex-row-btn" on:click={() => toggleExpand(ex)}>
          <div class="ex-row-main">
            <div class="ex-row-name">{ex.name}</div>
            <div class="ex-row-meta">{ex.primary_muscles.join(', ')}</div>
          </div>
          {#if affectedExercises[ex.id]}
            <span title="Affected: {affectedExercises[ex.id].join(', ')}" style="font-size:13px; margin-right:2px;">⚠</span>
          {/if}
          <span class="ex-cat-badge" style="color:{catColor(ex.movement_pattern)};border-color:{catColor(ex.movement_pattern)}35;background:{catColor(ex.movement_pattern)}14">
            {ex.movement_pattern}
          </span>
          <span class="ex-expand-icon">{expandedId === ex.id ? '▲' : '▼'}</span>
        </button>

        {#if expandedId === ex.id}
          <div class="ex-detail">
            {#if loadingDetail}
              <div class="flex items-center gap-2" style="padding:8px 0;"><div class="spinner"></div></div>

            {:else if editingId === ex.id}
              <!-- ── Edit form ──────────────────────────────── -->
              <div class="edit-form">
                <div class="edit-field">
                  <label class="edit-label">Name</label>
                  <input class="edit-input" bind:value={editForm.name} />
                </div>
                <div class="edit-field">
                  <label class="edit-label">Aliases <span class="edit-hint">(comma-separated)</span></label>
                  <input class="edit-input" bind:value={editForm.aliases} placeholder="e.g. bench, flat press" />
                </div>
                <div class="edit-field">
                  <label class="edit-label">Notes / cue</label>
                  <textarea class="edit-textarea" bind:value={editForm.notes} rows="2"></textarea>
                </div>

                <div class="edit-field">
                  <label class="edit-label">Primary muscles</label>
                  <div class="edit-checks">
                    {#each ALL_MUSCLES as m}
                      <label class="check-pill" class:checked={editForm.primary_muscles.includes(m)}>
                        <input type="checkbox" checked={editForm.primary_muscles.includes(m)}
                          on:change={() => editForm.primary_muscles = toggleMuscle(editForm.primary_muscles, m)} />
                        {m}
                      </label>
                    {/each}
                  </div>
                </div>

                <div class="edit-field">
                  <label class="edit-label">Secondary muscles</label>
                  <div class="edit-checks">
                    {#each ALL_MUSCLES as m}
                      <label class="check-pill" class:checked={editForm.secondary_muscles.includes(m)}>
                        <input type="checkbox" checked={editForm.secondary_muscles.includes(m)}
                          on:change={() => editForm.secondary_muscles = toggleMuscle(editForm.secondary_muscles, m)} />
                        {m}
                      </label>
                    {/each}
                  </div>
                </div>

                <div class="edit-field">
                  <label class="edit-label">Equipment</label>
                  <div class="edit-checks">
                    {#each EQUIPMENT_LIST as eq}
                      <label class="check-pill" class:checked={editForm.equipment_required.includes(eq)}>
                        <input type="checkbox" checked={editForm.equipment_required.includes(eq)}
                          on:change={() => toggleEquipment(eq)} />
                        {eq.replace('_', ' ')}
                      </label>
                    {/each}
                  </div>
                </div>

                <div class="edit-row-3">
                  <div class="edit-field">
                    <label class="edit-label">Pattern</label>
                    <select class="edit-select" bind:value={editForm.movement_pattern}>
                      {#each MOVEMENT_PATTERNS as p}<option value={p}>{p}</option>{/each}
                    </select>
                  </div>
                  <div class="edit-field">
                    <label class="edit-label">Mechanics</label>
                    <select class="edit-select" bind:value={editForm.mechanics}>
                      {#each MECHANICS_LIST as m}<option value={m}>{m}</option>{/each}
                    </select>
                  </div>
                  <div class="edit-field">
                    <label class="edit-label">Force</label>
                    <select class="edit-select" bind:value={editForm.force}>
                      {#each FORCE_LIST as f}<option value={f}>{f}</option>{/each}
                    </select>
                  </div>
                </div>

                <div class="edit-field" style="flex-direction:row;align-items:center;gap:10px;">
                  <label class="edit-label" style="margin:0;">Bilateral</label>
                  <input type="checkbox" bind:checked={editForm.is_bilateral} style="width:16px;height:16px;cursor:pointer;" />
                </div>

                {#if editError}
                  <div class="edit-error">{editError}</div>
                {/if}

                <div class="edit-actions">
                  <button class="btn-primary" on:click={() => saveEdit(ex)} disabled={editSaving}>
                    {editSaving ? 'Saving…' : 'Save'}
                  </button>
                  <button class="btn-ghost" on:click={cancelEdit} disabled={editSaving}>Cancel</button>
                </div>
              </div>

            {:else if exDetail}
              <!-- ── Normal detail view ─────────────────────── -->
              <div class="ex-stats-grid">
                <div class="ex-stat">
                  <div class="ex-stat-val">{bestOneRM ?? '—'}<span class="ex-stat-unit">lb</span></div>
                  <div class="ex-stat-lbl">Best est. 1RM</div>
                </div>
                <div class="ex-stat">
                  <div class="ex-stat-val">
                    {#if lastSession}{lastSession.max_weight ?? '—'}{:else}—{/if}
                    <span class="ex-stat-unit">lb</span>
                  </div>
                  <div class="ex-stat-lbl">Last Session</div>
                </div>
              </div>

              {#if exDetail.notes}
                <div class="ex-cue">{exDetail.notes}</div>
              {/if}

              <div class="ex-muscles">
                {#each exDetail.primary_muscles as m}
                  <span class="tag tag-primary">{m}</span>
                {/each}
                {#each exDetail.secondary_muscles as m}
                  <span class="tag">{m}</span>
                {/each}
              </div>

              <a href="/log" class="add-to-workout-btn">+ Add to Workout</a>
              <a href="/1rm-test?exercise={ex.id}" class="test-1rm-btn">⊗ Test 1RM</a>

              <!-- Edit / Delete row -->
              <div class="mgmt-row">
                <button class="btn-mgmt" on:click={() => startEdit(ex)}>Edit</button>
                {#if deleteConfirmId !== ex.id}
                  <button class="btn-mgmt btn-mgmt-danger" on:click={() => { deleteConfirmId = ex.id; deleteError = ''; }}>Delete</button>
                {:else}
                  <div class="delete-confirm">
                    <span class="delete-confirm-msg">Delete "{ex.name}"? This cannot be undone.</span>
                    {#if deleteError}
                      <div class="delete-error">{deleteError}</div>
                    {/if}
                    <div class="delete-confirm-btns">
                      <button class="btn-danger-solid" on:click={() => executeDelete(ex)} disabled={deleting}>
                        {deleting ? 'Deleting…' : 'Confirm Delete'}
                      </button>
                      <button class="btn-ghost" on:click={() => { deleteConfirmId = null; deleteError = ''; }} disabled={deleting}>Cancel</button>
                    </div>
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        {/if}
      </div>
    {/each}
  </div>
{/if}

<style>
  .page-title { font-family:var(--serif); font-size:26px; color:var(--text); margin-bottom:16px; line-height:1; }
  .page-title em { font-style:italic; color:var(--accent); }

  .ex-count { font-size:11px; color:var(--muted); margin-bottom:10px; }

  .ex-list { display:flex; flex-direction:column; }
  .ex-row {
    border-bottom: 1px solid var(--bdr);
    background: transparent; transition: background 0.15s;
  }
  .ex-row.is-expanded { background: var(--surf); border-radius: var(--radius-lg); border: 1px solid var(--bdr-2); margin-bottom: 4px; overflow: hidden; }
  .ex-row-btn {
    width:100%; text-align:left; background:transparent; border:none;
    padding:12px 4px; cursor:pointer;
    display:flex; align-items:center; gap:10px;
  }
  .ex-row-main { flex:1; }
  .ex-row-name { font-family:var(--serif); font-size:17px; color:var(--text); line-height:1; }
  .ex-row-meta { font-size:11px; color:var(--muted); margin-top:3px; }
  .ex-cat-badge {
    font-size:9px; padding:2px 8px; border-radius:3px;
    border:1px solid; text-transform:uppercase; font-weight:600; letter-spacing:0.06em;
    white-space:nowrap;
  }
  .ex-expand-icon { font-size:10px; color:var(--faint); width:16px; text-align:right; }

  .ex-detail { padding:12px 16px 16px; border-top:1px solid var(--bdr); }
  .ex-stats-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:12px; }
  .ex-stat {
    background: var(--surf-2); border:1px solid var(--bdr-2);
    border-radius: var(--radius); padding:10px 12px;
  }
  .ex-stat-val { font-family:var(--serif); font-size:20px; color:var(--accent); line-height:1; }
  .ex-stat-unit { font-size:11px; color:var(--muted); margin-left:3px; }
  .ex-stat-lbl { font-size:10px; color:var(--muted); margin-top:3px; }
  .ex-cue {
    font-style:italic; font-size:12px; color:var(--muted);
    line-height:1.6; margin-bottom:10px; padding:8px 10px;
    border-left:2px solid var(--bdr-2); background:var(--surf-2);
    border-radius:0 var(--radius) var(--radius) 0;
  }
  .ex-muscles { display:flex; flex-wrap:wrap; gap:4px; margin-bottom:12px; }
  .add-to-workout-btn {
    display:block; width:100%; text-align:center;
    background:var(--accent); color:#fff; border:none;
    border-radius:var(--radius-lg); padding:11px;
    font-size:13px; font-weight:600; text-decoration:none;
    transition:background 0.15s;
  }
  .add-to-workout-btn:hover { background:#f05070; }
  .test-1rm-btn {
    display:block; width:100%; text-align:center;
    background:transparent; color:var(--muted);
    border:1px solid var(--bdr-2);
    border-radius:var(--radius-lg); padding:9px;
    font-size:12px; font-weight:600; text-decoration:none;
    margin-top:8px; transition:all 0.15s;
  }
  .test-1rm-btn:hover { border-color:var(--accent); color:var(--accent); }

  /* Management row */
  .mgmt-row { display:flex; gap:8px; margin-top:10px; align-items:flex-start; flex-wrap:wrap; }
  .btn-mgmt {
    flex:1; padding:8px; background:transparent;
    border:1px solid var(--bdr-2); border-radius:var(--radius);
    font-size:12px; color:var(--muted); cursor:pointer; transition:all 0.15s;
  }
  .btn-mgmt:hover { border-color:var(--accent); color:var(--accent); }
  .btn-mgmt-danger:hover { border-color:var(--danger, #e8365d); color:var(--danger, #e8365d); }

  /* Delete confirmation */
  .delete-confirm { width:100%; }
  .delete-confirm-msg { font-size:12px; color:var(--muted); display:block; margin-bottom:8px; }
  .delete-error { font-size:12px; color:var(--danger, #e8365d); margin-bottom:8px; padding:6px 10px; background:rgba(232,54,93,0.08); border-radius:var(--radius); }
  .delete-confirm-btns { display:flex; gap:8px; }
  .btn-danger-solid {
    flex:1; padding:9px; background:var(--danger, #e8365d); color:#fff;
    border:none; border-radius:var(--radius); font-size:12px; font-weight:600;
    cursor:pointer; transition:opacity 0.15s;
  }
  .btn-danger-solid:disabled { opacity:0.5; cursor:not-allowed; }

  /* Edit form */
  .edit-form { display:flex; flex-direction:column; gap:14px; }
  .edit-field { display:flex; flex-direction:column; gap:4px; }
  .edit-label { font-size:11px; font-weight:600; color:var(--accent); text-transform:uppercase; letter-spacing:0.06em; }
  .edit-hint { font-weight:400; color:var(--muted); text-transform:none; letter-spacing:0; }
  .edit-input, .edit-select, .edit-textarea {
    background:var(--surf-2); border:1px solid var(--bdr-2);
    border-radius:var(--radius); padding:8px 10px;
    font-size:13px; color:var(--text); width:100%; box-sizing:border-box;
  }
  .edit-textarea { resize:vertical; min-height:56px; font-family:inherit; }
  .edit-select { cursor:pointer; }
  .edit-checks { display:flex; flex-wrap:wrap; gap:6px; }
  .check-pill {
    display:flex; align-items:center; gap:5px;
    padding:4px 10px; border-radius:3px; font-size:11px;
    border:1px solid var(--bdr-2); cursor:pointer; transition:all 0.12s;
    color:var(--muted);
  }
  .check-pill input { display:none; }
  .check-pill.checked { border-color:var(--accent); color:var(--accent); background:rgba(var(--accent-rgb,205,133,63),0.1); }
  .edit-row-3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; }
  .edit-error { font-size:12px; color:var(--danger, #e8365d); padding:6px 10px; background:rgba(232,54,93,0.08); border-radius:var(--radius); }
  .edit-actions { display:flex; gap:8px; }
  .btn-primary {
    flex:1; padding:10px; background:var(--accent); color:#fff;
    border:none; border-radius:var(--radius); font-size:13px; font-weight:600;
    cursor:pointer; transition:opacity 0.15s;
  }
  .btn-primary:disabled { opacity:0.5; cursor:not-allowed; }
  .btn-ghost {
    flex:1; padding:10px; background:transparent; color:var(--muted);
    border:1px solid var(--bdr-2); border-radius:var(--radius);
    font-size:13px; cursor:pointer; transition:all 0.15s;
  }
  .btn-ghost:hover { border-color:var(--accent); color:var(--accent); }
  .btn-ghost:disabled { opacity:0.5; cursor:not-allowed; }
</style>
