<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { refreshImportQueueCount } from '$lib/stores.js';

  let items = [];
  let loading = true;

  // Per-item UI state
  let expandedId = null;       // which item has the search panel open
  let searchQuery = {};        // { [id]: string }
  let searchResults = {};      // { [id]: Exercise[] }
  let searching = {};          // { [id]: bool }
  let resolving = {};          // { [id]: bool }
  let searchDebounce = {};

  onMount(async () => {
    await load();
  });

  async function load() {
    loading = true;
    try {
      const d = await api.importQueue.list();
      items = d.items;
    } finally {
      loading = false;
    }
  }

  function toggleExpand(id) {
    if (expandedId === id) {
      expandedId = null;
    } else {
      expandedId = id;
      if (!searchQuery[id]) searchQuery[id] = '';
      searchResults[id] = [];
    }
  }

  function onSearchInput(id) {
    clearTimeout(searchDebounce[id]);
    searchDebounce[id] = setTimeout(() => doSearch(id), 250);
  }

  async function doSearch(id) {
    const q = (searchQuery[id] || '').trim();
    if (!q) { searchResults[id] = []; return; }
    searching[id] = true;
    try {
      const res = await api.exercises.list({ search: q, limit: 8 });
      searchResults[id] = res;
    } catch {
      searchResults[id] = [];
    }
    searching = { ...searching };
  }

  async function matchTo(item, exerciseId) {
    resolving[item.id] = true;
    try {
      await api.importQueue.resolve(item.id, { exercise_id: exerciseId });
      items = items.filter(i => i.id !== item.id);
      await refreshImportQueueCount();
    } catch (e) {
      alert(e.message || 'Failed to resolve');
    }
    resolving = { ...resolving };
  }

  async function createNew(item) {
    resolving[item.id] = true;
    try {
      await api.importQueue.resolve(item.id, { create: true });
      items = items.filter(i => i.id !== item.id);
      await refreshImportQueueCount();
    } catch (e) {
      alert(e.message || 'Failed to create');
    }
    resolving = { ...resolving };
  }

  async function dismiss(item) {
    if (!confirm(`Dismiss "${item.raw_name}"? Its ${item.set_count} sets will not be imported.`)) return;
    resolving[item.id] = true;
    try {
      await api.importQueue.dismiss(item.id);
      items = items.filter(i => i.id !== item.id);
      await refreshImportQueueCount();
    } catch (e) {
      alert(e.message || 'Failed to dismiss');
    }
    resolving = { ...resolving };
  }
</script>

<div class="page">
  <div class="page-header">
    <h1 class="page-title">Import Queue</h1>
    {#if !loading}
      <p class="page-sub">
        {#if items.length > 0}
          {items.length} unrecognized exercise{items.length > 1 ? 's' : ''} from Liftosaur — match each to an existing exercise or add it as new.
        {:else}
          All clear — nothing waiting for review.
        {/if}
      </p>
    {/if}
  </div>

  {#if loading}
    <div class="empty-state">Loading…</div>
  {:else if items.length === 0}
    <div class="empty-state">
      <div class="empty-icon">✓</div>
      <div class="empty-label">Queue is empty</div>
      <div class="empty-sub">All imported exercises have been resolved.</div>
    </div>
  {:else}
    <div class="queue-list">
      {#each items as item (item.id)}
        {@const busy = resolving[item.id]}
        {@const isOpen = expandedId === item.id}

        <div class="queue-card" class:expanded={isOpen}>
          <div class="card-main">
            <div class="card-left">
              <div class="raw-name">"{item.raw_name}"</div>
              <div class="card-meta">{item.set_count} sets · {item.source}</div>
            </div>
            <div class="card-actions">
              <button class="btn-match" on:click={() => toggleExpand(item.id)} disabled={busy}>
                {isOpen ? 'Cancel' : 'Match'}
              </button>
              <button class="btn-create" on:click={() => createNew(item)} disabled={busy}>
                {busy && !isOpen ? '…' : 'Add as new'}
              </button>
              <button class="btn-dismiss" on:click={() => dismiss(item)} disabled={busy} title="Dismiss — skip these sets">✕</button>
            </div>
          </div>

          {#if isOpen}
            <div class="search-panel">
              <div class="search-hint">Search your exercise library to find the match:</div>
              <input
                class="search-input"
                type="text"
                placeholder="e.g. Barbell Bench Press…"
                bind:value={searchQuery[item.id]}
                on:input={() => onSearchInput(item.id)}
                autofocus
              />
              {#if searching[item.id]}
                <div class="search-status">Searching…</div>
              {:else if searchResults[item.id]?.length > 0}
                <div class="results-list">
                  {#each searchResults[item.id] as ex}
                    <button class="result-row" on:click={() => matchTo(item, ex.id)} disabled={busy}>
                      <div class="result-name">{ex.name}</div>
                      <div class="result-meta">{ex.primary_muscles?.[0] ?? ''}{ex.mechanics ? ' · ' + ex.mechanics : ''}</div>
                    </button>
                  {/each}
                </div>
              {:else if (searchQuery[item.id] || '').trim().length > 0}
                <div class="search-status">No matches found.</div>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .page { padding: 20px 16px 80px; max-width: 640px; margin: 0 auto; }
  .page-header { margin-bottom: 24px; }
  .page-title { font-family: var(--serif); font-size: 26px; margin: 0 0 6px; }
  .page-sub { font-size: 13px; color: var(--muted); margin: 0; line-height: 1.5; }

  .empty-state {
    display: flex; flex-direction: column; align-items: center;
    padding: 60px 20px; gap: 8px; text-align: center; color: var(--muted);
  }
  .empty-icon { font-size: 36px; color: var(--success); }
  .empty-label { font-family: var(--serif); font-size: 20px; color: var(--text); }
  .empty-sub { font-size: 13px; }

  .queue-list { display: flex; flex-direction: column; gap: 12px; }

  .queue-card {
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    background: var(--surf);
    transition: border-color 0.15s;
  }
  .queue-card.expanded { border-color: var(--accent); }

  .card-main {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 16px; gap: 12px;
  }
  .raw-name {
    font-family: var(--serif); font-size: 16px;
    color: var(--text); word-break: break-word;
  }
  .card-meta { font-size: 12px; color: var(--muted); margin-top: 2px; }

  .card-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

  .btn-match {
    padding: 7px 14px; border-radius: 8px;
    background: var(--accent); color: #fff; border: none;
    font-size: 13px; font-weight: 600; cursor: pointer;
    transition: background 0.15s;
  }
  .btn-match:hover:not(:disabled) { background: #e07030; }

  .btn-create {
    padding: 7px 14px; border-radius: 8px;
    background: transparent; color: var(--text);
    border: 1px solid var(--border);
    font-size: 13px; cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }
  .btn-create:hover:not(:disabled) { border-color: var(--text); }

  .btn-dismiss {
    padding: 7px 10px; border-radius: 8px;
    background: transparent; color: var(--muted);
    border: 1px solid transparent;
    font-size: 14px; cursor: pointer;
    transition: color 0.15s;
  }
  .btn-dismiss:hover:not(:disabled) { color: var(--accent); }

  button:disabled { opacity: 0.5; cursor: not-allowed; }

  .search-panel {
    border-top: 1px solid var(--border);
    padding: 14px 16px;
    background: var(--surface-2, rgba(255,255,255,0.03));
  }
  .search-hint { font-size: 12px; color: var(--muted); margin-bottom: 10px; }
  .search-input {
    width: 100%; box-sizing: border-box;
    background: var(--input-bg, rgba(255,255,255,0.06));
    border: 1px solid var(--border); border-radius: 8px;
    color: var(--text); font-size: 14px;
    padding: 10px 12px; outline: none;
  }
  .search-input:focus { border-color: var(--accent); }

  .search-status { font-size: 12px; color: var(--muted); margin-top: 10px; }

  .results-list { display: flex; flex-direction: column; gap: 4px; margin-top: 10px; }
  .result-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 12px; border-radius: 8px;
    background: transparent; border: 1px solid var(--border);
    cursor: pointer; text-align: left; width: 100%;
    transition: background 0.12s, border-color 0.12s;
  }
  .result-row:hover:not(:disabled) {
    background: rgba(205,133,63,0.1); border-color: var(--accent);
  }
  .result-name { font-size: 14px; color: var(--text); }
  .result-meta { font-size: 12px; color: var(--muted); text-transform: capitalize; }
</style>
