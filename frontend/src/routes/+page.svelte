<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { activeSession, refreshActiveSession, userProfile, getElapsed, sessionPlan } from '$lib/stores.js';
  import { autoSessionName } from '$lib/utils.js';

  let recentSessions = [];
  let loading = true;
  let elapsed = '0:00';
  let elapsedInterval;
  let creating = false;
  let fatigueReport = null;
  let nextPlanned = null;
  let weekDays = [];

  // Weekly check-in
  let checkinDue = false;
  let checkinDismissed = false;
  let checkinData = { energy: 3, sleep_quality: 3, stress: 3, soreness: 3, notes: '', body_weight: null };
  let submittingCheckin = false;
  let checkinDone = false;

  // Generate session
  let generating = false;

  function buildWeekDays(sessions) {
    const now = new Date();
    const dayOffset = (now.getDay() + 6) % 7; // 0=Mon
    const monday = new Date(now);
    monday.setDate(now.getDate() - dayOffset);
    monday.setHours(0, 0, 0, 0);

    return ['M','T','W','T','F','S','S'].map((label, i) => {
      const start = new Date(monday);
      start.setDate(monday.getDate() + i);
      const end = new Date(start);
      end.setHours(23, 59, 59, 999);
      const daySessions = sessions.filter(s => {
        if (!s.completed_at) return false;
        const d = new Date(s.started_at);
        return d >= start && d <= end;
      });
      return { label, sets: daySessions.reduce((a, s) => a + (s.set_count || 0), 0), trained: daySessions.length > 0 };
    });
  }

  onMount(async () => {
    await refreshActiveSession();

    elapsedInterval = setInterval(() => {
      if ($activeSession) elapsed = getElapsed($activeSession.started_at);
    }, 1000);

    try {
      const sessions = await api.history.recent();
      recentSessions = sessions.slice(0, 5);
      weekDays = buildWeekDays(sessions);

      try {
        const meso = await api.programs.getActiveMesocycle();
        if (meso?.current_week_sessions) {
          nextPlanned = meso.current_week_sessions.find(s => !s.session_id) || null;
        }
      } catch { /* no active program */ }

      try {
        fatigueReport = await api.volume.fatigueReport();
      } catch { /* graceful */ }

      try {
        const cs = await api.recovery.checkinStatus();
        checkinDue = cs.due;
      } catch { /* graceful */ }
    } catch (e) {
      console.error(e);
    }
    loading = false;

    return () => clearInterval(elapsedInterval);
  });

  $: weekSessions = weekDays.filter(d => d.trained).length;
  $: weekSets = weekDays.reduce((a, d) => a + d.sets, 0);
  $: maxWeekSets = Math.max(...weekDays.map(d => d.sets), 1);

  $: fatigueScore = fatigueReport?.fatigue_score ?? 0;
  $: fatigueColor = fatigueScore >= 8 ? 'var(--danger)' : fatigueScore >= 5 ? 'var(--warn)' : 'var(--success)';
  $: ringCirc = 2 * Math.PI * 22;
  $: ringOffset = ringCirc * (1 - fatigueScore / 10);

  function greeting() {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning,';
    if (h < 17) return 'Good afternoon,';
    return 'Good evening,';
  }

  function todayLabel() {
    return new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  }

  function sessionDuration(s) {
    if (!s.started_at || !s.completed_at) return '';
    const mins = Math.round((new Date(s.completed_at) - new Date(s.started_at)) / 60000);
    if (mins < 1) return '';
    return mins >= 60 ? `${Math.floor(mins/60)}h ${mins%60}m` : `${mins}m`;
  }

  function sessionDateStr(s) {
    if (!s.started_at) return '';
    return new Date(s.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  async function beginSession() {
    creating = true;
    try {
      await api.sessions.create({ name: autoSessionName() });
      await refreshActiveSession();
      goto('/log');
    } catch (e) { console.error(e); }
    creating = false;
  }

  async function submitCheckin() {
    submittingCheckin = true;
    try {
      await api.recovery.submitCheckin(checkinData);
      checkinDone = true;
    } catch (e) { console.error(e); }
    submittingCheckin = false;
  }

  async function generateSession() {
    generating = true;
    try {
      const plan = await api.sessions.generate();
      sessionPlan.set(plan);
      await refreshActiveSession();
      goto('/log');
    } catch (e) { console.error(e); }
    generating = false;
  }
</script>

<svelte:head><title>LiftForge</title></svelte:head>

<div class="home">
  <!-- Header -->
  <div class="hdr">
    <div class="hdr-left">
      <div class="brand-label">LiftForge</div>
      <div class="greeting">
        {greeting()}<br/>
        <em>{$userProfile?.name?.split(' ')[0] ?? 'Athlete'}.</em>
      </div>
    </div>
    <div class="hdr-right">
      <div class="fatigue-label">Fatigue</div>
      <svg width="58" height="58" class="fatigue-ring">
        <circle cx="29" cy="29" r="22" fill="none" stroke="var(--faint)" stroke-width="4"/>
        <circle cx="29" cy="29" r="22" fill="none"
          stroke={fatigueColor} stroke-width="4"
          stroke-dasharray={ringCirc}
          stroke-dashoffset={ringOffset}
          stroke-linecap="round"
          style="transform-origin:29px 29px;transform:rotate(-90deg);transition:stroke-dashoffset 0.6s ease"/>
        <text x="29" y="34" text-anchor="middle" fill={fatigueColor}
          font-size="13" font-family="var(--sans)" font-weight="700">{fatigueScore}</text>
      </svg>
    </div>
  </div>
  <div class="date-line">{todayLabel()}</div>

  <!-- Weekly check-in card -->
  {#if checkinDue && !checkinDismissed && !checkinDone}
    <div class="checkin-card">
      <div class="checkin-hdr">
        <div>
          <div class="checkin-title">Weekly Check-in</div>
          <div class="checkin-sub">How are you feeling this week?</div>
        </div>
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <span class="checkin-skip" on:click={() => checkinDismissed = true}>Skip</span>
      </div>
      {#each [
        { key: 'energy', label: 'Energy' },
        { key: 'sleep_quality', label: 'Sleep' },
        { key: 'stress', label: 'Stress' },
        { key: 'soreness', label: 'Soreness' },
      ] as row}
        <div class="checkin-row">
          <div class="checkin-lbl">{row.label}</div>
          <div class="checkin-dots">
            {#each [1,2,3,4,5] as n}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <span class="dot" class:filled={checkinData[row.key] >= n}
                on:click={() => checkinData[row.key] = n}></span>
            {/each}
          </div>
        </div>
      {/each}
      <div class="checkin-row" style="margin-top:4px;">
        <div class="checkin-lbl">Body Weight <span style="font-size:10px; color:var(--muted);">({$userProfile?.unit_preference ?? 'lbs'}) optional</span></div>
        <input
          type="number"
          min="50" max="500" step="0.1"
          bind:value={checkinData.body_weight}
          placeholder="—"
          style="width:72px; text-align:right; font-size:13px; padding:4px 8px;"
        />
      </div>
      <button class="btn-primary checkin-submit" on:click={submitCheckin} disabled={submittingCheckin}>
        {submittingCheckin ? 'Saving…' : 'Submit'}
      </button>
    </div>
  {/if}

  <!-- Stat grid -->
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-val">{weekSessions}</div>
      <div class="stat-lbl">Sessions</div>
    </div>
    <div class="stat-card">
      <div class="stat-val">{weekSets}</div>
      <div class="stat-lbl">Sets</div>
    </div>
    <div class="stat-card">
      <div class="stat-val">{fatigueReport ? fatigueScore : '—'}</div>
      <div class="stat-lbl">Fatigue /10</div>
    </div>
  </div>

  <!-- Week chart -->
  <div class="week-card">
    <div class="week-card-hdr">
      <span class="serif-15">Weekly Volume</span>
      <span class="muted-10">{weekSets} sets this week</span>
    </div>
    <div class="week-bars">
      {#each weekDays as d}
        <div class="week-col">
          <div class="week-bar" style="height:{d.trained ? Math.max(4, (d.sets / maxWeekSets) * 36) : 3}px; background:{d.trained ? 'var(--accent)' : 'var(--faint)'}"></div>
          <div class="week-day" style="color:{d.trained ? 'var(--muted)' : 'var(--faint)'}">{d.label}</div>
        </div>
      {/each}
    </div>
  </div>

  <!-- Fatigue warning banner -->
  {#if fatigueReport?.deload_recommended}
    <div class="fatigue-banner" style="border-color:{fatigueScore>=8?'rgba(232,54,93,0.4)':'rgba(232,160,54,0.3)'}; background:{fatigueScore>=8?'rgba(232,54,93,0.07)':'rgba(232,160,54,0.07)'}">
      <div class="fatigue-banner-title" style="color:{fatigueScore>=8?'var(--danger)':'var(--warn)'}">
        {fatigueScore >= 8 ? 'Critical fatigue — deload now' : 'High fatigue — consider a deload'}
      </div>
      {#each (fatigueReport.reasons || []) as r}
        <div class="fatigue-reason">{r}</div>
      {/each}
    </div>
  {/if}

  <!-- Session CTA -->
  {#if $activeSession}
    <div class="active-card">
      <div class="active-label">In Progress</div>
      <div class="active-body">
        <div>
          <div class="active-name">{$activeSession.name || 'Unnamed Session'}</div>
          <div class="active-elapsed">{elapsed}</div>
        </div>
        <a href="/log" class="resume-btn">Resume →</a>
      </div>
    </div>
  {:else}
    <div class="cta-wrap">
      <button class="begin-btn" on:click={beginSession} disabled={creating}>
        {creating ? 'Starting…' : 'Begin Session'}
      </button>
      <div class="cta-secondary">
        <a href="/program" class="cta-sec-btn">From Program</a>
        <a href="/templates" class="cta-sec-btn">From Template</a>
        <button class="cta-sec-btn generate-btn" on:click={generateSession} disabled={generating}>
          {generating ? 'Building…' : 'Generate Session'}
        </button>
      </div>
    </div>
  {/if}

  <!-- Next planned -->
  {#if nextPlanned}
    <a href="/program" class="next-card">
      <div>
        <div class="next-label">Next Up</div>
        <div class="serif-17">{nextPlanned.split_day_name || 'Next Session'}</div>
        <div class="muted-11">{nextPlanned.exercise_count ?? ''} exercises</div>
      </div>
      <span class="tomorrow-badge">Tomorrow ›</span>
    </a>
  {/if}

  <!-- Recent sessions -->
  {#if loading}
    <div class="loading-row"><div class="spinner"></div></div>
  {:else if recentSessions.length > 0}
    <div class="divider-row">
      <div class="divider-line"></div>
      <div class="divider-label">Recent</div>
      <div class="divider-line"></div>
    </div>
    {#each recentSessions as s, i}
      <a href="/history" class="session-row" class:border-b={i < recentSessions.length - 1}>
        <div class="session-main">
          <div class="serif-17">{s.name || 'Unnamed Session'}</div>
          <div class="session-meta">
            {sessionDateStr(s)}{sessionDuration(s) ? ' · ' + sessionDuration(s) : ''} · {s.set_count} sets
          </div>
        </div>
        <div class="muscle-tags">
          {#each (s.muscles || []).slice(0, 3) as m}
            <span class="muscle-tag">{m}</span>
          {/each}
        </div>
      </a>
    {/each}
  {:else}
    <div class="empty-state" style="padding:32px 0;">
      <p>No sessions yet — start your first workout!</p>
    </div>
  {/if}
</div>

<style>
  .home { padding-bottom: 8px; }

  /* Header */
  .hdr {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 6px;
  }
  .brand-label {
    font-size: 9px;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 6px;
  }
  .greeting {
    font-family: var(--serif);
    font-size: 28px;
    color: var(--text);
    line-height: 1.1;
  }
  .greeting em {
    font-style: italic;
    color: var(--accent);
  }
  .hdr-right { text-align: right; }
  .fatigue-label {
    font-size: 9px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 3px;
  }
  .date-line {
    font-size: 11px;
    color: var(--muted);
    margin-bottom: 18px;
  }

  /* Stats */
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }
  .stat-card {
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-radius: var(--radius-lg);
    padding: 12px 8px;
    text-align: center;
  }
  .stat-val {
    font-family: var(--serif);
    font-size: 24px;
    color: var(--accent);
    line-height: 1;
  }
  .stat-lbl {
    font-size: 10px;
    color: var(--muted);
    margin-top: 3px;
  }

  /* Week chart */
  .week-card {
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-radius: var(--radius-lg);
    padding: 14px 16px;
    margin-bottom: 12px;
  }
  .week-card-hdr {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  .serif-15 { font-family: var(--serif); font-size: 15px; color: var(--text); }
  .muted-10 { font-size: 10px; color: var(--muted); }
  .week-bars {
    display: flex;
    gap: 4px;
    align-items: flex-end;
    height: 48px;
  }
  .week-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    justify-content: flex-end;
  }
  .week-bar {
    width: 100%;
    border-radius: 3px 3px 0 0;
    transition: height 0.4s ease;
  }
  .week-day { font-size: 9px; }

  /* Fatigue banner */
  .fatigue-banner {
    border: 1px solid;
    border-radius: var(--radius-lg);
    padding: 12px 14px;
    margin-bottom: 12px;
  }
  .fatigue-banner-title { font-size: 12px; font-weight: 600; margin-bottom: 4px; }
  .fatigue-reason { font-size: 11px; color: var(--muted); line-height: 1.6; }

  /* Active session card */
  .active-card {
    background: var(--accent-bg);
    border: 1px solid rgba(232,54,93,0.25);
    border-radius: var(--radius-lg);
    padding: 16px 18px;
    margin-bottom: 12px;
  }
  .active-label {
    font-size: 9px;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    font-weight: 600;
    margin-bottom: 8px;
  }
  .active-body { display: flex; justify-content: space-between; align-items: flex-end; }
  .active-name { font-family: var(--serif); font-size: 20px; color: var(--text); }
  .active-elapsed {
    font-family: var(--serif);
    font-size: 18px;
    color: var(--accent);
    font-style: italic;
    margin-top: 2px;
  }
  .resume-btn {
    background: var(--accent);
    color: #fff;
    border-radius: var(--radius);
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
  }

  /* Check-in card */
  .checkin-card {
    background: var(--surf); border: 1px solid rgba(232,54,93,0.25);
    border-radius: var(--radius-lg); padding: 14px 16px; margin-bottom: 14px;
  }
  .checkin-hdr { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; }
  .checkin-title { font-family:var(--serif); font-size:16px; color:var(--text); }
  .checkin-sub { font-size:11px; color:var(--muted); margin-top:2px; }
  .checkin-skip { font-size:11px; color:var(--muted); cursor:pointer; padding:2px 0; text-decoration:underline; }
  .checkin-skip:hover { color:var(--accent); }
  .checkin-row { display:flex; align-items:center; justify-content:space-between; padding:6px 0; }
  .checkin-lbl { font-size:12px; color:var(--text); }
  .checkin-dots { display:flex; gap:8px; }
  .dot {
    width:16px; height:16px; border-radius:50%;
    border:1.5px solid var(--bdr-2); background:transparent;
    cursor:pointer; transition:all 0.15s;
  }
  .dot.filled { background:var(--accent); border-color:var(--accent); }
  .checkin-submit { width:100%; margin-top:12px; }

  /* CTA */
  .cta-wrap { margin-bottom: 12px; }
  .begin-btn {
    width: 100%;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: var(--radius-lg);
    padding: 17px;
    font-family: var(--serif);
    font-size: 20px;
    cursor: pointer;
    margin-bottom: 8px;
    transition: background 0.15s;
  }
  .begin-btn:hover { background: #f05070; }
  .begin-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .cta-secondary { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .generate-btn { grid-column: 1 / -1; border:none; cursor:pointer; font-size:12px; font-weight:500; }
  .cta-sec-btn {
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-radius: var(--radius-lg);
    padding: 11px;
    font-size: 12px;
    color: var(--muted);
    font-weight: 500;
    text-align: center;
    text-decoration: none;
    transition: border-color 0.15s, color 0.15s;
  }
  .cta-sec-btn:hover { border-color: var(--accent); color: var(--accent); }

  /* Next planned */
  .next-card {
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-radius: var(--radius-lg);
    padding: 13px 16px;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    text-decoration: none;
    color: var(--text);
    transition: border-color 0.15s;
  }
  .next-card:hover { border-color: var(--accent); }
  .next-label {
    font-size: 9px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 3px;
  }
  .serif-17 { font-family: var(--serif); font-size: 17px; color: var(--text); }
  .muted-11 { font-size: 11px; color: var(--muted); margin-top: 1px; }
  .tomorrow-badge {
    font-size: 10px;
    padding: 4px 10px;
    border-radius: var(--radius);
    background: var(--accent-bg);
    color: var(--accent);
    white-space: nowrap;
  }

  /* Recent sessions */
  .loading-row { display: flex; justify-content: center; padding: 24px 0; }
  .divider-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 4px;
  }
  .divider-line { flex: 1; height: 1px; background: var(--bdr); }
  .divider-label {
    font-size: 9px;
    color: var(--faint);
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }
  .session-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 12px 0;
    text-decoration: none;
    color: var(--text);
    gap: 12px;
  }
  .border-b { border-bottom: 1px solid var(--bdr); }
  .session-meta { color: var(--muted); font-size: 11px; margin-top: 2px; }
  .muscle-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    justify-content: flex-end;
    max-width: 110px;
    flex-shrink: 0;
  }
  .muscle-tag {
    font-size: 9px;
    padding: 2px 7px;
    border-radius: 3px;
    background: var(--accent-bg);
    color: var(--accent);
    border: 1px solid rgba(232,54,93,0.2);
  }
</style>
