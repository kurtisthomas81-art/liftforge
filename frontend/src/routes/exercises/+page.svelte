<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { formatDate } from '$lib/utils.js';

  let exercises = [];
  let filtered = [];
  let loading = true;
  let search = '';
  let muscleFilter = '';
  let equipFilter = '';
  let patternFilter = '';

  let selectedEx = null;
  let exDetail = null;
  let exHistory = [];
  let loadingDetail = false;

  const MUSCLES = ['chest','back','shoulders','biceps','triceps','quads','hamstrings','glutes','calves','abs'];
  const PATTERNS = ['push','pull','hinge','squat','core','isolation','carry'];
  const EQUIPMENT = ['barbell','dumbbells','cable_machine','machine','bodyweight','bands','pull_up_bar','bench','rack','ez_bar','trap_bar','leg_press','dip_bars'];

  onMount(async () => {
    exercises = await api.exercises.list();
    filtered = exercises;
    loading = false;
  });

  function applyFilters() {
    let list = exercises;
    if (muscleFilter) {
      list = list.filter(e =>
        e.primary_muscles.includes(muscleFilter) || e.secondary_muscles.includes(muscleFilter)
      );
    }
    if (equipFilter) {
      list = list.filter(e => e.equipment_required.includes(equipFilter));
    }
    if (patternFilter) {
      list = list.filter(e => e.movement_pattern === patternFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(e =>
        e.name.toLowerCase().includes(q) ||
        e.aliases.some(a => a.toLowerCase().includes(q))
      );
    }
    filtered = list;
  }

  $: { search; muscleFilter; equipFilter; patternFilter; applyFilters(); }

  async function selectExercise(ex) {
    if (selectedEx?.id === ex.id) {
      selectedEx = null;
      exDetail = null;
      exHistory = [];
      return;
    }
    selectedEx = ex;
    loadingDetail = true;
    [exDetail, exHistory] = await Promise.all([
      api.exercises.get(ex.id),
      api.history.exerciseProgression(ex.id),
    ]);
    loadingDetail = false;
  }

  function patternClass(p) {
    const map = { push: 'tag-push', pull: 'tag-pull', squat: 'tag-squat', hinge: 'tag-hinge', core: 'tag-core' };
    return map[p] || '';
  }
</script>

<svelte:head><title>Exercises — LiftForge</title></svelte:head>

<div style="max-width:1000px;">
  <h2 style="font-size:20px; font-weight:700; margin-bottom:20px;">Exercise Browser</h2>

  <!-- Search + filters -->
  <div class="card mb-4">
    <div class="search-wrap mb-3">
      <span class="search-icon">⊞</span>
      <input bind:value={search} placeholder="Search exercises or aliases..." />
    </div>

    <div style="display:flex; flex-direction:column; gap:10px;">
      <div>
        <div class="section-title" style="margin-bottom:6px;">Muscle</div>
        <div class="filter-chips">
          <button class="chip" class:active={muscleFilter === ''} on:click={() => (muscleFilter = '')}>All</button>
          {#each MUSCLES as m}
            <button class="chip" class:active={muscleFilter === m} on:click={() => (muscleFilter = m)}>{m}</button>
          {/each}
        </div>
      </div>
      <div>
        <div class="section-title" style="margin-bottom:6px;">Movement</div>
        <div class="filter-chips">
          <button class="chip" class:active={patternFilter === ''} on:click={() => (patternFilter = '')}>All</button>
          {#each PATTERNS as p}
            <button class="chip" class:active={patternFilter === p} on:click={() => (patternFilter = p)}>{p}</button>
          {/each}
        </div>
      </div>
    </div>
  </div>

  <div style="display:grid; grid-template-columns: 1fr {selectedEx ? '340px' : ''}; gap:16px; align-items:start;">
    <!-- Exercise list -->
    <div>
      {#if loading}
        <div class="flex items-center gap-3"><div class="spinner"></div></div>
      {:else}
        <div style="color:var(--text-muted); font-size:12px; margin-bottom:10px;">
          {filtered.length} exercise{filtered.length !== 1 ? 's' : ''}
        </div>
        <div style="display:flex; flex-direction:column; gap:6px;">
          {#each filtered as ex}
            <button
              on:click={() => selectExercise(ex)}
              style="width:100%; text-align:left; background:{selectedEx?.id === ex.id ? 'rgba(232,160,64,0.06)' : 'var(--surface)'}; border:1px solid {selectedEx?.id === ex.id ? 'rgba(232,160,64,0.3)' : 'var(--border)'}; border-radius:6px; padding:12px 14px; cursor:pointer; transition:all 0.15s;"
            >
              <div class="flex items-center justify-between">
                <div style="font-weight:500; font-size:14px; color:var(--text);">{ex.name}</div>
                <span class="tag {patternClass(ex.movement_pattern)}">{ex.movement_pattern}</span>
              </div>
              <div style="color:var(--text-muted); font-size:12px; margin-top:3px;">
                {ex.primary_muscles.join(', ')}
                {#if ex.secondary_muscles.length > 0}
                  · <span style="color:var(--text-faint);">{ex.secondary_muscles.slice(0,2).join(', ')}</span>
                {/if}
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Detail panel -->
    {#if selectedEx}
      <div class="card" style="position:sticky; top:0;">
        {#if loadingDetail}
          <div class="flex items-center gap-2"><div class="spinner"></div></div>
        {:else if exDetail}
          <div style="font-weight:700; font-size:16px; margin-bottom:12px;">{exDetail.name}</div>

          <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px;">
            <span class="tag tag-primary">{exDetail.mechanics}</span>
            <span class="tag {patternClass(exDetail.movement_pattern)}">{exDetail.movement_pattern}</span>
            <span class="tag">{exDetail.force}</span>
            {#if exDetail.is_bilateral}
              <span class="tag">bilateral</span>
            {:else}
              <span class="tag">unilateral</span>
            {/if}
          </div>

          <div style="margin-bottom:10px;">
            <div class="section-title">Primary Muscles</div>
            <div class="flex gap-2" style="flex-wrap:wrap;">
              {#each exDetail.primary_muscles as m}
                <span class="tag tag-primary">{m}</span>
              {/each}
            </div>
          </div>

          {#if exDetail.secondary_muscles.length > 0}
            <div style="margin-bottom:10px;">
              <div class="section-title">Secondary Muscles</div>
              <div class="flex gap-2" style="flex-wrap:wrap;">
                {#each exDetail.secondary_muscles as m}
                  <span class="tag">{m}</span>
                {/each}
              </div>
            </div>
          {/if}

          <div style="margin-bottom:10px;">
            <div class="section-title">Equipment</div>
            <div class="flex gap-2" style="flex-wrap:wrap;">
              {#each exDetail.equipment_required as e}
                <span class="tag">{e.replace('_', ' ')}</span>
              {/each}
            </div>
          </div>

          {#if exDetail.notes}
            <div style="margin-bottom:10px;">
              <div class="section-title">Notes</div>
              <p style="color:var(--text-muted); font-size:13px; line-height:1.6;">{exDetail.notes}</p>
            </div>
          {/if}

          {#if exDetail.substitutions?.length > 0}
            <div style="margin-bottom:10px;">
              <div class="section-title">Substitutions</div>
              <div style="display:flex; flex-direction:column; gap:4px;">
                {#each exDetail.substitutions as sub}
                  <button
                    on:click={() => selectExercise(sub)}
                    style="text-align:left; background:transparent; border:none; color:var(--primary); font-size:13px; cursor:pointer; padding:2px 0;"
                  >
                    → {sub.name}
                  </button>
                {/each}
              </div>
            </div>
          {/if}

          {#if exHistory.length > 0}
            <div>
              <div class="section-title">Recent History</div>
              <div style="font-size:12px; color:var(--text-muted);">
                {exHistory.length} session{exHistory.length !== 1 ? 's' : ''} logged ·
                Best est. 1RM: <span style="color:var(--primary);">
                  {Math.max(...exHistory.map(d => d.estimated_1rm)).toFixed(1)}
                </span>
              </div>
            </div>
          {/if}
        {/if}
      </div>
    {/if}
  </div>
</div>
