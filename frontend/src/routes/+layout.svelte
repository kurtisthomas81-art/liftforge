<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import '../app.css';
  import { activeSession, refreshActiveSession, refreshProfile, getElapsed, importQueueCount, refreshImportQueueCount } from '$lib/stores.js';
  import HexMark from '$lib/HexMark.svelte';

  let elapsed = '0:00';
  let intervalId;
  let showMore = false;

  // Swipe-to-close state
  let touchStartY = 0;
  let dragY = 0;
  let isDragging = false;
  let sheetEl;

  onMount(async () => {
    await Promise.all([refreshActiveSession(), refreshProfile(), refreshImportQueueCount()]);

    intervalId = setInterval(() => {
      if ($activeSession) {
        elapsed = getElapsed($activeSession.started_at);
      }
    }, 1000);

    return () => clearInterval(intervalId);
  });

  $: currentPath = $page.url.pathname;

  const rootPaths = new Set(['/', '/log', '/program', '/history']);
  $: canGoBack = !rootPaths.has(currentPath);

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

  $: isMoreActive = allMoreItems.some(m => currentPath.startsWith(m.href));

  function handleMoreNav(href) {
    showMore = false;
    goto(href);
  }

  $: if (!showMore) dragY = 0;

  function onSheetTouchStart(e) {
    touchStartY = e.touches[0].clientY;
    isDragging = true;
  }
  function onSheetTouchMove(e) {
    const delta = e.touches[0].clientY - touchStartY;
    if (delta > 0 && (!sheetEl || sheetEl.scrollTop === 0)) {
      e.preventDefault();
      dragY = Math.max(0, delta);
    }
  }
  function onSheetTouchEnd() {
    if (dragY > 80) showMore = false;
    dragY = 0;
    isDragging = false;
  }
</script>

<!-- Desktop sidebar (hidden on mobile via CSS) -->
<aside class="sidebar">
  <a href="/" class="sidebar-logo">
    <HexMark size={28} sceneOpacity={0.52}/>
    <div class="sidebar-wordmark-text">
      <span class="sidebar-wordmark-lift">LIFT</span><span class="sidebar-wordmark-forge">Forge</span>
    </div>
  </a>
  <nav class="sidebar-nav">
    {#each tabs as tab}
      <a href={tab.href} class="sidebar-nav-item"
         class:active={tab.href === '/' ? currentPath === '/' : currentPath.startsWith(tab.href)}>
        <span class="sidebar-nav-icon">{tab.icon}</span>
        {tab.label}
      </a>
    {/each}
    <div class="sidebar-divider"></div>
    {#each moreSections as section}
      <div class="sidebar-section-label">{section.label}</div>
      {#each section.items as item}
        <a href={item.href} class="sidebar-nav-item" class:active={currentPath.startsWith(item.href)}>
          <span class="sidebar-nav-icon">{item.icon}</span>
          {item.label}
        </a>
      {/each}
    {/each}
  </nav>
  <div class="sidebar-settings">
    <a href="/settings" class="sidebar-nav-item" class:active={currentPath === '/settings'}>
      <span class="sidebar-nav-icon">⚙</span>
      Settings
      {#if $importQueueCount > 0}<span class="queue-badge">{$importQueueCount}</span>{/if}
    </a>
  </div>
</aside>

<div class="page-wrap">
  <header class="app-header">
    {#if canGoBack}
      <button class="back-btn" on:click={() => history.back()}>←</button>
    {:else}
      <a href="/" class="wordmark">
        <HexMark size={30} sceneOpacity={0.52}/>
        <div class="wordmark-text">
          <span class="wordmark-lift">LIFT</span><span class="wordmark-forge">Forge</span>
        </div>
      </a>
    {/if}
    <a href="/settings" class="settings-btn" class:active={currentPath === '/settings'} title="Settings">
      ⚙{#if $importQueueCount > 0}<span class="queue-badge">{$importQueueCount}</span>{/if}
    </a>
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
      <a href={tab.href} class="tab-btn"
         class:active={tab.href === '/' ? currentPath === '/' : currentPath.startsWith(tab.href)}>
        <span class="tab-icon">{tab.icon}</span>
        {tab.label}
      </a>
    {/each}
    <button class="tab-btn" class:active={isMoreActive || showMore} on:click={() => (showMore = true)}>
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
    <div
      class="more-sheet"
      bind:this={sheetEl}
      style="transform: translateY({dragY}px); transition: {isDragging ? 'none' : 'transform 0.25s ease'};"
      on:touchstart={onSheetTouchStart}
      on:touchmove={onSheetTouchMove}
      on:touchend={onSheetTouchEnd}
    >
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
  .wordmark {
    display: flex;
    align-items: center;
    gap: 9px;
    text-decoration: none;
  }
  .wordmark-text {
    line-height: 1;
  }
  .wordmark-lift {
    font-family: 'DM Sans', sans-serif;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text, #f8f8ff);
  }
  .wordmark-forge {
    font-family: 'DM Serif Display', serif;
    font-style: italic;
    font-size: 13px;
    letter-spacing: 0.04em;
    color: var(--accent, #e8365d);
    margin-left: 1px;
  }
  .settings-btn {
    font-size: 18px;
    color: var(--muted);
    text-decoration: none;
    padding: 4px 6px;
    border-radius: 6px;
    transition: color 0.15s, background 0.15s;
    position: relative;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .settings-btn:hover, .settings-btn.active {
    color: var(--text);
    background: rgba(255,255,255,0.07);
  }
  .queue-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 16px;
    height: 16px;
    padding: 0 4px;
    border-radius: 8px;
    background: var(--accent);
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    line-height: 1;
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
