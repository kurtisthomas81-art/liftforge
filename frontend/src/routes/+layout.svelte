<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import '../app.css';
  import { activeSession, refreshActiveSession, refreshProfile, getElapsed } from '$lib/stores.js';

  let elapsed = '0:00';
  let intervalId;

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

  const navLinks = [
    { href: '/',           label: 'Dashboard',  icon: '◈' },
    { href: '/program',    label: 'Program',    icon: '▦' },
    { href: '/log',        label: 'Log Workout', icon: '✦' },
    { href: '/history',    label: 'History',     icon: '◎' },
    { href: '/exercises',  label: 'Exercises',   icon: '⊞' },
    { href: '/chat',       label: 'AI Coach',    icon: '◇' },
    { href: '/settings',   label: 'Settings',    icon: '⚙' },
  ];

  function isActive(href) {
    if (href === '/') return currentPath === '/';
    return currentPath.startsWith(href);
  }
</script>

<div class="page-wrap">
  <!-- Sidebar (desktop) -->
  <aside class="sidebar">
    <div class="sidebar-logo">
      <h1>LiftForge</h1>
      <span>Self-hosted tracker</span>
    </div>

    <nav class="sidebar-nav">
      {#each navLinks as link}
        <a href={link.href} class:active={isActive(link.href)}>
          <span class="nav-icon">{link.icon}</span>
          {link.label}
        </a>
      {/each}
    </nav>

    {#if $activeSession}
      <a href="/log" class="active-session-badge">
        <strong>Session Active</strong>
        {elapsed} elapsed
      </a>
    {/if}
  </aside>

  <!-- Main content -->
  <main class="main-content">
    <slot />
  </main>

  <!-- Bottom nav (mobile) -->
  <nav class="bottom-nav">
    {#each navLinks as link}
      <a href={link.href} class:active={isActive(link.href)}>
        <span class="nav-icon">{link.icon}</span>
        {link.label.split(' ')[0]}
      </a>
    {/each}
  </nav>
</div>
