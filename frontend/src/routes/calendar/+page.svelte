<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  const DOW_HEADERS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  let today = new Date();
  let viewYear = today.getFullYear();
  let viewMonth = today.getMonth() + 1; // 1-indexed

  let calData = null;
  let loading = false;

  onMount(async () => {
    await loadMonth();
  });

  async function loadMonth() {
    loading = true;
    try {
      calData = await api.history.calendar(viewYear, viewMonth);
    } catch (e) {
      calData = { sessions: [], planned: [] };
    }
    loading = false;
  }

  function prevMonth() {
    if (viewMonth === 1) { viewYear--; viewMonth = 12; }
    else viewMonth--;
    loadMonth();
  }

  function nextMonth() {
    if (viewMonth === 12) { viewYear++; viewMonth = 1; }
    else viewMonth++;
    loadMonth();
  }

  const MONTH_NAMES = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December'
  ];

  function buildCalendarGrid(year, month) {
    const firstDay = new Date(year, month - 1, 1);
    // 0=Sun..6=Sat → convert to Mon=0..Sun=6
    let startDow = firstDay.getDay();
    startDow = startDow === 0 ? 6 : startDow - 1;

    const daysInMonth = new Date(year, month, 0).getDate();
    const cells = [];

    // Leading blanks
    for (let i = 0; i < startDow; i++) cells.push(null);

    for (let d = 1; d <= daysInMonth; d++) {
      cells.push(d);
    }

    // Trailing blanks to fill last row
    while (cells.length % 7 !== 0) cells.push(null);

    return cells;
  }

  $: cells = buildCalendarGrid(viewYear, viewMonth);

  function dateString(d) {
    if (!d) return null;
    const mm = String(viewMonth).padStart(2, '0');
    const dd = String(d).padStart(2, '0');
    return `${viewYear}-${mm}-${dd}`;
  }

  function getSessionForDay(d) {
    if (!calData || !d) return null;
    const ds = dateString(d);
    return calData.sessions.find(s => s.date === ds) || null;
  }

  function getPlannedForDay(d) {
    if (!calData || !d) return null;
    const ds = dateString(d);
    return calData.planned.find(p => p.date === ds) || null;
  }

  function isToday(d) {
    if (!d) return false;
    return dateString(d) === today.toISOString().slice(0, 10);
  }

  function sessionDotColor(muscles) {
    if (!muscles || muscles.length === 0) return 'var(--primary)';
    const lower = ['quads','hamstrings','glutes','calves'];
    const upper = ['chest','shoulders','triceps','back','biceps'];
    const hasLower = muscles.some(m => lower.includes(m));
    const hasUpper = muscles.some(m => upper.includes(m));
    if (hasLower && hasUpper) return '#4caf6a';
    if (hasLower) return '#4a90d9';
    if (hasUpper) return '#e8a040';
    return '#9b59b6';
  }

  // Stats for the month
  $: sessionsThisMonth = calData?.sessions?.length || 0;
  $: daysInCurrentMonth = new Date(viewYear, viewMonth, 0).getDate();
  $: restDays = daysInCurrentMonth - sessionsThisMonth;

  $: {
    // Streak: count consecutive days with sessions going back from today
    // (only relevant when viewing current month)
  }
</script>

<svelte:head><title>Calendar — LiftForge</title></svelte:head>

<div style="max-width:800px;">
  <!-- Header -->
  <div class="flex items-center justify-between mb-4">
    <h2 style="font-size:20px; font-weight:700;">Training Calendar</h2>
    <div class="flex items-center gap-3">
      <button class="btn-ghost btn-sm" on:click={prevMonth}>&#8249; Prev</button>
      <span style="font-size:15px; font-weight:600; min-width:150px; text-align:center;">
        {MONTH_NAMES[viewMonth - 1]} {viewYear}
      </span>
      <button class="btn-ghost btn-sm" on:click={nextMonth}>Next &#8250;</button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center gap-3" style="padding:48px 0;">
      <div class="spinner"></div>
      <span style="color:var(--text-muted);">Loading...</span>
    </div>
  {:else}
    <!-- Calendar grid -->
    <div class="card" style="padding:0; overflow:hidden;">
      <!-- Day-of-week headers -->
      <div style="display:grid; grid-template-columns:repeat(7, 1fr); border-bottom:1px solid var(--border);">
        {#each DOW_HEADERS as dow}
          <div style="padding:8px 0; text-align:center; font-size:11px; font-weight:600; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.06em;">
            {dow}
          </div>
        {/each}
      </div>

      <!-- Cells -->
      <div style="display:grid; grid-template-columns:repeat(7, 1fr);">
        {#each cells as d, i}
          {@const session = getSessionForDay(d)}
          {@const planned = getPlannedForDay(d)}
          {@const todayCell = isToday(d)}
          {@const isFuture = d && new Date(dateString(d)) > today}
          <div
            style="
              min-height:72px;
              padding:6px;
              border-right:{((i + 1) % 7 === 0) ? 'none' : '1px solid var(--border)'};
              border-bottom:1px solid var(--border);
              background:{session ? 'rgba(232,160,64,0.04)' : 'transparent'};
              cursor:{session ? 'pointer' : planned ? 'pointer' : 'default'};
              position:relative;
            "
            on:click={() => {
              if (session) goto('/history');
              else if (planned) goto(`/program`);
            }}
            on:keydown={e => e.key === 'Enter' && (session ? goto('/history') : planned ? goto('/program') : null)}
            role={session || planned ? 'button' : 'presentation'}
            tabindex={session || planned ? 0 : -1}
          >
            <!-- Day number -->
            <div style="
              font-size:12px;
              font-weight:{todayCell ? '700' : '400'};
              color:{todayCell ? 'var(--primary)' : d ? 'var(--text-muted)' : 'transparent'};
              {todayCell ? 'background:rgba(232,160,64,0.15); border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center;' : ''}
            ">{d || ''}</div>

            <!-- Session chip -->
            {#if session}
              <div style="
                margin-top:4px;
                background:{sessionDotColor(session.muscles)};
                border-radius:3px;
                padding:2px 5px;
                font-size:10px;
                font-weight:600;
                color:#000;
                white-space:nowrap;
                overflow:hidden;
                text-overflow:ellipsis;
                max-width:100%;
              " title="{session.session_name}: {session.muscles.join(', ')}">
                {session.session_name.length > 12 ? session.session_name.slice(0, 11) + '…' : session.session_name}
              </div>

            <!-- Planned chip -->
            {:else if planned && isFuture}
              <div style="
                margin-top:4px;
                border:1px dashed var(--border-2);
                border-radius:3px;
                padding:2px 5px;
                font-size:10px;
                color:var(--text-faint);
                white-space:nowrap;
                overflow:hidden;
                text-overflow:ellipsis;
                max-width:100%;
              " title="{planned.split_day_name}">
                {planned.split_day_name.length > 12 ? planned.split_day_name.slice(0, 11) + '…' : planned.split_day_name}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    </div>

    <!-- Month stats -->
    <div class="flex gap-3 mt-4">
      <div class="card" style="flex:1; text-align:center; padding:12px;">
        <div style="font-size:24px; font-weight:700; color:var(--primary);">{sessionsThisMonth}</div>
        <div style="color:var(--text-muted); font-size:12px; margin-top:2px;">Sessions</div>
      </div>
      <div class="card" style="flex:1; text-align:center; padding:12px;">
        <div style="font-size:24px; font-weight:700; color:var(--text-muted);">{calData?.planned?.length || 0}</div>
        <div style="color:var(--text-muted); font-size:12px; margin-top:2px;">Planned Remaining</div>
      </div>
      <div class="card" style="flex:1; text-align:center; padding:12px; display:flex; flex-direction:column; align-items:center; gap:4px;">
        <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; justify-content:center;">
          <span style="font-size:10px; color:var(--text-muted);">Upper</span>
          <div style="width:10px; height:10px; border-radius:2px; background:#e8a040;"></div>
          <span style="font-size:10px; color:var(--text-muted);">Lower</span>
          <div style="width:10px; height:10px; border-radius:2px; background:#4a90d9;"></div>
          <span style="font-size:10px; color:var(--text-muted);">Full</span>
          <div style="width:10px; height:10px; border-radius:2px; background:#4caf6a;"></div>
          <span style="font-size:10px; color:var(--text-muted);">Other</span>
          <div style="width:10px; height:10px; border-radius:2px; background:#9b59b6;"></div>
        </div>
        <div style="color:var(--text-faint); font-size:11px;">Color Key</div>
      </div>
    </div>
  {/if}
</div>
