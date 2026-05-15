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

  function dColor(muscle) {
    const m = muscles.find(m => m.muscle === muscle);
    if (!m || m.status === 'gray') return STATUS_COLOR.green;
    return STATUS_COLOR[m.status];
  }

  function opa() { return 0.45; }

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
    <p class="subtitle">Muscle readiness based on training recency and effort (RIR — reps left in tank)</p>
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
      <!-- SVG Body Diagrams — image base + colored status overlays -->
      <div class="diagrams">

        <!-- Front view: left half of muscle.png (x=0–123) -->
        <div class="diagram-wrap">
          <div class="diagram-label">Front</div>
          <svg viewBox="0 0 124 357" xmlns="http://www.w3.org/2000/svg">
            <image href="/muscle.png" x="0" y="0" width="247" height="357"/>

            <!-- Chest / Pectorals -->
            <ellipse cx="48" cy="112" rx="20" ry="20" fill={dColor('chest')} opacity={opa()}/>
            <ellipse cx="76" cy="112" rx="20" ry="20" fill={dColor('chest')} opacity={opa()}/>

            <!-- Shoulders / Anterior deltoid -->
            <ellipse cx="22" cy="87" rx="13" ry="12" fill={dColor('shoulders')} opacity={opa()}/>
            <ellipse cx="101" cy="87" rx="13" ry="12" fill={dColor('shoulders')} opacity={opa()}/>

            <!-- Biceps -->
            <ellipse cx="17" cy="128" rx="8" ry="22" fill={dColor('biceps')} opacity={opa()}/>
            <ellipse cx="106" cy="128" rx="8" ry="22" fill={dColor('biceps')} opacity={opa()}/>

            <!-- Abs -->
            <rect x="38" y="136" width="47" height="68" rx="6" fill={dColor('abs')} opacity={opa()}/>

            <!-- Quads -->
            <rect x="27" y="220" width="30" height="82" rx="8" fill={dColor('quads')} opacity={opa()}/>
            <rect x="66" y="220" width="30" height="82" rx="8" fill={dColor('quads')} opacity={opa()}/>

            <!-- Calves (front) -->
            <ellipse cx="42" cy="328" rx="13" ry="18" fill={dColor('calves')} opacity={opa()}/>
            <ellipse cx="81" cy="328" rx="13" ry="18" fill={dColor('calves')} opacity={opa()}/>
          </svg>
        </div>

        <!-- Back view: right half of muscle.png (x=124–247) -->
        <div class="diagram-wrap">
          <div class="diagram-label">Back</div>
          <svg viewBox="124 0 123 357" xmlns="http://www.w3.org/2000/svg">
            <image href="/muscle.png" x="0" y="0" width="247" height="357"/>

            <!-- Trapezius -->
            <ellipse cx="185" cy="96" rx="33" ry="20" fill={dColor('traps')} opacity={opa()}/>

            <!-- Lats -->
            <rect x="137" y="112" width="24" height="70" rx="8" fill={dColor('lats')} opacity={opa()}/>
            <rect x="209" y="112" width="24" height="70" rx="8" fill={dColor('lats')} opacity={opa()}/>

            <!-- Mid back / rhomboids -->
            <rect x="163" y="106" width="44" height="55" rx="6" fill={dColor('back')} opacity={opa()}/>

            <!-- Triceps -->
            <ellipse cx="134" cy="128" rx="8" ry="22" fill={dColor('triceps')} opacity={opa()}/>
            <ellipse cx="236" cy="128" rx="8" ry="22" fill={dColor('triceps')} opacity={opa()}/>

            <!-- Glutes -->
            <ellipse cx="167" cy="234" rx="21" ry="21" fill={dColor('glutes')} opacity={opa()}/>
            <ellipse cx="208" cy="234" rx="21" ry="21" fill={dColor('glutes')} opacity={opa()}/>

            <!-- Hamstrings -->
            <rect x="145" y="260" width="32" height="46" rx="8" fill={dColor('hamstrings')} opacity={opa()}/>
            <rect x="193" y="260" width="32" height="46" rx="8" fill={dColor('hamstrings')} opacity={opa()}/>

            <!-- Calves (back) -->
            <ellipse cx="161" cy="327" rx="13" ry="18" fill={dColor('calves')} opacity={opa()}/>
            <ellipse cx="209" cy="327" rx="13" ry="18" fill={dColor('calves')} opacity={opa()}/>
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
              <th title="Average Reps In Reserve — higher means more recovery capacity">Avg RIR</th>
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
    width: 120px;
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
