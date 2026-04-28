<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let programs = [];
  let loading = true;
  let installing = null;  // slug being installed
  let error = null;
  let success = null;

  onMount(async () => {
    try {
      programs = await api.programs.listLibrary();
    } catch (e) {
      error = e.message;
    }
    loading = false;
  });

  async function install(slug) {
    installing = slug;
    error = null;
    success = null;
    try {
      await api.programs.installLibraryProgram(slug);
      goto('/program');
    } catch (e) {
      error = e.message;
      installing = null;
    }
  }

  function difficultyColor(d) {
    if (d === 'beginner')     return '#50c880';
    if (d === 'intermediate') return 'var(--accent)';
    return '#e8365d';
  }

  function goalColor(g) {
    return g === 'strength' ? '#5090e8' : '#cd853f';
  }

  function daysLabel(n) {
    return `${n} day${n !== 1 ? 's' : ''}/week`;
  }

  function weeksLabel(n) {
    return `${n} weeks`;
  }
</script>

<div class="page">
  <div class="page-header">
    <h1 class="page-title">Programs Library</h1>
    <p class="page-sub">Pick a program and start training — no setup required.</p>
  </div>

  {#if error}
    <div class="banner banner-err">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">Loading…</div>
  {:else}
    <div class="cards">
      {#each programs as prog}
        <div class="card">
          <div class="card-top">
            <div class="card-name">{prog.name}</div>
            <div class="card-author">{prog.author}</div>
          </div>

          <p class="card-desc">{prog.description}</p>

          <div class="card-meta">
            <span class="badge" style="color:{goalColor(prog.goal)};border-color:{goalColor(prog.goal)}">
              {prog.goal}
            </span>
            <span class="badge" style="color:{difficultyColor(prog.difficulty)};border-color:{difficultyColor(prog.difficulty)}">
              {prog.difficulty}
            </span>
            <span class="meta-pill">{daysLabel(prog.days_per_week)}</span>
            <span class="meta-pill">{weeksLabel(prog.weeks)}</span>
          </div>

          <button
            class="start-btn"
            disabled={installing !== null}
            on:click={() => install(prog.slug)}
          >
            {#if installing === prog.slug}
              Installing…
            {:else}
              Start Program
            {/if}
          </button>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .page {
    padding: 1rem 1rem 6rem;
    max-width: 640px;
    margin: 0 auto;
  }

  .page-header {
    margin-bottom: 1.5rem;
  }

  .page-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.6rem;
    color: var(--text);
    margin: 0 0 0.25rem;
  }

  .page-sub {
    font-size: 0.85rem;
    color: var(--muted);
    margin: 0;
  }

  .loading {
    color: var(--muted);
    font-size: 0.9rem;
    padding: 2rem 0;
    text-align: center;
  }

  .banner {
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-bottom: 1rem;
  }

  .banner-err {
    background: rgba(232, 54, 93, 0.12);
    color: #e8365d;
    border: 1px solid rgba(232, 54, 93, 0.3);
  }

  .cards {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.1rem 1.1rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .card-top {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .card-name {
    font-family: 'DM Serif Display', serif;
    font-size: 1.15rem;
    color: var(--text);
    line-height: 1.2;
  }

  .card-author {
    font-size: 0.75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .card-desc {
    font-size: 0.85rem;
    color: var(--text-dim, #999);
    line-height: 1.5;
    margin: 0;
  }

  .card-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
  }

  .badge {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
    border: 1px solid currentColor;
  }

  .meta-pill {
    font-size: 0.75rem;
    color: var(--muted);
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 0.2rem 0.55rem;
  }

  .start-btn {
    margin-top: 0.25rem;
    width: 100%;
    padding: 0.75rem;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .start-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .start-btn:not(:disabled):active {
    opacity: 0.8;
  }
</style>
