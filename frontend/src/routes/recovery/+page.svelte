<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let muscles = [];
  let loading = true;
  let error = null;

  const STATUS_COLOR = {
    green: 'var(--success)',
    amber: 'var(--primary)',
    red:   'var(--danger)',
    gray:  '#333333',
  };

  const STATUS_LABEL = {
    green: 'Recovered',
    amber: 'Recovering',
    red:   'Fatigued',
    gray:  'Not logged',
  };

  const STATUS_ORDER = { red: 0, amber: 1, gray: 2, green: 3 };

  onMount(async () => {
    try {
      const data = await api.recovery.getMap();
      muscles = data.muscles.slice().sort(
        (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]
      );
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function color(muscle) {
    const m = muscles.find(m => m.muscle === muscle);
    return m ? STATUS_COLOR[m.status] : '#333333';
  }

  function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function fmtDays(d) {
    if (d === null || d === undefined) return '—';
    if (d < 1) return `${Math.round(d * 24)}h ago`;
    return `${d.toFixed(1)}d ago`;
  }
</script>

<div class="page">
  <div class="page-header">
    <h2>Recovery Map</h2>
    <p class="subtitle">Muscle readiness based on training recency and effort (RIR)</p>
    <div class="legend">
      <span class="dot" style="background:var(--success)"></span> Recovered
      <span class="dot" style="background:var(--primary)"></span> Recovering
      <span class="dot" style="background:var(--danger)"></span> Fatigued
      <span class="dot" style="background:#333333; border:1px solid #555"></span> Not logged
    </div>
  </div>

  {#if loading}
    <div class="spinner-wrap"><div class="spinner"></div></div>
  {:else if error}
    <div class="error-box">{error}</div>
  {:else}
    <div class="content">
      <!-- SVG Body Diagrams -->
      <div class="diagrams">
        <!-- Front view -->
        <div class="diagram-wrap">
          <div class="diagram-label">Front</div>
          <svg viewBox="0 0 120 298" xmlns="http://www.w3.org/2000/svg">
            <!-- Body silhouette -->
            <circle cx="60" cy="20" r="18" fill="#232323"/>
            <rect x="55" y="36" width="10" height="13" fill="#232323"/>
            <rect x="18" y="46" width="84" height="22" rx="8" fill="#232323"/>
            <rect x="8"  y="46" width="22" height="86" rx="7" fill="#232323"/>
            <rect x="90" y="46" width="22" height="86" rx="7" fill="#232323"/>
            <rect x="30" y="62" width="60" height="100" rx="5" fill="#232323"/>
            <rect x="6"  y="128" width="20" height="60" rx="6" fill="#232323"/>
            <rect x="94" y="128" width="20" height="60" rx="6" fill="#232323"/>
            <rect x="26" y="158" width="68" height="22" rx="8" fill="#232323"/>
            <rect x="28" y="176" width="28" height="72" rx="6" fill="#232323"/>
            <rect x="64" y="176" width="28" height="72" rx="6" fill="#232323"/>
            <rect x="30" y="244" width="24" height="50" rx="6" fill="#232323"/>
            <rect x="66" y="244" width="24" height="50" rx="6" fill="#232323"/>

            <!-- Muscle overlays -->
            <!-- Chest -->
            <rect x="33" y="66" width="22" height="26" rx="4" fill={color('chest')} opacity="0.9"/>
            <rect x="65" y="66" width="22" height="26" rx="4" fill={color('chest')} opacity="0.9"/>
            <!-- Shoulders (front delt) -->
            <ellipse cx="19" cy="58" rx="10" ry="8" fill={color('shoulders')} opacity="0.9"/>
            <ellipse cx="101" cy="58" rx="10" ry="8" fill={color('shoulders')} opacity="0.9"/>
            <!-- Biceps -->
            <rect x="9"  y="80" width="14" height="38" rx="4" fill={color('biceps')} opacity="0.9"/>
            <rect x="97" y="80" width="14" height="38" rx="4" fill={color('biceps')} opacity="0.9"/>
            <!-- Abs (3 pairs) -->
            <rect x="37" y="96"  width="17" height="13" rx="3" fill={color('abs')} opacity="0.9"/>
            <rect x="66" y="96"  width="17" height="13" rx="3" fill={color('abs')} opacity="0.9"/>
            <rect x="37" y="112" width="17" height="13" rx="3" fill={color('abs')} opacity="0.9"/>
            <rect x="66" y="112" width="17" height="13" rx="3" fill={color('abs')} opacity="0.9"/>
            <rect x="37" y="128" width="17" height="13" rx="3" fill={color('abs')} opacity="0.9"/>
            <rect x="66" y="128" width="17" height="13" rx="3" fill={color('abs')} opacity="0.9"/>
            <!-- Quads -->
            <rect x="29" y="180" width="26" height="62" rx="5" fill={color('quads')} opacity="0.9"/>
            <rect x="65" y="180" width="26" height="62" rx="5" fill={color('quads')} opacity="0.9"/>
            <!-- Calves -->
            <rect x="31" y="248" width="22" height="42" rx="5" fill={color('calves')} opacity="0.9"/>
            <rect x="67" y="248" width="22" height="42" rx="5" fill={color('calves')} opacity="0.9"/>
          </svg>
        </div>

        <!-- Back view -->
        <div class="diagram-wrap">
          <div class="diagram-label">Back</div>
          <svg viewBox="0 0 120 298" xmlns="http://www.w3.org/2000/svg">
            <!-- Body silhouette (same as front) -->
            <circle cx="60" cy="20" r="18" fill="#232323"/>
            <rect x="55" y="36" width="10" height="13" fill="#232323"/>
            <rect x="18" y="46" width="84" height="22" rx="8" fill="#232323"/>
            <rect x="8"  y="46" width="22" height="86" rx="7" fill="#232323"/>
            <rect x="90" y="46" width="22" height="86" rx="7" fill="#232323"/>
            <rect x="30" y="62" width="60" height="100" rx="5" fill="#232323"/>
            <rect x="6"  y="128" width="20" height="60" rx="6" fill="#232323"/>
            <rect x="94" y="128" width="20" height="60" rx="6" fill="#232323"/>
            <rect x="26" y="158" width="68" height="22" rx="8" fill="#232323"/>
            <rect x="28" y="176" width="28" height="72" rx="6" fill="#232323"/>
            <rect x="64" y="176" width="28" height="72" rx="6" fill="#232323"/>
            <rect x="30" y="244" width="24" height="50" rx="6" fill="#232323"/>
            <rect x="66" y="244" width="24" height="50" rx="6" fill="#232323"/>

            <!-- Muscle overlays -->
            <!-- Traps -->
            <rect x="34" y="50" width="52" height="22" rx="6" fill={color('traps')} opacity="0.9"/>
            <!-- Lats -->
            <rect x="28" y="68" width="14" height="84" rx="4" fill={color('lats')} opacity="0.9"/>
            <rect x="78" y="68" width="14" height="84" rx="4" fill={color('lats')} opacity="0.9"/>
            <!-- Back (mid / rhomboids) -->
            <rect x="42" y="74" width="36" height="48" rx="4" fill={color('back')} opacity="0.9"/>
            <!-- Triceps -->
            <rect x="9"  y="78" width="14" height="44" rx="4" fill={color('triceps')} opacity="0.9"/>
            <rect x="97" y="78" width="14" height="44" rx="4" fill={color('triceps')} opacity="0.9"/>
            <!-- Glutes -->
            <rect x="28" y="164" width="28" height="30" rx="8" fill={color('glutes')} opacity="0.9"/>
            <rect x="64" y="164" width="28" height="30" rx="8" fill={color('glutes')} opacity="0.9"/>
            <!-- Hamstrings -->
            <rect x="29" y="194" width="26" height="48" rx="5" fill={color('hamstrings')} opacity="0.9"/>
            <rect x="65" y="194" width="26" height="48" rx="5" fill={color('hamstrings')} opacity="0.9"/>
            <!-- Calves -->
            <rect x="31" y="248" width="22" height="42" rx="5" fill={color('calves')} opacity="0.9"/>
            <rect x="67" y="248" width="22" height="42" rx="5" fill={color('calves')} opacity="0.9"/>
          </svg>
        </div>
      </div>

      <!-- Muscle status table -->
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Muscle</th>
              <th>Status</th>
              <th>Last Trained</th>
              <th>Avg RIR</th>
            </tr>
          </thead>
          <tbody>
            {#each muscles as m}
              <tr>
                <td class="muscle-name">{capitalize(m.muscle)}</td>
                <td>
                  <span class="badge" style="background:{STATUS_COLOR[m.status]}22; color:{STATUS_COLOR[m.status]}; border-color:{STATUS_COLOR[m.status]}44">
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
    </div>
  {/if}
</div>

<style>
  .page {
    padding: 2rem;
    max-width: 900px;
    margin: 0 auto;
  }

  .page-header {
    margin-bottom: 2rem;
  }

  h2 {
    font-size: 1.4rem;
    font-weight: 600;
    color: var(--text);
    margin: 0 0 0.25rem;
  }

  .subtitle {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin: 0 0 1rem;
  }

  .legend {
    display: flex;
    align-items: center;
    gap: 1.2rem;
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 4px;
    vertical-align: middle;
  }

  .content {
    display: flex;
    gap: 2.5rem;
    align-items: flex-start;
  }

  .diagrams {
    display: flex;
    gap: 1.5rem;
    flex-shrink: 0;
  }

  .diagram-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }

  .diagram-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  svg {
    width: 130px;
    height: auto;
    display: block;
  }

  .table-wrap {
    flex: 1;
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
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0 0.75rem 0.6rem;
    border-bottom: 1px solid var(--border);
  }

  td {
    padding: 0.6rem 0.75rem;
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
    font-size: 0.78rem;
    font-weight: 500;
    border: 1px solid transparent;
  }

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

  @media (max-width: 640px) {
    .page { padding: 1rem; }
    .content { flex-direction: column; align-items: center; }
    .table-wrap { width: 100%; }
  }
</style>
