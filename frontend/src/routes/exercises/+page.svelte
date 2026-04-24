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

  const MUSCLES = ['chest','back','shoulders','biceps','triceps','quads','hamstrings','glutes','calves','abs'];
  const PATTERNS = ['push','pull','hinge','squat','core','isolation'];

  const CAT_COLOR = { push:'var(--push)', pull:'var(--pull)', squat:'var(--squat)', hinge:'var(--hinge)', core:'var(--core)' };

  onMount(async () => {
    exercises = await api.exercises.list();
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
    if (expandedId === ex.id) { expandedId = null; exDetail = null; exHistory = []; return; }
    expandedId = ex.id;
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
          <span class="ex-cat-badge" style="color:{catColor(ex.movement_pattern)};border-color:{catColor(ex.movement_pattern)}35;background:{catColor(ex.movement_pattern)}14">
            {ex.movement_pattern}
          </span>
          <span class="ex-expand-icon">{expandedId === ex.id ? '▲' : '▼'}</span>
        </button>

        {#if expandedId === ex.id}
          <div class="ex-detail">
            {#if loadingDetail}
              <div class="flex items-center gap-2" style="padding:8px 0;"><div class="spinner"></div></div>
            {:else if exDetail}
              <!-- PR + Last Session stats -->
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

              <!-- Notes / cue -->
              {#if exDetail.notes}
                <div class="ex-cue">{exDetail.notes}</div>
              {/if}

              <!-- Muscles -->
              <div class="ex-muscles">
                {#each exDetail.primary_muscles as m}
                  <span class="tag tag-primary">{m}</span>
                {/each}
                {#each exDetail.secondary_muscles as m}
                  <span class="tag">{m}</span>
                {/each}
              </div>

              <!-- Add to workout button -->
              <a href="/log" class="add-to-workout-btn">+ Add to Workout</a>
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
</style>
