<script>
  import { api } from '$lib/api.js';

  let query = '';
  let results = [];
  let loading = false;
  let searched = false;
  let searchTimer;

  function formatDate(iso) {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function onInput() {
    clearTimeout(searchTimer);
    if (!query.trim()) { results = []; searched = false; return; }
    searchTimer = setTimeout(runSearch, 400);
  }

  async function runSearch() {
    if (!query.trim()) return;
    loading = true;
    searched = true;
    try { results = await api.history.search(query); }
    catch { results = []; }
    loading = false;
  }

  function highlight(text, q) {
    if (!text || !q) return text;
    const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return text.replace(new RegExp(`(${escaped})`, 'gi'), '<mark>$1</mark>');
  }
</script>

<svelte:head><title>Search Notes — LiftForge</title></svelte:head>

<div style="max-width:640px;">
  <div class="page-title">Search <em>Notes</em></div>

  <div class="search-wrap" style="margin-bottom:20px;">
    <span class="search-icon">◎</span>
    <input
      bind:value={query}
      on:input={onInput}
      placeholder="Search session names, notes, set notes…"
      autofocus
    />
  </div>

  {#if loading}
    <div class="flex items-center gap-3" style="padding:16px 0;"><div class="spinner"></div></div>

  {:else if searched && results.length === 0}
    <div style="font-size:14px; color:var(--text-muted); padding:16px 0;">No results for "{query}"</div>

  {:else if results.length}
    <div style="font-size:11px; color:var(--text-muted); margin-bottom:12px;">{results.length} session{results.length !== 1 ? 's' : ''} matched</div>

    <div style="display:flex; flex-direction:column; gap:10px;">
      {#each results as r}
        <a href="/history" class="result-card">
          <div class="result-header">
            <span class="result-name">{@html highlight(r.session_name, query)}</span>
            <span class="result-date">{formatDate(r.started_at)}</span>
          </div>

          {#if r.session_notes && r.match_type !== 'set_notes'}
            <div class="result-snippet">{@html highlight(r.session_notes, query)}</div>
          {/if}

          {#if r.matching_set_notes.length}
            <div class="result-sets">
              {#each r.matching_set_notes as sn}
                <div class="result-set-note">
                  <span class="result-ex">{sn.exercise_name}</span>
                  <span class="result-note-text">{@html highlight(sn.note, query)}</span>
                </div>
              {/each}
            </div>
          {/if}
        </a>
      {/each}
    </div>

  {:else if !query}
    <div style="font-size:13px; color:var(--text-faint); padding:8px 0;">
      Searches across all session names, session notes, and per-set notes.
    </div>
  {/if}
</div>

<style>
  .page-title { font-family:var(--serif); font-size:26px; color:var(--text); margin-bottom:16px; line-height:1; }
  .page-title em { font-style:italic; color:var(--accent); }

  .result-card {
    display: block; text-decoration: none;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-lg); padding: 14px 16px;
    transition: border-color 0.15s;
  }
  .result-card:hover { border-color: var(--accent); }

  .result-header { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; margin-bottom: 6px; }
  .result-name { font-weight: 600; font-size: 14px; color: var(--text); flex: 1; }
  .result-date { font-size: 11px; color: var(--text-muted); white-space: nowrap; }

  .result-snippet {
    font-size: 12px; color: var(--text-muted); line-height: 1.5;
    padding: 6px 8px; background: var(--surface-2);
    border-radius: var(--radius); border-left: 2px solid var(--border);
    margin-bottom: 4px;
  }

  .result-sets { display: flex; flex-direction: column; gap: 4px; }
  .result-set-note { display: flex; gap: 8px; font-size: 12px; align-items: baseline; }
  .result-ex { color: var(--accent); font-weight: 600; white-space: nowrap; }
  .result-note-text { color: var(--text-muted); }

  :global(mark) {
    background: rgba(232,160,64,0.3);
    color: inherit;
    border-radius: 2px;
    padding: 0 1px;
  }
</style>
