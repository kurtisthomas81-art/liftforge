<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let loading = true;
  let activeMeso = null;
  let weekVolume = null;
  let adherence = null;
  let error = null;
  let fatigueReport = null;
  let selectedSession = null;
  let loadingDetail = false;

  let library = [];
  let libraryLoading = true;
  let installing = null;

  const DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const CHART_MUSCLES = ['chest', 'back', 'quads', 'hamstrings', 'shoulders', 'biceps', 'triceps'];

  onMount(async () => {
    try {
      activeMeso = await api.programs.getActiveMesocycle();
      if (activeMeso) {
        [weekVolume, adherence] = await Promise.all([
          api.volume.forWeek(null),
          api.programs.adherence(activeMeso.id),
        ]);
      }
      try { fatigueReport = await api.volume.fatigueReport(); } catch {}
    } catch (e) { error = e.message; }
    loading = false;

    try { library = await api.programs.listLibrary(); } catch {}
    libraryLoading = false;
  });

  async function quickInstall(slug) {
    installing = slug;
    try {
      await api.programs.installLibraryProgram(slug);
      activeMeso = await api.programs.getActiveMesocycle();
      if (activeMeso) {
        [weekVolume, adherence] = await Promise.all([
          api.volume.forWeek(null),
          api.programs.adherence(activeMeso.id),
        ]);
      }
    } catch (e) { error = e.message; }
    installing = null;
  }

  async function openDay(ps) {
    loadingDetail = true;
    try {
      selectedSession = await api.programs.getPlannedSession(ps.id);
    } catch { selectedSession = ps; }
    loadingDetail = false;
  }

  function closeDay() { selectedSession = null; }

  async function startDay(ps) {
    try {
      const s = await api.programs.startPlannedSession(ps.id || ps.planned_session_id);
      goto('/log');
    } catch { goto('/log'); }
  }

  function goalBadgeColor(goal) {
    if (goal === 'strength') return '#5090e8';
    if (goal === 'recomp') return '#50c880';
    return 'var(--accent)';
  }

  function sessionLabel(ps) {
    const todayDow = new Date().getDay();
    const todayMon = todayDow === 0 ? 6 : todayDow - 1;
    if (ps.session_id) return 'Done';
    if (ps.day_of_week === todayMon) return 'Today';
    return null;
  }

  function getMavWidth(muscle) {
    if (!weekVolume) return 0;
    const entry = weekVolume.muscles.find(m => m.muscle === muscle);
    if (!entry?.landmarks) return 0;
    return Math.min(100, (entry.sets / (entry.landmarks.mrv || 25)) * 100);
  }

  function getMavRange(muscle) {
    if (!weekVolume) return { start:0, end:0 };
    const entry = weekVolume.muscles.find(m => m.muscle === muscle);
    if (!entry?.landmarks) return { start:0, end:0 };
    const mrv = entry.landmarks.mrv || 25;
    return { start:(entry.landmarks.mav_low/mrv)*100, end:(entry.landmarks.mav_high/mrv)*100 };
  }

  function barColor(muscle) {
    if (!weekVolume) return 'var(--muted)';
    const entry = weekVolume.muscles.find(m => m.muscle === muscle);
    if (!entry) return 'var(--muted)';
    if (entry.status === 'at_mrv') return 'var(--danger)';
    if (entry.status === 'in_mav') return 'var(--success)';
    if (entry.status === 'above_mav') return 'var(--warn)';
    return 'var(--muted)';
  }

  function getMevWidth(muscle) {
    if (!weekVolume) return 0;
    const entry = weekVolume.muscles.find(m => m.muscle === muscle);
    if (!entry?.landmarks?.mev) return 0;
    return Math.min(100, (entry.landmarks.mev / (entry.landmarks.mrv || 25)) * 100);
  }

  function getVolumeStatus(muscle) {
    if (!weekVolume) return null;
    const entry = weekVolume.muscles.find(m => m.muscle === muscle);
    if (!entry?.landmarks) return null;
    const { sets } = entry;
    const { mev, mav_low, mav_high, mrv } = entry.landmarks;
    if (sets === 0)
      return { label: 'Not started', color: 'var(--muted)',   rec: `Target this week: ${mav_low}–${mav_high} sets` };
    if (mev && sets < mev)
      return { label: 'Under minimum', color: 'var(--muted)', rec: `Add ${mev - sets} more set${mev - sets !== 1 ? 's' : ''} to reach the floor` };
    if (sets < mav_low)
      return { label: 'Building up',   color: 'var(--muted)', rec: `${mav_low - sets} more set${mav_low - sets !== 1 ? 's' : ''} to enter the target zone` };
    if (sets <= mav_high)
      return { label: 'In the zone',   color: 'var(--success)', rec: "You're in the optimal range" };
    if (sets < mrv)
      return { label: 'Getting close', color: 'var(--warn)',   rec: `${mrv - sets} set${mrv - sets !== 1 ? 's' : ''} from your weekly limit` };
    return   { label: 'At limit',      color: 'var(--danger)', rec: 'At your ceiling — back off next session' };
  }

  function dayCatColor(name) {
    const n = (name || '').toLowerCase();
    if (n.includes('push')) return 'var(--push)';
    if (n.includes('pull')) return 'var(--pull)';
    if (n.includes('leg') || n.includes('squat') || n.includes('quad')) return 'var(--squat)';
    if (n.includes('dead') || n.includes('hinge') || n.includes('rdl')) return 'var(--hinge)';
    if (n.includes('core') || n.includes('abs')) return 'var(--core)';
    return 'var(--accent)';
  }

  $: currentDay = activeMeso?.current_week_sessions?.find(s => !s.session_id) || activeMeso?.current_week_sessions?.[0];
  $: weekProgress = activeMeso ? Math.round((activeMeso.current_week - 1) / activeMeso.weeks_total * 100) : 0;
  $: completedSessions = activeMeso?.current_week_sessions?.filter(s => s.session_id).length ?? 0;
</script>

<svelte:head><title>Program — LiftForge</title></svelte:head>

{#if selectedSession}
  <!-- Drill-in view -->
  <div class="drill-header">
    <button class="back-btn" on:click={closeDay}>‹</button>
    <div class="drill-title-wrap">
      <div class="drill-title">{selectedSession.split_day_name || 'Training Day'}</div>
      <div class="drill-meta">
        {#if selectedSession.exercises?.length}
          {selectedSession.exercises.length} exercises
        {:else if selectedSession.planned_exercises?.length}
          {selectedSession.planned_exercises.length} exercises
        {/if}
      </div>
    </div>
    <span class="drill-cat-badge" style="color:{dayCatColor(selectedSession.split_day_name)};border-color:{dayCatColor(selectedSession.split_day_name)}35;background:{dayCatColor(selectedSession.split_day_name)}18">
      {selectedSession.split_day_name?.split(' ')[0]?.toLowerCase() || 'train'}
    </span>
  </div>

  <div class="drill-body">
    {#each (selectedSession.exercises || selectedSession.planned_exercises || []) as ex, i}
      <div class="drill-ex-row">
        <div class="drill-num" style="background:{dayCatColor(selectedSession.split_day_name)}18;border-color:{dayCatColor(selectedSession.split_day_name)}35;color:{dayCatColor(selectedSession.split_day_name)}">
          {i + 1}
        </div>
        <div class="drill-ex-info">
          <div class="drill-ex-name">{ex.exercise_name || ex.name}</div>
          {#if ex.target_sets}
            <div class="drill-ex-meta">{ex.target_sets} × {ex.target_reps_min ?? '?'}–{ex.target_reps_max ?? '?'}</div>
          {/if}
        </div>
      </div>
    {/each}

    {#if (selectedSession.exercises || selectedSession.planned_exercises || []).length === 0}
      <div class="empty-state" style="padding:32px 0;"><p>No exercises listed</p></div>
    {/if}
  </div>

  <div class="drill-footer">
    <button class="start-day-btn" on:click={() => startDay(selectedSession)}>
      Start This Day
    </button>
  </div>

{:else}
  <!-- Program overview -->

  {#if loading}
    <div class="flex items-center gap-3" style="padding:32px 0;">
      <div class="spinner"></div>
    </div>

  {:else if error}
    <div class="card" style="color:var(--danger);">{error}</div>

  {:else if !activeMeso}
    <div class="start-head">
      <div class="start-title">Start a Program</div>
      <div class="start-sub">Pick a published program or build a custom mesocycle.</div>
    </div>

    {#if libraryLoading}
      <div class="lib-loading">Loading programs…</div>
    {:else}
      <div class="lib-list">
        {#each library as prog}
          <div class="lib-row">
            <div class="lib-row-info">
              <div class="lib-row-name">{prog.name}</div>
              <div class="lib-row-meta">{prog.days_per_week}d/wk · {prog.weeks}wk · {prog.difficulty}</div>
            </div>
            <div class="lib-row-btns">
              <a class="lib-customize-link" href="/programs-library?open={prog.slug}">Customize</a>
              <button class="lib-start-btn" disabled={installing !== null}
                on:click={() => quickInstall(prog.slug)}>
                {installing === prog.slug ? '…' : 'Start'}
              </button>
            </div>
          </div>
        {/each}
      </div>
      <button class="create-btn outline-btn" on:click={() => goto('/program/builder')}>Build Custom Mesocycle</button>
    {/if}

  {:else}
    <!-- Program header -->
    <div class="prog-hdr">
      <div class="prog-label">Current Program</div>
      <div class="prog-name">{activeMeso.name}</div>
      <div class="prog-week-row">
        <span class="prog-week-txt">Week {activeMeso.current_week} of {activeMeso.weeks_total}</span>
        <span class="prog-pct">{weekProgress}%</span>
      </div>
      <div class="prog-bar-track">
        <div class="prog-bar-fill" style="width:{weekProgress}%"></div>
      </div>
      {#if activeMeso.current_week_is_deload}
        <div class="deload-badge">Deload Week</div>
      {/if}
    </div>

    <!-- Adherence card -->
    {#if adherence}
      {@const ov = adherence.overall}
      <div class="adh-card">
        <div class="adh-left">
          <div class="adh-pct">{ov.pct}%</div>
          <div class="adh-sub">{ov.completed} of {ov.planned} sessions</div>
        </div>
        <div class="adh-right">
          {#each adherence.weeks as w}
            {@const isCurrent = w.week_number === adherence.current_week}
            {@const isFuture = w.week_number > adherence.current_week}
            {@const color = isFuture ? 'var(--faint)' : w.pct >= 80 ? 'var(--success)' : w.pct >= 50 ? 'var(--warn)' : 'var(--danger)'}
            <div class="adh-week" class:adh-week-current={isCurrent}
              style="background:{isFuture ? 'var(--surf-2)' : color + '22'};border-color:{isCurrent ? 'var(--accent)' : color}">
              <div class="adh-week-num">W{w.week_number}</div>
              <div class="adh-week-pct" style="color:{isFuture ? 'var(--muted)' : color}">
                {isFuture ? '–' : w.pct + '%'}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Up Next card -->
    {#if currentDay}
      <div class="up-next-card" on:click={() => openDay(currentDay)}
        role="button" tabindex="0"
        on:keydown={e => e.key === 'Enter' && openDay(currentDay)}>
        <div class="up-next-body">
          <div>
            <div class="up-next-label">Up Next</div>
            <div class="up-next-name">{currentDay.split_day_name || 'Training Day'}</div>
            <div class="up-next-meta">{activeMeso.sessions_per_week ?? ''} sessions/week</div>
          </div>
          <button class="start-now-btn" on:click|stopPropagation={() => startDay(currentDay)}>Start</button>
        </div>
      </div>
    {/if}

    <!-- Fatigue banner -->
    {#if fatigueReport?.deload_recommended}
      <div class="fatigue-warn" style="border-color:{fatigueReport.fatigue_score>=8?'rgba(232,54,93,0.4)':'rgba(232,160,54,0.3)'}">
        <div class="fatigue-warn-title" style="color:{fatigueReport.fatigue_score>=8?'var(--danger)':'var(--warn)'}">
          {fatigueReport.fatigue_score>=8?'Critical fatigue — deload now':'High fatigue — consider a deload'}
        </div>
      </div>
    {/if}

    <!-- This week days -->
    <div class="section-title">This Week</div>
    <div class="days-list">
      {#each (activeMeso.current_week_sessions || []).sort((a,b) => a.day_of_week - b.day_of_week) as ps}
        {@const label = sessionLabel(ps)}
        <div class="day-row" class:is-done={!!ps.session_id}
          on:click={() => openDay(ps)}
          role="button" tabindex="0"
          on:keydown={e => e.key === 'Enter' && openDay(ps)}>
          <div class="day-badge" style="background:{dayCatColor(ps.split_day_name)}18;border-color:{dayCatColor(ps.split_day_name)}35;color:{dayCatColor(ps.split_day_name)}">
            {ps.session_id ? '✓' : (ps.day_of_week + 1)}
          </div>
          <div class="day-info">
            <div class="day-name" class:strikethrough={!!ps.session_id}>{ps.split_day_name || 'Training Day'}</div>
            <div class="day-meta">{DOW[ps.day_of_week]}{label ? ' · ' + label : ''}</div>
          </div>
          <div class="day-chevron">›</div>
        </div>
      {/each}
    </div>

    <!-- Weekly volume chart -->
    {#if weekVolume}
      <div class="card mt-4">
        <div class="vol-header">
          <div class="section-title" style="margin-bottom:0">Weekly Volume</div>
          <div class="vol-legend">
            <span class="vol-leg-band"></span>
            <span class="vol-leg-text">Target zone</span>
            <span class="vol-leg-sep">·</span>
            <span class="vol-leg-dot" style="background:var(--success)"></span>
            <span class="vol-leg-text">On track</span>
            <span class="vol-leg-sep">·</span>
            <span class="vol-leg-dot" style="background:var(--warn)"></span>
            <span class="vol-leg-text">Near limit</span>
            <span class="vol-leg-sep">·</span>
            <span class="vol-leg-dot" style="background:var(--danger)"></span>
            <span class="vol-leg-text">Back off</span>
          </div>
        </div>
        <div class="vol-chart">
          {#each CHART_MUSCLES as muscle}
            {@const entry = weekVolume.muscles.find(m => m.muscle === muscle)}
            {@const sets = entry?.sets ?? 0}
            {@const lm = entry?.landmarks}
            {@const mrv = lm?.mrv ?? 25}
            {@const mavR = getMavRange(muscle)}
            {@const status = getVolumeStatus(muscle)}
            <div class="vol-row">
              <div class="vol-muscle">{muscle}</div>
              <div class="vol-main">
                <div class="vol-bar-row">
                  <div class="vol-bar-wrap">
                    {#if lm}
                      <div class="vol-mav-band" style="left:{mavR.start}%;width:{mavR.end - mavR.start}%"></div>
                      {#if lm.mev}
                        <div class="vol-mev-tick" style="left:{getMevWidth(muscle)}%"></div>
                      {/if}
                    {/if}
                    <div class="vol-bar-fill" style="width:{getMavWidth(muscle)}%;background:{barColor(muscle)}"></div>
                  </div>
                  <div class="vol-count">{sets}{lm ? '/' + mrv : ''}</div>
                </div>
                {#if status}
                  <div class="vol-status-row">
                    <span class="vol-chip" style="color:{status.color}">{status.label}</span>
                    <span class="vol-rec">{status.rec}</span>
                  </div>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Actions -->
    <div class="prog-actions">
      <a href="/program/{activeMeso.id}" class="prog-detail-btn">View Details</a>
      <button class="create-outline-btn" on:click={() => goto('/program/builder')}>+ New Program</button>
    </div>

    <!-- Switch program -->
    <a href="/programs-library" class="switch-prog-link">Browse Programs Library →</a>
  {/if}
{/if}

<style>
  /* Drill-in */
  .drill-header {
    display:flex; align-items:center; gap:12px;
    background:var(--surf); border-bottom:1px solid var(--bdr);
    padding:14px 0 14px; margin:-20px -20px 16px;
    padding-left:20px; padding-right:20px;
    position:sticky; top:0; z-index:10;
  }
  .back-btn { background:none; border:none; color:var(--muted); font-size:22px; cursor:pointer; padding:0; line-height:1; }
  .drill-title-wrap { flex:1; }
  .drill-title { font-family:var(--serif); font-size:22px; color:var(--text); line-height:1; }
  .drill-meta { font-size:10px; color:var(--muted); margin-top:2px; }
  .drill-cat-badge {
    font-size:9px; padding:3px 10px; border-radius:var(--radius);
    border:1px solid; text-transform:uppercase; font-weight:600; letter-spacing:0.06em;
  }
  .drill-body { padding-bottom:80px; }
  .drill-ex-row {
    display:flex; align-items:center; gap:12px;
    padding:12px 16px; background:var(--surf);
    border:1px solid var(--bdr); border-radius:var(--radius-lg); margin-bottom:8px;
  }
  .drill-num {
    width:28px; height:28px; border-radius:50%;
    border:1px solid; display:flex; align-items:center; justify-content:center;
    font-size:11px; font-weight:700; flex-shrink:0;
  }
  .drill-ex-name { font-family:var(--serif); font-size:17px; color:var(--text); }
  .drill-ex-meta { font-size:10px; color:var(--muted); margin-top:2px; }
  .drill-footer {
    position:fixed; bottom:var(--tab-h); left:0; right:0;
    padding:12px 20px; background:var(--surf); border-top:1px solid var(--bdr); z-index:10;
  }
  .start-day-btn {
    width:100%; background:var(--accent); color:#fff; border:none;
    border-radius:var(--radius-lg); padding:15px;
    font-family:var(--serif); font-size:18px; cursor:pointer;
    transition:background 0.15s;
  }
  .start-day-btn:hover { background:#f05070; }

  /* Program header */
  .prog-hdr { margin-bottom:16px; }
  .prog-label { font-size:10px; color:var(--accent); text-transform:uppercase; letter-spacing:0.18em; font-weight:600; margin-bottom:6px; }
  .prog-name { font-family:var(--serif); font-size:26px; color:var(--text); line-height:1; margin-bottom:10px; }
  .prog-week-row { display:flex; justify-content:space-between; margin-bottom:8px; font-size:11px; }
  .prog-week-txt { color:var(--muted); }
  .prog-pct { color:var(--accent); }
  .prog-bar-track { height:4px; background:var(--faint); border-radius:2px; }
  .prog-bar-fill { height:100%; background:var(--accent); border-radius:2px; transition:width 0.5s ease; }
  .deload-badge {
    display:inline-block; margin-top:8px;
    font-size:10px; color:var(--warn);
    background:rgba(232,160,54,0.1); border:1px solid rgba(232,160,54,0.25);
    border-radius:var(--radius); padding:2px 8px;
  }

  /* Adherence card */
  .adh-card {
    display:flex; align-items:center; justify-content:space-between; gap:16px;
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:14px 16px; margin-bottom:12px;
  }
  .adh-left { flex-shrink:0; }
  .adh-pct { font-family:var(--serif); font-size:30px; color:var(--text); line-height:1; }
  .adh-sub { font-size:10px; color:var(--muted); margin-top:3px; }
  .adh-right { display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end; }
  .adh-week {
    display:flex; flex-direction:column; align-items:center;
    border:1px solid; border-radius:6px; padding:5px 8px; min-width:36px;
    transition:border-color 0.15s;
  }
  .adh-week-current { border-color:var(--accent) !important; }
  .adh-week-num { font-size:9px; color:var(--muted); font-weight:600; letter-spacing:0.04em; }
  .adh-week-pct { font-size:11px; font-weight:700; margin-top:2px; }

  /* Up Next */
  .up-next-card {
    background:var(--accent-bg); border:1px solid rgba(232,54,93,0.25);
    border-radius:var(--radius-lg); padding:14px 16px; margin-bottom:12px; cursor:pointer;
    transition:border-color 0.15s;
  }
  .up-next-card:hover { border-color:var(--accent); }
  .up-next-body { display:flex; justify-content:space-between; align-items:center; }
  .up-next-label { font-size:9px; color:var(--accent); text-transform:uppercase; letter-spacing:0.13em; font-weight:600; margin-bottom:5px; }
  .up-next-name { font-family:var(--serif); font-size:22px; color:var(--text); }
  .up-next-meta { font-size:11px; color:var(--muted); margin-top:2px; }
  .start-now-btn {
    background:var(--accent); color:#fff; border:none;
    border-radius:var(--radius); padding:10px 18px;
    font-size:12px; font-weight:600; cursor:pointer;
    transition:background 0.15s;
  }
  .start-now-btn:hover { background:#f05070; }

  /* Fatigue warn */
  .fatigue-warn {
    border:1px solid; border-radius:var(--radius-lg);
    padding:10px 14px; margin-bottom:12px;
  }
  .fatigue-warn-title { font-size:12px; font-weight:600; }

  /* Days list */
  .days-list { display:flex; flex-direction:column; gap:8px; margin-bottom:4px; }
  .day-row {
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:13px 16px;
    display:flex; align-items:center; gap:12px;
    cursor:pointer; transition:border-color 0.15s;
  }
  .day-row.is-done { opacity:0.65; }
  .day-row:hover { border-color:var(--accent); }
  .day-badge {
    width:32px; height:32px; border-radius:8px; border:1px solid;
    display:flex; align-items:center; justify-content:center;
    font-size:13px; font-weight:700; flex-shrink:0;
  }
  .day-info { flex:1; }
  .day-name { font-family:var(--serif); font-size:17px; color:var(--text); line-height:1; }
  .day-name.strikethrough { text-decoration:line-through; color:var(--muted); }
  .day-meta { font-size:10px; color:var(--muted); margin-top:2px; }
  .day-chevron { color:var(--muted); font-size:18px; }

  /* Volume chart */
  .vol-header { display:flex; flex-direction:column; gap:8px; margin-bottom:14px; }
  .vol-legend { display:flex; align-items:center; gap:5px; flex-wrap:wrap; }
  .vol-leg-band {
    display:inline-block; width:16px; height:10px; border-radius:3px; flex-shrink:0;
    background:rgba(54,200,122,0.2); border:1px solid rgba(54,200,122,0.45);
  }
  .vol-leg-dot { display:inline-block; width:7px; height:7px; border-radius:50%; flex-shrink:0; }
  .vol-leg-text { font-size:10px; color:var(--muted); }
  .vol-leg-sep { font-size:10px; color:var(--faint); }

  .vol-chart { display:flex; flex-direction:column; gap:14px; }
  .vol-row { display:flex; align-items:flex-start; gap:10px; }
  .vol-muscle { font-size:11px; text-transform:capitalize; width:76px; flex-shrink:0; color:var(--muted); padding-top:2px; }
  .vol-main { flex:1; min-width:0; }
  .vol-bar-row { display:flex; align-items:center; gap:8px; }
  .vol-bar-wrap { flex:1; position:relative; background:var(--surf-2); border-radius:3px; height:10px; overflow:hidden; }
  .vol-mav-band {
    position:absolute; top:0; bottom:0;
    background:rgba(54,200,122,0.2);
    border-left:1px solid rgba(54,200,122,0.4);
    border-right:1px solid rgba(54,200,122,0.4);
  }
  .vol-mev-tick { position:absolute; top:0; bottom:0; width:1px; background:rgba(255,255,255,0.18); }
  .vol-bar-fill { position:absolute; top:0; bottom:0; left:0; border-radius:3px; transition:width 0.3s; }
  .vol-count { font-size:11px; color:var(--muted); width:38px; text-align:right; flex-shrink:0; font-variant-numeric:tabular-nums; }
  .vol-status-row { display:flex; align-items:center; gap:6px; margin-top:5px; }
  .vol-chip { font-size:10px; font-weight:700; flex-shrink:0; }
  .vol-rec { font-size:10px; color:var(--muted); }

  /* Start-a-program empty state */
  .start-head { margin-bottom:16px; }
  .start-title { font-family:var(--serif); font-size:22px; color:var(--text); margin-bottom:4px; }
  .start-sub { font-size:12px; color:var(--muted); }
  .lib-loading { font-size:12px; color:var(--muted); padding:12px 0; }
  .lib-list { display:flex; flex-direction:column; gap:8px; margin-bottom:16px; }
  .lib-row {
    display:flex; align-items:center; justify-content:space-between; gap:12px;
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:12px 14px;
  }
  .lib-row-info { flex:1; min-width:0; }
  .lib-row-name { font-family:var(--serif); font-size:15px; color:var(--text); }
  .lib-row-meta { font-size:10px; color:var(--muted); margin-top:2px; text-transform:capitalize; }
  .lib-row-btns { display:flex; align-items:center; gap:8px; flex-shrink:0; }
  .lib-customize-link {
    font-size:11px; color:var(--muted); text-decoration:none;
    border:1px solid var(--bdr); border-radius:var(--radius);
    padding:5px 10px; transition:color .15s, border-color .15s;
  }
  .lib-customize-link:hover { color:var(--accent); border-color:var(--accent); }
  .lib-start-btn {
    background:var(--accent); color:#fff; border:none;
    border-radius:var(--radius); padding:6px 14px;
    font-size:12px; font-weight:600; cursor:pointer;
    transition:opacity .15s;
  }
  .lib-start-btn:disabled { opacity:.5; cursor:not-allowed; }
  .outline-btn {
    width:100%; background:transparent;
    border:1px dashed var(--bdr); border-radius:var(--radius-lg);
    color:var(--muted); font-size:13px; padding:12px;
    cursor:pointer; transition:border-color .15s, color .15s;
  }
  .outline-btn:hover { border-color:var(--accent); color:var(--accent); }

  /* Switch program link */
  .switch-prog-link {
    display:block; margin-top:14px; text-align:center;
    font-size:12px; color:var(--muted); text-decoration:none;
    transition:color .15s;
  }
  .switch-prog-link:hover { color:var(--accent); }

  /* Legacy empty (kept for safety) */
  .empty-program { display:flex; flex-direction:column; align-items:center; padding:60px 20px; text-align:center; gap:12px; }
  .empty-title { font-family:var(--serif); font-size:22px; }
  .empty-sub { font-size:13px; color:var(--muted); max-width:280px; }
  .create-btn {
    background:var(--accent); color:#fff; border:none;
    border-radius:var(--radius-lg); padding:14px 36px;
    font-family:var(--serif); font-size:18px; cursor:pointer; margin-top:8px;
  }

  /* Actions */
  .prog-actions { display:flex; gap:10px; margin-top:16px; }
  .prog-detail-btn {
    flex:1; text-align:center; padding:11px;
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); font-size:13px; color:var(--muted);
    text-decoration:none; transition:border-color 0.15s;
  }
  .prog-detail-btn:hover { border-color:var(--accent); color:var(--accent); }
  .create-outline-btn {
    flex:1; padding:11px; background:transparent;
    border:1px solid var(--bdr); border-radius:var(--radius-lg);
    font-size:13px; color:var(--muted); cursor:pointer;
    transition:border-color 0.15s;
  }
  .create-outline-btn:hover { border-color:var(--accent); color:var(--accent); }
</style>
