<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import '../app.css';
  import { activeSession, refreshActiveSession, refreshProfile, getElapsed } from '$lib/stores.js';

  let elapsed = '0:00';
  let intervalId;
  let showMore = false;

  onMount(async () => {
    await Promise.all([refreshActiveSession(), refreshProfile()]);

    intervalId = setInterval(() => {
      if ($activeSession) {
        elapsed = getElapsed($activeSession.started_at);
      }
    }, 1000);

    return () => clearInterval(intervalId);
  });

  $: currentPath = $page.url.pathname;

  const tabs = [
    { href: '/',        label: 'Home',    icon: '◈' },
    { href: '/log',     label: 'Log',     icon: '✦' },
    { href: '/program', label: 'Program', icon: '▦' },
    { href: '/history', label: 'History', icon: '◎' },
  ];

  const moreSections = [
    {
      label: 'Training',
      items: [
        { href: '/templates',    label: 'Templates',       icon: '◫', desc: 'Saved workouts' },
        { href: '/1rm-test',     label: '1RM Test',        icon: '⊗', desc: 'Guided max strength test' },
        { href: '/plates',       label: 'Plates',          icon: '⊙', desc: 'Plate calculator' },
      ]
    },
    {
      label: 'Analytics',
      items: [
        { href: '/progress',     label: 'Progress',        icon: '◑', desc: '1RM charts & trends' },
        { href: '/calendar',     label: 'Calendar',        icon: '▣', desc: 'Monthly training view' },
        { href: '/recovery',     label: 'Recovery',        icon: '◉', desc: 'Muscle recovery map' },
        { href: '/measurements', label: 'Measurements',    icon: '↕', desc: 'Body stats & trends' },
      ]
    },
    {
      label: 'Library',
      items: [
        { href: '/exercises',        label: 'Exercises',        icon: '⊞', desc: 'Exercise browser' },
        { href: '/programs-library', label: 'Browse Programs',  icon: '◧', desc: 'Pre-built programs to run' },
      ]
    },
    {
      label: 'App',
      items: [
        { href: '/chat',   label: 'AI Coach', icon: '◇', desc: 'Ollama coaching' },
        { href: '/search', label: 'Search',   icon: '⊕', desc: 'Search training notes' },
      ]
    },
  ];

  const allMoreItems = moreSections.flatMap(s => s.items);

  function isTabActive(href) {
    if (href === '/') return currentPath === '/';
    return currentPath.startsWith(href);
  }

  $: isMoreActive = allMoreItems.some(m => currentPath.startsWith(m.href));

  function handleMoreNav(href) {
    showMore = false;
    goto(href);
  }
</script>

<div class="page-wrap">
  <header class="app-header">
    <span class="app-header-title">LiftForge</span>
    <a href="/settings" class="settings-btn" class:active={currentPath === '/settings'} title="Settings">⚙</a>
  </header>
  <main class="main-content">
    {#if $activeSession && currentPath !== '/log'}
      <a href="/log" class="active-session-bar">
        <span class="asb-dot"></span>
        <span class="asb-label">Session active — {elapsed} elapsed</span>
        <span class="asb-cta">Resume →</span>
      </a>
    {/if}
    <slot />
  </main>

  <!-- Bottom tab bar -->
  <nav class="bottom-nav">
    {#each tabs as tab}
      <a href={tab.href} class="tab-btn" class:active={isTabActive(tab.href)}>
        <span class="tab-icon">{tab.icon}</span>
        {tab.label}
      </a>
    {/each}
    <button class="tab-btn" class:active={isMoreActive || showMore} on:click={() => showMore = true}>
      <span class="tab-icon">≡</span>
      More
    </button>
  </nav>
</div>

<!-- More sheet -->
{#if showMore}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="more-overlay" on:click|self={() => showMore = false}>
    <div class="more-sheet">
      <div class="more-sheet-handle"></div>
      <div class="more-sheet-title">More</div>
      {#each moreSections as section}
        <div class="more-section-label">{section.label}</div>
        <div class="more-grid">
          {#each section.items as item}
            <button class="more-card" on:click={() => handleMoreNav(item.href)}>
              <div class="more-card-icon">{item.icon}</div>
              <div class="more-card-text">
                <div class="more-card-label">{item.label}</div>
                <div class="more-card-desc">{item.desc}</div>
              </div>
            </button>
          {/each}
        </div>
      {/each}
    </div>
  </div>
{/if}

<style>
  .app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px 6px;
    background: var(--surface, #111);
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }
  .app-header-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--muted);
    text-transform: uppercase;
  }
  .settings-btn {
    font-size: 18px;
    color: var(--muted);
    text-decoration: none;
    padding: 4px 6px;
    border-radius: 6px;
    transition: color 0.15s, background 0.15s;
  }
  .settings-btn:hover, .settings-btn.active {
    color: var(--text);
    background: rgba(255,255,255,0.07);
  }
  .more-section-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    padding: 12px 0 6px;
  }
  .more-section-label:first-of-type {
    padding-top: 4px;
  }
  .active-session-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--accent-bg);
    border: 1px solid rgba(232,54,93,0.2);
    border-radius: var(--radius);
    padding: 8px 12px;
    margin-bottom: 16px;
    font-size: 12px;
    color: var(--text);
    text-decoration: none;
  }
  .asb-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent);
    flex-shrink: 0;
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .asb-label { flex: 1; color: var(--muted); font-size: 11px; }
  .asb-cta { font-size: 11px; color: var(--accent); font-weight: 600; }
</style>
