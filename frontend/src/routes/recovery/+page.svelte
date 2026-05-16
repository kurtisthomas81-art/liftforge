<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let view = 'fatigue';
  let muscles = [];
  let fatigue = null;
  let weekVolume = null;
  let loading = true;
  let error = null;

  const GROUPS = [
    { key: 'push', label: 'Push',  names: ['chest', 'shoulders', 'triceps'] },
    { key: 'pull', label: 'Pull',  names: ['back', 'lats', 'traps', 'biceps'] },
    { key: 'legs', label: 'Legs',  names: ['quads', 'hamstrings', 'glutes', 'calves'] },
    { key: 'core', label: 'Core',  names: ['abs'] },
  ];

  const REC_COLOR = {
    green: 'var(--success)',
    amber: 'var(--primary)',
    red:   'var(--danger)',
    gray:  '#505050',
  };

  const REC_LABEL = {
    green: 'Recovered',
    amber: 'Recovering',
    red:   'Fatigued',
    gray:  'Not trained',
  };

  const FAT_COLOR = {
    low:      'var(--success)',
    moderate: 'var(--primary)',
    high:     '#e07b39',
    critical: 'var(--danger)',
  };

  const VOL_COLOR = {
    below_mev: 'var(--danger)',
    in_mav:    'var(--success)',
    above_mav: 'var(--primary)',
    at_mrv:    'var(--danger)',
    unknown:   '#505050',
  };

  const VOL_LABEL = {
    below_mev: 'Under MEV',
    in_mav:    'On track',
    above_mav: 'Above sweet spot',
    at_mrv:    'At MRV',
    unknown:   '—',
  };

  onMount(async () => {
    try {
      const [mapData, fatigueData, weekData] = await Promise.all([
        api.recovery.getMap(),
        api.volume.fatigueReport(),
        api.volume.forWeek(null),
      ]);
      muscles = mapData.muscles;
      fatigue = fatigueData;
      weekVolume = weekData;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; }
  function goalLabel(g) { return cap(g ? g.replace(/_/g, ' ') : ''); }

  function fmtDays(d) {
    if (d === null || d === undefined) return '—';
    if (d < 1) return `${Math.round(d * 24)}h ago`;
    return `${d.toFixed(1)}d ago`;
  }

  function fillPct(sets, mrv) {
    if (!mrv) return 0;
    return Math.min(100, (sets / mrv) * 100);
  }

  function pct(val, mrv) {
    if (!mrv) return 0;
    return Math.min(100, (val / mrv) * 100);
  }

  function groupMuscles(names, list) {
    return names.map(n => list.find(m => m.muscle === n)).filter(Boolean);
  }

  $: fatiguePct = fatigue ? (fatigue.fatigue_score / 10) * 100 : 0;
  $: fatigueColor = fatigue ? FAT_COLOR[fatigue.overall_fatigue] : 'var(--text-muted)';
</script>

<div class="page">
  <div class="page-header">
    <h2>Recovery</h2>
    <div class="seg-ctrl">
      <button class:active={view === 'fatigue'} on:click={() => view = 'fatigue'}>Fatigue</button>
      <button class:active={view === 'balance'} on:click={() => view = 'balance'}>Balance</button>
    </div>
  </div>

  {#if loading}
    <div class="spinner-wrap"><div class="spinner"></div></div>
  {:else if error}
    <div class="error-box">{error}</div>

  {:else if view === 'fatigue'}

    {#if fatigue}
      <div class="summary-card">
        <div class="summary-top">
          <div>
            <div class="sum-label">Overall Fatigue</div>
            <div class="sum-level" style="color:{fatigueColor}">{cap(fatigue.overall_fatigue)}</div>
          </div>
          <div class="score-badge" style="color:{fatigueColor}; border-color:{fatigueColor}40">
            <span class="score-num">{fatigue.fatigue_score}</span><span class="score-denom">/10</span>
          </div>
        </div>

        <div class="gauge-wrap">
          <div class="gauge-track">
            <div class="gz gz-low"  style="width:30%"></div>
            <div class="gz gz-mod"  style="left:30%;width:30%"></div>
            <div class="gz gz-high" style="left:60%;width:20%"></div>
            <div class="gz gz-crit" style="left:80%;width:20%"></div>
            <div class="gauge-fill" style="width:{fatiguePct}%;background:{fatigueColor}"></div>
          </div>
          <div class="gauge-legend">
            <span>Low</span>
            <span>Moderate</span>
            <span>High</span>
            <span>Critical</span>
          </div>
        </div>

        {#if fatigue.deload_recommended}
          <div class="deload-banner">Deload recommended — take a lighter week</div>
        {/if}

        {#if fatigue.reasons.length}
          <ul class="flag-list">
            {#each fatigue.reasons as r}<li>{r}</li>{/each}
          </ul>
        {:else}
          <p class="no-flags">No fatigue flags — training load looks healthy.</p>
        {/if}
      </div>
    {/if}

    {#each GROUPS as g}
      {@const gm = groupMuscles(g.names, muscles)}
      {#if gm.length}
        <div class="group-block">
          <div class="group-hdr">{g.label}</div>
          {#each gm as m}
            <div class="rec-row">
              <div class="dot" style="background:{REC_COLOR[m.status]}"></div>
              <div class="rec-name">{cap(m.muscle)}</div>
              <div class="rec-since">{fmtDays(m.days_since_trained)}</div>
              <div class="rec-rir">{m.avg_rir !== null ? `RIR ${m.avg_rir}` : '—'}</div>
              <div class="rec-status" style="color:{REC_COLOR[m.status]}">{REC_LABEL[m.status]}</div>
            </div>
          {/each}
        </div>
      {/if}
    {/each}

  {:else}

    {#if weekVolume}
      <div class="balance-meta">
        <span class="bm-week">Week of {weekVolume.week_start}</span>
        <span class="bm-goal">{goalLabel(weekVolume.goal)}</span>
      </div>

      <div class="balance-legend">
        <span class="bl-item"><span class="bl-dot" style="background:var(--danger)"></span>Under MEV</span>
        <span class="bl-item"><span class="bl-dot" style="background:var(--success)"></span>In sweet spot</span>
        <span class="bl-item"><span class="bl-dot" style="background:var(--primary)"></span>Above MAV</span>
        <span class="bl-item"><span class="bl-dot" style="background:var(--danger);opacity:.6"></span>At MRV</span>
      </div>

      {#each GROUPS as g}
        {@const gm = groupMuscles(g.names, weekVolume.muscles)}
        {#if gm.length}
          <div class="group-block">
            <div class="group-hdr">{g.label}</div>
            {#each gm as m}
              {@const lm = m.landmarks}
              <div class="vol-row">
                <div class="dot" style="background:{VOL_COLOR[m.status]}"></div>
                <div class="vol-name">{cap(m.muscle)}</div>
                <div class="vol-bar-wrap">
                  <div class="bar-shell">
                    {#if lm}
                      <!-- sweet spot zone -->
                      <div class="bar-sweet"
                        style="left:{pct(lm.mav_low,lm.mrv)}%;width:{pct(lm.mav_high - lm.mav_low, lm.mrv)}%">
                      </div>
                    {/if}
                    <!-- fill -->
                    <div class="bar-fill" style="width:{fillPct(m.sets,lm?.mrv)}%;background:{VOL_COLOR[m.status]}">
                    </div>
                    {#if lm}
                      <!-- MEV tick line drawn above fill -->
                      <div class="bar-mev" style="left:{pct(lm.mev,lm.mrv)}%"></div>
                    {/if}
                  </div>
                  {#if lm}
                    <div class="bar-targets">
                      <span>MEV {lm.mev}</span>
                      <span>MAV {lm.mav_low}–{lm.mav_high}</span>
                      <span>MRV {lm.mrv}</span>
                    </div>
                  {/if}
                </div>
                <div class="vol-right">
                  <div class="vol-count">{m.sets}<span class="vol-unit"> sets</span></div>
                  <div class="vol-label" style="color:{VOL_COLOR[m.status]}">{VOL_LABEL[m.status]}</div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      {/each}
    {/if}

  {/if}
</div>

<style>
  .page {
    padding: 1.5rem 2rem 3rem;
    max-width: 820px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
  }

  h2 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text);
    margin: 0;
  }

  /* Segmented control */
  .seg-ctrl {
    display: flex;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 3px;
    gap: 2px;
  }

  .seg-ctrl button {
    background: none;
    border: none;
    padding: 5px 18px;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-muted);
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    line-height: 1.4;
  }

  .seg-ctrl button.active {
    background: var(--primary);
    color: #fff;
  }

  /* Summary card */
  .summary-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem 1rem;
    margin-bottom: 1.5rem;
  }

  .summary-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.25rem;
  }

  .sum-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
  }

  .sum-level {
    font-size: 1.25rem;
    font-weight: 700;
  }

  .score-badge {
    display: flex;
    align-items: baseline;
    gap: 1px;
    border: 2px solid;
    border-radius: 10px;
    padding: 4px 12px 4px 10px;
  }

  .score-num {
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1;
  }

  .score-denom {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-muted);
  }

  /* Gauge */
  .gauge-wrap {
    margin-bottom: 0.75rem;
  }

  .gauge-track {
    position: relative;
    height: 8px;
    border-radius: 4px;
    background: var(--border);
    overflow: hidden;
    margin-bottom: 4px;
  }

  .gz {
    position: absolute;
    top: 0;
    height: 100%;
  }

  .gz-low  { background: var(--success); opacity: 0.15; }
  .gz-mod  { background: var(--primary); opacity: 0.15; }
  .gz-high { background: #e07b39; opacity: 0.15; }
  .gz-crit { background: var(--danger); opacity: 0.15; }

  .gauge-fill {
    position: absolute;
    top: 0; left: 0;
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
  }

  .gauge-legend {
    display: grid;
    grid-template-columns: 30fr 30fr 20fr 20fr;
    font-size: 0.65rem;
    color: var(--text-muted);
    letter-spacing: 0.02em;
  }

  .gauge-legend span:not(:first-child) { text-align: center; }
  .gauge-legend span:last-child { text-align: right; }

  /* Deload / flags */
  .deload-banner {
    display: inline-block;
    background: var(--danger);
    color: #fff;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 100px;
    margin: 0.75rem 0 0.5rem;
  }

  .flag-list {
    margin: 0.75rem 0 0;
    padding: 0 0 0 1.1rem;
    list-style: disc;
  }

  .flag-list li {
    font-size: 0.8rem;
    color: var(--text-muted);
    line-height: 1.5;
    padding: 0.1rem 0;
  }

  .no-flags {
    font-size: 0.82rem;
    color: var(--text-muted);
    margin: 0.5rem 0 0;
  }

  /* Group sections */
  .group-block {
    margin-bottom: 0.5rem;
  }

  .group-hdr {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    padding: 0.9rem 0 0.4rem;
    border-top: 1px solid var(--border);
  }

  /* Fatigue rows */
  .rec-row {
    display: grid;
    grid-template-columns: 10px 130px 1fr 70px 100px;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0;
    border-bottom: 1px solid var(--border);
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .rec-name {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--text);
  }

  .rec-since {
    font-size: 0.82rem;
    color: var(--text-muted);
  }

  .rec-rir {
    font-size: 0.82rem;
    color: var(--text-muted);
    text-align: right;
  }

  .rec-status {
    font-size: 0.82rem;
    font-weight: 600;
    text-align: right;
  }

  /* Balance meta */
  .balance-meta {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .bm-week {
    font-size: 0.82rem;
    color: var(--text-muted);
  }

  .bm-goal {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 100px;
    background: var(--primary)22;
    color: var(--primary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .balance-legend {
    display: flex;
    gap: 1.2rem;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
    flex-wrap: wrap;
  }

  .bl-item { display: flex; align-items: center; gap: 5px; }

  .bl-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  /* Volume rows */
  .vol-row {
    display: grid;
    grid-template-columns: 10px 110px 1fr 100px;
    align-items: center;
    gap: 0.75rem;
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--border);
  }

  .vol-name {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--text);
    white-space: nowrap;
  }

  /* Zone bar */
  .vol-bar-wrap {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .bar-shell {
    position: relative;
    height: 10px;
    background: var(--border);
    border-radius: 5px;
    overflow: hidden;
  }

  .bar-sweet {
    position: absolute;
    top: 0;
    height: 100%;
    background: var(--success);
    opacity: 0.18;
  }

  .bar-fill {
    position: absolute;
    top: 0; left: 0;
    height: 100%;
    border-radius: 5px;
    transition: width 0.45s ease;
  }

  .bar-mev {
    position: absolute;
    top: 0;
    width: 2px;
    height: 100%;
    background: rgba(255,255,255,0.45);
    z-index: 2;
  }

  .bar-targets {
    display: flex;
    gap: 0.75rem;
    font-size: 0.65rem;
    color: var(--text-muted);
    letter-spacing: 0.01em;
  }

  /* Volume right side */
  .vol-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 1px;
  }

  .vol-count {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
    line-height: 1.1;
  }

  .vol-unit {
    font-size: 0.72rem;
    font-weight: 400;
    color: var(--text-muted);
  }

  .vol-label {
    font-size: 0.72rem;
    font-weight: 500;
  }

  /* Spinner / error */
  .spinner-wrap {
    display: flex;
    justify-content: center;
    padding: 4rem 0;
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .error-box {
    background: var(--surface);
    border: 1px solid var(--danger);
    color: var(--danger);
    padding: 1rem;
    border-radius: var(--radius);
    font-size: 0.875rem;
  }

  @media (max-width: 600px) {
    .page { padding: 1rem 1rem 3rem; }
    .rec-row { grid-template-columns: 10px 1fr 60px 80px; }
    .rec-rir { display: none; }
    .vol-row { grid-template-columns: 10px 90px 1fr 80px; }
    .bar-targets { display: none; }
    .gauge-legend span:not(:first-child):not(:last-child) { display: none; }
  }
</style>
