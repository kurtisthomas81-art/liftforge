<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  const DOW_HEADERS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December'];

  let today = new Date();
  let viewYear = today.getFullYear();
  let viewMonth = today.getMonth() + 1;
  let calData = null;
  let loading = false;
  let selectedDay = null;

  onMount(async () => { await loadMonth(); });

  async function loadMonth() {
    loading = true;
    selectedDay = null;
    try { calData = await api.history.calendar(viewYear, viewMonth); }
    catch { calData = { sessions: [], planned: [] }; }
    loading = false;
  }

  function prevMonth() {
    if (viewMonth === 1) { viewYear--; viewMonth = 12; } else viewMonth--;
    loadMonth();
  }

  function nextMonth() {
    if (viewMonth === 12) { viewYear++; viewMonth = 1; } else viewMonth++;
    loadMonth();
  }

  function buildCalendarGrid(year, month) {
    const firstDay = new Date(year, month - 1, 1);
    let startDow = firstDay.getDay();
    startDow = startDow === 0 ? 6 : startDow - 1;
    const daysInMonth = new Date(year, month, 0).getDate();
    const cells = [];
    for (let i = 0; i < startDow; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  }

  $: cells = buildCalendarGrid(viewYear, viewMonth);

  function dateString(d) {
    if (!d) return null;
    return `${viewYear}-${String(viewMonth).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
  }

  function getSessionForDay(d) {
    if (!calData || !d) return null;
    return calData.sessions.find(s => s.date === dateString(d)) || null;
  }

  function getPlannedForDay(d) {
    if (!calData || !d) return null;
    return calData.planned.find(p => p.date === dateString(d)) || null;
  }

  function isToday(d) {
    if (!d) return false;
    return dateString(d) === today.toISOString().slice(0, 10);
  }

  function sessionDotColor(muscles) {
    if (!muscles?.length) return 'var(--accent)';
    const lower = ['quads','hamstrings','glutes','calves'];
    const hasLower = muscles.some(m => lower.includes(m));
    const hasUpper = muscles.some(m => !lower.includes(m) && m !== 'abs' && m !== 'core');
    if (hasLower && hasUpper) return 'var(--success)';
    if (hasLower) return 'var(--push)';
    if (hasUpper) return 'var(--warn)';
    return 'var(--squat)';
  }

  $: sessionsThisMonth = calData?.sessions?.length ?? 0;

  // Upcoming: next 3 planned sessions after today
  $: upcoming = (calData?.planned || [])
    .filter(p => p.date >= today.toISOString().slice(0,10))
    .sort((a,b) => a.date.localeCompare(b.date))
    .slice(0, 3);

  function selectedSessionData(d) {
    if (!d) return null;
    return getSessionForDay(d);
  }

  $: selectedData = selectedDay ? selectedSessionData(selectedDay) : null;
</script>

<svelte:head><title>Calendar — LiftForge</title></svelte:head>

<div class="cal-header">
  <div class="cal-title">Training <em>Calendar</em></div>
  <div class="cal-stats">
    <span class="cal-stat-pill">{sessionsThisMonth} sessions this month</span>
  </div>
</div>

<!-- Month nav -->
<div class="month-nav">
  <button class="nav-btn" on:click={prevMonth}>‹</button>
  <span class="month-label">{MONTH_NAMES[viewMonth - 1]} {viewYear}</span>
  <button class="nav-btn" on:click={nextMonth}>›</button>
</div>

{#if loading}
  <div class="flex items-center gap-3" style="padding:32px 0;"><div class="spinner"></div></div>
{:else}
  <!-- Day-of-week headers -->
  <div class="dow-row">
    {#each DOW_HEADERS as d}
      <div class="dow-hdr">{d}</div>
    {/each}
  </div>

  <!-- Calendar grid -->
  <div class="cal-grid">
    {#each cells as d}
      {@const session = getSessionForDay(d)}
      {@const planned = getPlannedForDay(d)}
      {@const todayCell = isToday(d)}
      {@const selected = selectedDay === d && d != null}
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <div class="cal-cell"
        class:today={todayCell}
        class:selected
        class:trained={!!session}
        class:clickable={!!(session || planned) && !!d}
        on:click={() => { if (d) selectedDay = selectedDay === d ? null : d; }}>
        <span class="cal-day-num" class:today-num={todayCell}>{d || ''}</span>
        {#if session}
          <span class="cal-dot" style="background:{sessionDotColor(session.muscles)}"></span>
        {:else if planned}
          <span class="cal-dot planned-dot"></span>
        {/if}
      </div>
    {/each}
  </div>

  <!-- Category legend -->
  <div class="legend-row">
    <span class="legend-pill"><span class="legend-dot" style="background:var(--warn)"></span>Upper</span>
    <span class="legend-pill"><span class="legend-dot" style="background:var(--push)"></span>Lower</span>
    <span class="legend-pill"><span class="legend-dot" style="background:var(--success)"></span>Full Body</span>
    <span class="legend-pill"><span class="legend-dot" style="background:var(--faint);border:1px dashed var(--bdr-2)"></span>Planned</span>
  </div>

  <!-- Selected day detail -->
  {#if selectedDay && selectedData}
    <div class="selected-card">
      <div class="selected-date">{new Date(dateString(selectedDay) + 'T00:00:00').toLocaleDateString('en-US', { weekday:'long', month:'long', day:'numeric' })}</div>
      <div class="selected-name">{selectedData.session_name}</div>
      <div class="selected-done">✓ Session logged</div>
    </div>
  {:else if selectedDay && !selectedData}
    {@const pl = getPlannedForDay(selectedDay)}
    {#if pl}
      <div class="selected-card">
        <div class="selected-date">{new Date(dateString(selectedDay) + 'T00:00:00').toLocaleDateString('en-US', { weekday:'long', month:'long', day:'numeric' })}</div>
        <div class="selected-name" style="display:flex; align-items:center; gap:6px;">
          {pl.base_session_name ?? pl.split_day_name}
          {#if pl.variant}
            <span style="display:inline-block; padding:1px 6px; border-radius:10px; background:rgba(232,160,64,0.18); color:var(--accent); font-size:10px; font-weight:700;">{pl.variant}</span>
          {/if}
        </div>
        <div class="selected-planned">Planned session</div>
      </div>
    {/if}
  {/if}

  <!-- Upcoming -->
  {#if upcoming.length > 0}
    <div class="section-title mt-4">Upcoming</div>
    {#each upcoming as p}
      <div class="upcoming-row">
        <div class="upcoming-info">
          <div class="upcoming-name" style="display:flex; align-items:center; gap:5px;">
            {p.base_session_name ?? p.split_day_name}
            {#if p.variant}
              <span style="display:inline-block; padding:1px 5px; border-radius:8px; background:rgba(232,160,64,0.18); color:var(--accent); font-size:9px; font-weight:700; line-height:1.5;">{p.variant}</span>
            {/if}
          </div>
          <div class="upcoming-date">{new Date(p.date + 'T00:00:00').toLocaleDateString('en-US', { weekday:'short', month:'short', day:'numeric' })}</div>
        </div>
        <button class="upcoming-go-btn" on:click={() => goto('/program')}>Go →</button>
      </div>
    {/each}
  {/if}
{/if}

<style>
  .cal-header { margin-bottom: 12px; }
  .cal-title { font-family: var(--serif); font-size: 26px; color: var(--text); line-height: 1; margin-bottom: 4px; }
  .cal-title em { font-style: italic; color: var(--accent); }
  .cal-stats { display: flex; gap: 8px; }
  .cal-stat-pill { font-size: 11px; color: var(--muted); }

  .month-nav {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 12px;
  }
  .nav-btn {
    background: transparent; border: 1px solid var(--bdr-2);
    border-radius: var(--radius); padding: 4px 12px;
    font-size: 18px; color: var(--muted); cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
  }
  .nav-btn:hover { color: var(--accent); border-color: var(--accent); }
  .month-label { font-family: var(--serif); font-size: 18px; color: var(--text); }

  .dow-row { display: grid; grid-template-columns: repeat(7, 1fr); margin-bottom: 4px; }
  .dow-hdr { text-align: center; font-size: 9px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; padding: 4px 0; }

  .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 12px; }
  .cal-cell {
    aspect-ratio: 1;
    border-radius: 8px;
    border: 1px solid transparent;
    display: flex; flex-direction: column; align-items: center;
    justify-content: space-between; padding: 4px 2px;
    position: relative; transition: border-color 0.15s, background 0.15s;
  }
  .cal-cell.today { border-color: var(--accent); background: var(--accent-bg); }
  .cal-cell.selected { border-color: var(--accent); background: rgba(232,54,93,0.12); }
  .cal-cell.trained { background: rgba(255,255,255,0.02); }
  .cal-cell.clickable { cursor: pointer; }
  .cal-cell.clickable:hover { border-color: var(--bdr-2); }

  .cal-day-num { font-size: 11px; color: var(--muted); line-height: 1; }
  .cal-day-num.today-num { color: var(--accent); font-weight: 700; }
  .cal-dot { width: 5px; height: 5px; border-radius: 50%; margin-bottom: 2px; }
  .planned-dot { background: var(--faint); border: 1px dashed var(--bdr-2); }

  /* Legend */
  .legend-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
  .legend-pill { display: flex; align-items: center; gap: 4px; font-size: 10px; color: var(--muted); }
  .legend-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }

  /* Selected day card */
  .selected-card {
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-radius: var(--radius-lg);
    padding: 14px 16px;
    margin-bottom: 12px;
  }
  .selected-date { font-size: 10px; color: var(--muted); margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.06em; }
  .selected-name { font-family: var(--serif); font-size: 20px; color: var(--text); margin-bottom: 4px; }
  .selected-done { font-size: 11px; color: var(--success); font-weight: 600; }
  .selected-planned { font-size: 11px; color: var(--muted); }

  /* Upcoming */
  .upcoming-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 0; border-bottom: 1px solid var(--bdr);
  }
  .upcoming-row:last-child { border-bottom: none; }
  .upcoming-name { font-family: var(--serif); font-size: 15px; color: var(--text); }
  .upcoming-date { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .upcoming-go-btn {
    background: transparent; border: 1px solid var(--bdr-2);
    border-radius: var(--radius); padding: 5px 12px;
    font-size: 11px; color: var(--muted); cursor: pointer;
    transition: all 0.15s;
  }
  .upcoming-go-btn:hover { border-color: var(--accent); color: var(--accent); }
</style>
