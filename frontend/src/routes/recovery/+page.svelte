<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let view = 'fatigue'; // 'fatigue' | 'balance'
  let muscles = [];
  let fatigue = null;
  let weekVolume = null;
  let loading = true;
  let error = null;

  const STATUS_COLOR = {
    green: 'var(--success)',
    amber: 'var(--primary)',
    red:   'var(--danger)',
    gray:  '#666666',
  };

  const STATUS_LABEL = {
    green: 'Recovered',
    amber: 'Recovering',
    red:   'Fatigued',
    gray:  'Not logged',
  };

  const STATUS_ORDER = { red: 0, amber: 1, gray: 2, green: 3 };

  const FATIGUE_COLOR = {
    low:      'var(--success)',
    moderate: 'var(--primary)',
    high:     'var(--danger)',
    critical: 'var(--danger)',
  };

  const VOL_COLOR = {
    below_mev: 'var(--danger)',
    in_mav:    'var(--success)',
    above_mav: 'var(--primary)',
    at_mrv:    'var(--danger)',
    unknown:   '#555555',
  };

  const VOL_LABEL = {
    below_mev: 'Under target',
    in_mav:    'On track',
    above_mav: 'Above sweet spot',
    at_mrv:    'At max',
    unknown:   '—',
  };

  onMount(async () => {
    try {
      const [mapData, fatigueData, weekData] = await Promise.all([
        api.recovery.getMap(),
        api.volume.fatigueReport(),
        api.volume.forWeek(null),
      ]);
      muscles = mapData.muscles.slice().sort(
        (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]
      );
      fatigue = fatigueData;
      weekVolume = weekData;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function fmtDays(d) {
    if (d === null || d === undefined) return '—';
    if (d < 1) return `${Math.round(d * 24)}h ago`;
    return `${d.toFixed(1)}d ago`;
  }

  function barPct(sets, mrv) {
    if (!mrv || mrv === 0) return 0;
    return Math.min(100, (sets / mrv) * 100);
  }

  function landmarkPct(val, mrv) {
    if (!mrv) return 0;
    return Math.min(100, (val / mrv) * 100);
  }

  $: balanceMuscles = weekVolume
    ? [...weekVolume.muscles].sort((a, b) => {
        const order = { below_mev: 0, unknown: 1, above_mav: 2, at_mrv: 3, in_mav: 4 };
        return (order[a.status] ?? 5) - (order[b.status] ?? 5);
      })
    : [];

  $: fatigueBarPct = fatigue ? (fatigue.fatigue_score / 10) * 100 : 0;
</script>

<div class="page">
  <div class="page-header">
    <div class="header-row">
      <h2>Recovery</h2>
      <div class="toggle-group">
        <button class="toggle-btn" class:active={view === 'fatigue'} on:click={() => view = 'fatigue'}>
          Fatigue
        </button>
        <button class="toggle-btn" class:active={view === 'balance'} on:click={() => view = 'balance'}>
          Balance
        </button>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="spinner-wrap"><div class="spinner"></div></div>
  {:else if error}
    <div class="error-box">{error}</div>
  {:else if view === 'fatigue'}

    {#if fatigue}
      <div class="fatigue-card">
        <div class="fatigue-top">
          <div>
            <div class="fatigue-label">Overall Fatigue</div>
            <div class="fatigue-level" style="color:{FATIGUE_COLOR[fatigue.overall_fatigue]}">
              {capitalize(fatigue.overall_fatigue)}
            </div>
          </div>
          <div class="fatigue-score" style="color:{FATIGUE_COLOR[fatigue.overall_fatigue]}">
            {fatigue.fatigue_score}<span class="score-denom">/10</span>
          </div>
        </div>

        <div class="gauge-track">
          <div class="gauge-fill" style="width:{fatigueBarPct}%; background:{FATIGUE_COLOR[fatigue.overall_fatigue]}"></div>
          <div class="gauge-tick" style="left:30%"><span class="tick-label">3</span></div>
          <div class="gauge-tick" style="left:60%"><span class="tick-label">6</span></div>
          <div class="gauge-tick" style="left:80%"><span class="tick-label">8</span></div>
        </div>

        {#if fatigue.deload_recommended}
          <div class="deload-banner">
            ⚠ Deload recommended — your body needs a lighter week
          </div>
        {/if}

        {#if fatigue.reasons.length}
          <ul class="reasons-list">
            {#each fatigue.reasons as r}
              <li>{r}</li>
            {/each}
          </ul>
        {:else}
          <p class="reasons-none">No fatigue flags — you're in good shape.</p>
        {/if}
      </div>
    {/if}

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Muscle</th>
            <th>Status</th>
            <th>Last Trained</th>
            <th title="Average Reps In Reserve — higher means more left in the tank">Avg RIR</th>
          </tr>
        </thead>
        <tbody>
          {#each muscles as m}
            <tr>
              <td class="muscle-name">{capitalize(m.muscle)}</td>
              <td>
                <span class="badge"
                  style="background:{STATUS_COLOR[m.status]}22; color:{STATUS_COLOR[m.status]}; border-color:{STATUS_COLOR[m.status]}44">
                  {STATUS_LABEL[m.status]}
                </span>
              </td>
              <td class="muted">{fmtDays(m.days_since_trained)}</td>
              <td class="muted">{m.avg_rir !== null ? m.avg_rir : '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

  {:else}

    {#if weekVolume}
      <div class="balance-meta">
        <span class="meta-week">Week of {weekVolume.week_start}</span>
        <span class="meta-goal">{capitalize(weekVolume.goal.replace('_', ' '))} goal</span>
      </div>

      <div class="balance-legend">
        <span class="leg-item"><span class="leg-dot" style="background:var(--danger)"></span>Under MEV</span>
        <span class="leg-item"><span class="leg-dot" style="background:var(--success)"></span>Sweet spot</span>
        <span class="leg-item"><span class="leg-dot" style="background:var(--primary)"></span>Above MAV</span>
        <span class="leg-item"><span class="leg-dot" style="background:var(--danger); opacity:.65"></span>At MRV</span>
      </div>

      <div class="balance-list">
        {#each balanceMuscles as m}
          {@const lm = m.landmarks}
          <div class="balance-row">
            <div class="balance-name">{capitalize(m.muscle)}</div>
            <div class="balance-bar-col">
              <div class="bar-track">
                {#if lm}
                  <div class="mav-zone"
                    style="left:{landmarkPct(lm.mav_low, lm.mrv)}%; width:{landmarkPct(lm.mav_high - lm.mav_low, lm.mrv)}%">
                  </div>
                  <div class="bar-marker" style="left:{landmarkPct(lm.mev, lm.mrv)}%" title="MEV {lm.mev}"></div>
                  <div class="bar-marker mav-marker" style="left:{landmarkPct(lm.mav_low, lm.mrv)}%" title="MAV {lm.mav_low}"></div>
                  <div class="bar-marker mav-marker" style="left:{landmarkPct(lm.mav_high, lm.mrv)}%" title="MAV {lm.mav_high}"></div>
                {/if}
                <div class="bar-fill" style="width:{barPct(m.sets, lm?.mrv)}%; background:{VOL_COLOR[m.status]}"></div>
              </div>
              {#if lm}
                <div class="bar-targets">MEV {lm.mev} · MAV {lm.mav_low}–{lm.mav_high} · MRV {lm.mrv}</div>
              {/if}
            </div>
            <div class="balance-right">
              <span class="sets-count">{m.sets}</span>
              <span class="badge-sm"
                style="background:{VOL_COLOR[m.status]}22; color:{VOL_COLOR[m.status]}; border-color:{VOL_COLOR[m.status]}44">
                {VOL_LABEL[m.status]}
              </span>
            </div>
          </div>
        {/each}
      </div>
    {/if}

  {/if}
</div>

<style>
  .page {
    padding: 2rem;
    max-width: 780px;
    margin: 0 auto;
  }

  .page-header {
    margin-bottom: 1.5rem;
  }

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  h2 {
    font-size: 1.4rem;
    font-weight: 600;
    color: var(--text);
    margin: 0;
  }

  /* Toggle */
  .toggle-group {
    display: flex;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 3px;
    gap: 2px;
  }

  .toggle-btn {
    background: none;
    border: none;
    padding: 5px 16px;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-muted);
    border-radius: calc(var(--radius) - 2px);
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .toggle-btn.active {
    background: var(--primary);
    color: #fff;
  }

  /* Fatigue card */
  .fatigue-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
  }

  .fatigue-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
  }

  .fatigue-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    margin-bottom: 0.2rem;
  }

  .fatigue-level {
    font-size: 1.15rem;
    font-weight: 600;
  }

  .fatigue-score {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
  }

  .score-denom {
    font-size: 1rem;
    font-weight: 400;
    color: var(--text-muted);
  }

  .gauge-track {
    position: relative;
    height: 8px;
    background: var(--border);
    border-radius: 4px;
    overflow: visible;
    margin-bottom: 1rem;
  }

  .gauge-fill {
    position: absolute;
    top: 0; left: 0;
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
  }

  .gauge-tick {
    position: absolute;
    top: -2px;
    width: 1px;
    height: 12px;
    background: var(--border);
    transform: translateX(-50%);
  }

  .tick-label {
    position: absolute;
    top: 14px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.65rem;
    color: var(--text-muted);
  }

  .deload-banner {
    background: var(--danger)18;
    border: 1px solid var(--danger)44;
    color: var(--danger);
    border-radius: calc(var(--radius) - 2px);
    padding: 0.5rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 500;
    margin-top: 1.25rem;
    margin-bottom: 0.5rem;
  }

  .reasons-list {
    margin: 0.75rem 0 0;
    padding-left: 1.2rem;
    list-style: disc;
  }

  .reasons-list li {
    font-size: 0.8rem;
    color: var(--text-muted);
    padding: 0.15rem 0;
  }

  .reasons-none {
    font-size: 0.82rem;
    color: var(--text-muted);
    margin: 0.5rem 0 0;
  }

  /* Muscle table */
  .table-wrap {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  th {
    text-align: left;
    color: var(--text-muted);
    font-weight: 500;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0 0.75rem 0.6rem;
    border-bottom: 1px solid var(--border);
  }

  td {
    padding: 0.55rem 0.75rem;
    border-bottom: 1px solid var(--border);
    color: var(--text);
  }

  .muscle-name {
    font-weight: 500;
  }

  .muted {
    color: var(--text-muted);
  }

  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 500;
    border: 1px solid transparent;
  }

  /* Balance view */
  .balance-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.75rem;
  }

  .meta-week {
    font-size: 0.82rem;
    color: var(--text-muted);
  }

  .meta-goal {
    font-size: 0.75rem;
    padding: 2px 8px;
    background: var(--primary)22;
    color: var(--primary);
    border-radius: 4px;
    font-weight: 500;
  }

  .balance-legend {
    display: flex;
    gap: 1.2rem;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
  }

  .leg-item {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .leg-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .balance-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .balance-row {
    display: grid;
    grid-template-columns: 110px 1fr auto;
    align-items: center;
    gap: 0.75rem;
  }

  .balance-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text);
    white-space: nowrap;
  }

  .balance-bar-col {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .bar-track {
    position: relative;
    height: 12px;
    background: var(--border);
    border-radius: 6px;
    overflow: hidden;
  }

  .mav-zone {
    position: absolute;
    top: 0;
    height: 100%;
    background: var(--success)22;
    pointer-events: none;
  }

  .bar-marker {
    position: absolute;
    top: 0;
    width: 1.5px;
    height: 100%;
    background: rgba(255,255,255,0.3);
    z-index: 1;
    pointer-events: none;
  }

  .mav-marker {
    background: rgba(255,255,255,0.2);
  }

  .bar-fill {
    position: absolute;
    top: 0; left: 0;
    height: 100%;
    border-radius: 6px;
    transition: width 0.4s ease;
    z-index: 2;
  }

  .bar-targets {
    font-size: 0.67rem;
    color: var(--text-muted);
    letter-spacing: 0.02em;
  }

  .balance-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 3px;
    white-space: nowrap;
  }

  .sets-count {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1;
  }

  .badge-sm {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 500;
    border: 1px solid transparent;
  }

  /* Spinner */
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

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error-box {
    background: var(--surface);
    border: 1px solid var(--danger);
    color: var(--danger);
    padding: 1rem;
    border-radius: var(--radius);
    font-size: 0.875rem;
  }

  @media (max-width: 600px) {
    .page { padding: 1rem; }
    .balance-row { grid-template-columns: 90px 1fr auto; gap: 0.5rem; }
    .balance-name { font-size: 0.8rem; }
    .gauge-tick .tick-label { display: none; }
  }
</style>
