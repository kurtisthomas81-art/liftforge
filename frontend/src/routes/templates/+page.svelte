<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let templates = [];
  let loading = true;

  // Modal state
  let showModal = false;
  let editingTemplate = null;  // null = new, object = edit
  let modalName = '';
  let modalNotes = '';
  let modalExercises = [];   // { exercise_id, exercise_name, order_in_template, target_sets, target_reps_min, target_reps_max, target_rir, notes }

  // Exercise picker inside modal
  let allExercises = [];
  let exerciseSearch = '';
  let showExercisePicker = false;

  const MUSCLES = ['chest','back','shoulders','biceps','triceps','quads','hamstrings','glutes','calves','abs'];

  onMount(async () => {
    templates = await api.templates.list();
    loading = false;
  });

  async function openNew() {
    if (allExercises.length === 0) {
      allExercises = await api.exercises.list();
    }
    editingTemplate = null;
    modalName = '';
    modalNotes = '';
    modalExercises = [];
    exerciseSearch = '';
    showModal = true;
  }

  async function openEdit(tpl) {
    if (allExercises.length === 0) {
      allExercises = await api.exercises.list();
    }
    const detail = await api.templates.get(tpl.id);
    editingTemplate = detail;
    modalName = detail.name;
    modalNotes = detail.notes;
    modalExercises = detail.exercises.map(e => ({ ...e }));
    exerciseSearch = '';
    showModal = true;
  }

  function closeModal() {
    showModal = false;
    editingTemplate = null;
    showExercisePicker = false;
  }

  async function saveTemplate() {
    if (!modalName.trim()) return;
    const payload = {
      name: modalName.trim(),
      notes: modalNotes.trim(),
      exercises: modalExercises.map((e, i) => ({
        exercise_id: e.exercise_id,
        order_in_template: i + 1,
        target_sets: Number(e.target_sets),
        target_reps_min: Number(e.target_reps_min),
        target_reps_max: Number(e.target_reps_max),
        target_rir: Number(e.target_rir),
        notes: e.notes || '',
      })),
    };
    if (editingTemplate) {
      await api.templates.update(editingTemplate.id, payload);
    } else {
      await api.templates.create(payload);
    }
    templates = await api.templates.list();
    closeModal();
  }

  async function deleteTemplate(id) {
    if (!confirm('Delete this template?')) return;
    await api.templates.delete(id);
    templates = templates.filter(t => t.id !== id);
  }

  async function startTemplate(id) {
    const result = await api.templates.start(id);
    goto('/log');
  }

  function addExerciseToModal(ex) {
    if (modalExercises.find(e => e.exercise_id === ex.id)) return;
    modalExercises = [...modalExercises, {
      exercise_id: ex.id,
      exercise_name: ex.name,
      order_in_template: modalExercises.length + 1,
      target_sets: 3,
      target_reps_min: 8,
      target_reps_max: 12,
      target_rir: 2,
      notes: '',
    }];
    exerciseSearch = '';
    showExercisePicker = false;
  }

  function removeExercise(idx) {
    modalExercises = modalExercises.filter((_, i) => i !== idx);
  }

  function moveExercise(idx, dir) {
    const arr = [...modalExercises];
    const swap = idx + dir;
    if (swap < 0 || swap >= arr.length) return;
    [arr[idx], arr[swap]] = [arr[swap], arr[idx]];
    modalExercises = arr;
  }

  $: filteredExercises = exerciseSearch
    ? allExercises.filter(e =>
        e.name.toLowerCase().includes(exerciseSearch.toLowerCase())
      ).slice(0, 12)
    : [];

  function muscleCategoryColor(muscles) {
    if (!muscles || muscles.length === 0) return 'var(--text-faint)';
    const m = muscles[0];
    if (['chest','shoulders','triceps'].includes(m)) return '#e8a040';
    if (['back','biceps'].includes(m)) return '#4a90d9';
    if (['quads','hamstrings','glutes','calves'].includes(m)) return '#4caf6a';
    return '#9b59b6';
  }
</script>

<svelte:head><title>Templates — LiftForge</title></svelte:head>

<div style="max-width:800px;">
  <div class="flex items-center justify-between mb-4">
    <h2 style="font-size:20px; font-weight:700;">Workout Templates</h2>
    <button class="btn-primary" on:click={openNew}>+ New Template</button>
  </div>

  {#if loading}
    <div class="flex items-center gap-3" style="padding:48px 0;">
      <div class="spinner"></div>
      <span style="color:var(--text-muted);">Loading...</span>
    </div>
  {:else if templates.length === 0}
    <div class="card">
      <div class="empty-state">
        <div class="empty-icon">◫</div>
        <p>No templates yet. Create one to quickly start a pre-built workout.</p>
        <button class="btn-primary" on:click={openNew}>Create Template</button>
      </div>
    </div>
  {:else}
    <div style="display:flex; flex-direction:column; gap:10px;">
      {#each templates as tpl}
        <div class="card" style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;">
          <div style="flex:1; min-width:0;">
            <div style="font-weight:600; font-size:15px; margin-bottom:4px;">{tpl.name}</div>
            <div style="display:flex; flex-wrap:wrap; gap:4px; align-items:center;">
              <span style="font-size:12px; color:var(--text-muted); margin-right:4px;">{tpl.exercise_count} exercises</span>
              {#each (tpl.muscles || []).slice(0, 5) as m}
                <span class="tag" style="color:{muscleCategoryColor([m])}; border-color:transparent; background:rgba(255,255,255,0.05);">{m}</span>
              {/each}
            </div>
          </div>
          <div class="flex gap-2">
            <button class="btn-primary btn-sm" on:click={() => startTemplate(tpl.id)}>Start</button>
            <button class="btn-secondary btn-sm" on:click={() => openEdit(tpl)}>Edit</button>
            <button class="btn-danger btn-sm" on:click={() => deleteTemplate(tpl.id)}>✕</button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- ── Template Modal ──────────────────────────────────────────────────────── -->
{#if showModal}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="modal-overlay" on:click|self={closeModal}>
    <div class="modal" style="max-width:620px; max-height:85vh;">
      <div class="modal-header">
        <h3>{editingTemplate ? 'Edit Template' : 'New Template'}</h3>
        <button class="btn-ghost btn-sm" on:click={closeModal}>✕</button>
      </div>

      <div class="modal-body" style="display:flex; flex-direction:column; gap:14px;">
        <!-- Name + notes -->
        <div>
          <label for="tplName">Template Name</label>
          <input id="tplName" bind:value={modalName} placeholder="e.g. Chest Day" autofocus />
        </div>
        <div>
          <label for="tplNotes">Notes (optional)</label>
          <input id="tplNotes" bind:value={modalNotes} placeholder="Any notes about this template" />
        </div>

        <!-- Exercise list -->
        <div>
          <div class="section-title mb-2">Exercises</div>

          {#if modalExercises.length === 0}
            <div style="color:var(--text-muted); font-size:13px; padding:12px 0;">No exercises added yet.</div>
          {:else}
            {#each modalExercises as ex, idx}
              <div style="display:flex; align-items:center; gap:8px; padding:8px 0; border-bottom:1px solid var(--border);">
                <div style="display:flex; flex-direction:column; gap:2px; margin-right:4px;">
                  <button class="btn-ghost btn-sm" style="padding:1px 5px; font-size:10px;" on:click={() => moveExercise(idx, -1)} disabled={idx === 0}>▲</button>
                  <button class="btn-ghost btn-sm" style="padding:1px 5px; font-size:10px;" on:click={() => moveExercise(idx, 1)} disabled={idx === modalExercises.length - 1}>▼</button>
                </div>
                <div style="flex:1; min-width:0;">
                  <div style="font-size:13px; font-weight:500; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{ex.exercise_name}</div>
                  <div style="display:flex; gap:6px; flex-wrap:wrap;">
                    <div style="display:flex; align-items:center; gap:4px;">
                      <label style="margin:0; font-size:11px; white-space:nowrap;">Sets</label>
                      <input type="number" min="1" max="20" bind:value={ex.target_sets} style="width:46px;" />
                    </div>
                    <div style="display:flex; align-items:center; gap:4px;">
                      <label style="margin:0; font-size:11px; white-space:nowrap;">Reps</label>
                      <input type="number" min="1" bind:value={ex.target_reps_min} style="width:46px;" />
                      <span style="color:var(--text-faint); font-size:11px;">–</span>
                      <input type="number" min="1" bind:value={ex.target_reps_max} style="width:46px;" />
                    </div>
                    <div style="display:flex; align-items:center; gap:4px;">
                      <label style="margin:0; font-size:11px;">RIR</label>
                      <input type="number" min="0" max="5" bind:value={ex.target_rir} style="width:42px;" />
                    </div>
                  </div>
                </div>
                <button class="btn-danger btn-sm" on:click={() => removeExercise(idx)} style="flex-shrink:0;">✕</button>
              </div>
            {/each}
          {/if}

          <!-- Add exercise search -->
          <div style="margin-top:10px; position:relative;">
            <input
              bind:value={exerciseSearch}
              placeholder="Search to add exercise..."
              on:focus={() => (showExercisePicker = true)}
              on:blur={() => setTimeout(() => (showExercisePicker = false), 150)}
            />
            {#if showExercisePicker && filteredExercises.length > 0}
              <div style="position:absolute; left:0; right:0; top:calc(100% + 2px); background:var(--surface); border:1px solid var(--border-2); border-radius:var(--radius); z-index:300; max-height:200px; overflow-y:auto; box-shadow:0 4px 16px rgba(0,0,0,0.4);">
                {#each filteredExercises as ex}
                  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
                  <div
                    style="padding:8px 12px; cursor:pointer; border-bottom:1px solid var(--border); font-size:13px;"
                    on:mousedown={() => addExerciseToModal(ex)}
                  >
                    <div style="font-weight:500;">{ex.name}</div>
                    <div style="color:var(--text-muted); font-size:11px;">{ex.primary_muscles.join(', ')}</div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-ghost" on:click={closeModal}>Cancel</button>
        <button class="btn-primary" on:click={saveTemplate} disabled={!modalName.trim()}>
          {editingTemplate ? 'Save Changes' : 'Create Template'}
        </button>
      </div>
    </div>
  </div>
{/if}
