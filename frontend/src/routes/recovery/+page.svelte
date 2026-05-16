<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let muscles = [];
  let fatigue = null;
  let loading = true;
  let error = null;

  const STATUS_ORDER = { red: 0, amber: 1, gray: 2, green: 3 };

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

  onMount(async () => {
    try {
      const [mapData, fatigueData] = await Promise.all([
        api.recovery.getMap(),
        api.volume.fatigueReport(),
      ]);
      muscles = mapData.muscles;
      fatigue = fatigueData;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; }

  function fmtDays(d) {
    if (d === null || d === undefined) return '—';
    if (d < 1) return `${Math.round(d * 24)}h ago`;
    return `${d.toFixed(1)}d ago`;
  }

  $: sortedMuscles = [...muscles].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]);

  $: fatiguePct  = fatigue ? (fatigue.fatigue_score / 10) * 100 : 0;
  $: fatigueColor = fatigue ? FAT_COLOR[fatigue.overall_fatigue] : 'var(--text-muted)';
</script>

<div class="page">
  <div class="page-header">
    <h2>Recovery</h2>
    <p class="subtitle">Muscle readiness based on training recency and effort</p>
  </div>

  {#if loading}
    <div class="spinner-wrap"><div class="spinner"></div></div>
  {:else if error}
    <div class="error-box">{error}</div>
  {:else}

    {#if fatigue}
      <div class="summary-card">
        <div class="summary-top">
          <div>
            <div class="sum-label">Overall Fatigue</div>
            <div class="sum-level" style="color:{fatigueColor}">{cap(fatigue.overall_fatigue)}</div>
          </div>
          <div class="score-badge" style="color:{fatigueColor}; border-color:{fatigueColor}44">
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
          <div class="deload-pill">Deload recommended — take a lighter week</div>
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

    <div class="muscle-list">
      {#each sortedMuscles as m}
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
</div>

<style>
  .page {
    padding: 1.5rem 2rem 3rem;
    max-width: 720px;
    margin: 0 auto;
  }

  .page-header { margin-bottom: 1.5rem; }

  h2 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text);
    margin: 0 0 0.2rem;
  }

  .subtitle {
    font-size: 0.82rem;
    color: var(--text-muted);
    margin: 0;
  }

  /* Summary card */
  .summary-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem 1rem;
    margin-bottom: 0.5rem;
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

  .score-num  { font-size: 1.6rem; font-weight: 700; line-height: 1; }
  .score-denom { font-size: 0.85rem; font-weight: 500; color: var(--text-muted); }

  /* Gauge */
  .gauge-wrap { margin-bottom: 0.75rem; }

  .gauge-track {
    position: relative;
    height: 8px;
    border-radius: 4px;
    background: var(--border);
    overflow: hidden;
    margin-bottom: 4px;
  }

  .gz { position: absolute; top: 0; height: 100%; }
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
  }

  .gauge-legend span:not(:first-child) { text-align: center; }
  .gauge-legend span:last-child { text-align: right; }

  .deload-pill {
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

  .no-flags { font-size: 0.82rem; color: var(--text-muted); margin: 0.5rem 0 0; }

  /* Muscle list */
  .muscle-list { border-top: 1px solid var(--border); margin-top: 0.5rem; }

  .rec-row {
    display: grid;
    grid-template-columns: 10px 140px 1fr 70px 110px;
    align-items: center;
    gap: 0.75rem;
    padding: 0.65rem 0;
    border-bottom: 1px solid var(--border);
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .rec-name   { font-size: 0.9rem; font-weight: 500; color: var(--text); }
  .rec-since  { font-size: 0.82rem; color: var(--text-muted); }
  .rec-rir    { font-size: 0.82rem; color: var(--text-muted); text-align: right; }
  .rec-status { font-size: 0.82rem; font-weight: 600; text-align: right; }

  /* Spinner / error */
  .spinner-wrap { display: flex; justify-content: center; padding: 4rem 0; }

  .spinner {
    width: 32px; height: 32px;
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
    .rec-row { grid-template-columns: 10px 1fr 65px 100px; }
    .rec-rir { display: none; }
    .gauge-legend span:not(:first-child):not(:last-child) { display: none; }
  }
</style>
