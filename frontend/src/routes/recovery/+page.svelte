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
      <!-- SVG Body Diagrams -->
      <div class="diagrams">
        <!-- Front view -->
        <div class="diagram-wrap">
          <div class="diagram-label">Front</div>
          <svg viewBox="0 0 120 298" xmlns="http://www.w3.org/2000/svg">
            <!-- === BODY SILHOUETTE === -->
            <ellipse cx="60" cy="17" rx="13" ry="14" fill="#1e2020"/>
            <!-- Neck (slightly tapered) -->
            <path d="M54,29 Q55,36 54,41 L66,41 Q65,36 66,29 Z" fill="#1e2020"/>
            <!-- Torso: shoulder width, waist taper, hip flare -->
            <path d="M20,44 L100,44 Q106,50 104,58 L100,64 Q92,90 96,118 Q92,132 84,134 L36,134 Q28,132 24,118 Q28,90 20,64 L16,58 Q14,50 20,44 Z" fill="#1e2020"/>
            <!-- Left upper arm -->
            <path d="M16,52 Q10,58 9,70 L9,112 Q10,118 14,120 Q16,118 17,114 L18,70 Q18,60 20,54 Z" fill="#1e2020"/>
            <!-- Right upper arm -->
            <path d="M104,52 Q110,58 111,70 L111,112 Q110,118 106,120 Q104,118 103,114 L102,70 Q102,60 100,54 Z" fill="#1e2020"/>
            <!-- Left forearm -->
            <path d="M14,120 Q9,126 9,136 L10,160 Q11,165 14,165 L16,160 Q14,156 14,146 L14,124 Z" fill="#1e2020"/>
            <!-- Right forearm -->
            <path d="M106,120 Q111,126 111,136 L110,160 Q109,165 106,165 L104,160 Q106,156 106,146 L106,124 Z" fill="#1e2020"/>
            <!-- Left thigh -->
            <path d="M36,136 Q29,140 28,154 L28,208 Q30,216 40,218 Q50,216 52,208 L52,154 Q51,140 46,136 Z" fill="#1e2020"/>
            <!-- Right thigh -->
            <path d="M84,136 Q91,140 92,154 L92,208 Q90,216 80,218 Q70,216 68,208 L68,154 Q69,140 74,136 Z" fill="#1e2020"/>
            <!-- Knee caps -->
            <ellipse cx="40" cy="220" rx="12" ry="6" fill="#1e2020"/>
            <ellipse cx="80" cy="220" rx="12" ry="6" fill="#1e2020"/>
            <!-- Left lower leg (tapers to ankle) -->
            <path d="M29,222 Q26,234 28,252 L30,270 Q33,278 40,280 Q47,278 50,270 L52,252 Q54,234 51,222 Z" fill="#1e2020"/>
            <!-- Right lower leg -->
            <path d="M91,222 Q94,234 92,252 L90,270 Q87,278 80,280 Q73,278 70,270 L68,252 Q66,234 69,222 Z" fill="#1e2020"/>
            <!-- Feet -->
            <ellipse cx="40" cy="284" rx="13" ry="7" fill="#1e2020"/>
            <ellipse cx="80" cy="284" rx="13" ry="7" fill="#1e2020"/>

            <!-- === FRONT MUSCLE OVERLAYS === -->

            <!-- Chest / Pectorals — fan shape from sternum outward -->
            <path d="M55,58 Q43,56 35,62 Q29,70 31,84 Q34,94 44,96 Q54,96 57,86 Q59,76 57,64 Z"
                  fill={color('chest')} opacity="0.85"/>
            <path d="M65,58 Q77,56 85,62 Q91,70 89,84 Q86,94 76,96 Q66,96 63,86 Q61,76 63,64 Z"
                  fill={color('chest')} opacity="0.85"/>

            <!-- Shoulders / Anterior deltoid — rounded cap -->
            <path d="M16,52 Q14,44 20,42 Q27,40 29,48 Q31,58 27,64 Q22,66 18,62 Q15,58 16,54 Z"
                  fill={color('shoulders')} opacity="0.85"/>
            <path d="M104,52 Q106,44 100,42 Q93,40 91,48 Q89,58 93,64 Q98,66 102,62 Q105,58 104,54 Z"
                  fill={color('shoulders')} opacity="0.85"/>

            <!-- Biceps — teardrop on anterior upper arm -->
            <path d="M11,70 Q8,80 8,96 Q9,110 13,116 Q15,118 16,114 Q17,106 16,90 Q15,74 12,70 Z"
                  fill={color('biceps')} opacity="0.85"/>
            <path d="M109,70 Q112,80 112,96 Q111,110 107,116 Q105,118 104,114 Q103,106 104,90 Q105,74 108,70 Z"
                  fill={color('biceps')} opacity="0.85"/>

            <!-- Abs — 3 pairs with curved borders and slight narrowing toward bottom -->
            <path d="M37,92 Q39,90 44,90 Q49,90 51,92 L51,103 Q49,105 44,105 Q39,105 37,103 Z"
                  fill={color('abs')} opacity="0.85"/>
            <path d="M69,92 Q71,90 76,90 Q81,90 83,92 L83,103 Q81,105 76,105 Q71,105 69,103 Z"
                  fill={color('abs')} opacity="0.85"/>
            <path d="M37,107 Q39,105 44,105 Q49,105 51,107 L51,118 Q49,120 44,120 Q39,120 37,118 Z"
                  fill={color('abs')} opacity="0.85"/>
            <path d="M69,107 Q71,105 76,105 Q81,105 83,107 L83,118 Q81,120 76,120 Q71,120 69,118 Z"
                  fill={color('abs')} opacity="0.85"/>
            <path d="M38,122 Q40,120 44,120 Q48,120 50,122 L50,131 Q48,133 44,133 Q40,133 38,131 Z"
                  fill={color('abs')} opacity="0.85"/>
            <path d="M70,122 Q72,120 76,120 Q80,120 82,122 L82,131 Q80,133 76,133 Q72,133 70,131 Z"
                  fill={color('abs')} opacity="0.85"/>

            <!-- Quads — sweep shape with VMO teardrop at inner knee -->
            <path d="M30,152 Q28,164 28,182 Q29,202 32,210 Q35,217 40,218 Q45,217 49,210 Q52,200 52,182 Q52,164 50,152 Q46,145 40,145 Q34,145 30,152 Z"
                  fill={color('quads')} opacity="0.85"/>
            <ellipse cx="33" cy="212" rx="5" ry="6" transform="rotate(-12,33,212)"
                     fill={color('quads')} opacity="0.85"/>
            <path d="M90,152 Q92,164 92,182 Q91,202 88,210 Q85,217 80,218 Q75,217 71,210 Q68,200 68,182 Q68,164 70,152 Q74,145 80,145 Q86,145 90,152 Z"
                  fill={color('quads')} opacity="0.85"/>
            <ellipse cx="87" cy="212" rx="5" ry="6" transform="rotate(12,87,212)"
                     fill={color('quads')} opacity="0.85"/>

            <!-- Calves — gastrocnemius belly tapers to ankle -->
            <path d="M30,224 Q27,236 28,252 Q30,268 38,274 Q42,276 47,272 Q51,262 51,248 Q52,232 50,224 Q46,220 40,220 Q33,220 30,224 Z"
                  fill={color('calves')} opacity="0.85"/>
            <path d="M90,224 Q93,236 92,252 Q90,268 82,274 Q78,276 73,272 Q69,262 69,248 Q68,232 70,224 Q74,220 80,220 Q87,220 90,224 Z"
                  fill={color('calves')} opacity="0.85"/>
          </svg>
        </div>

        <!-- Back view -->
        <div class="diagram-wrap">
          <div class="diagram-label">Back</div>
          <svg viewBox="0 0 120 298" xmlns="http://www.w3.org/2000/svg">
            <!-- === BODY SILHOUETTE (identical to front) === -->
            <ellipse cx="60" cy="17" rx="13" ry="14" fill="#1e2020"/>
            <path d="M54,29 Q55,36 54,41 L66,41 Q65,36 66,29 Z" fill="#1e2020"/>
            <path d="M20,44 L100,44 Q106,50 104,58 L100,64 Q92,90 96,118 Q92,132 84,134 L36,134 Q28,132 24,118 Q28,90 20,64 L16,58 Q14,50 20,44 Z" fill="#1e2020"/>
            <path d="M16,52 Q10,58 9,70 L9,112 Q10,118 14,120 Q16,118 17,114 L18,70 Q18,60 20,54 Z" fill="#1e2020"/>
            <path d="M104,52 Q110,58 111,70 L111,112 Q110,118 106,120 Q104,118 103,114 L102,70 Q102,60 100,54 Z" fill="#1e2020"/>
            <path d="M14,120 Q9,126 9,136 L10,160 Q11,165 14,165 L16,160 Q14,156 14,146 L14,124 Z" fill="#1e2020"/>
            <path d="M106,120 Q111,126 111,136 L110,160 Q109,165 106,165 L104,160 Q106,156 106,146 L106,124 Z" fill="#1e2020"/>
            <path d="M36,136 Q29,140 28,154 L28,208 Q30,216 40,218 Q50,216 52,208 L52,154 Q51,140 46,136 Z" fill="#1e2020"/>
            <path d="M84,136 Q91,140 92,154 L92,208 Q90,216 80,218 Q70,216 68,208 L68,154 Q69,140 74,136 Z" fill="#1e2020"/>
            <ellipse cx="40" cy="220" rx="12" ry="6" fill="#1e2020"/>
            <ellipse cx="80" cy="220" rx="12" ry="6" fill="#1e2020"/>
            <path d="M29,222 Q26,234 28,252 L30,270 Q33,278 40,280 Q47,278 50,270 L52,252 Q54,234 51,222 Z" fill="#1e2020"/>
            <path d="M91,222 Q94,234 92,252 L90,270 Q87,278 80,280 Q73,278 70,270 L68,252 Q66,234 69,222 Z" fill="#1e2020"/>
            <ellipse cx="40" cy="284" rx="13" ry="7" fill="#1e2020"/>
            <ellipse cx="80" cy="284" rx="13" ry="7" fill="#1e2020"/>

            <!-- === BACK MUSCLE OVERLAYS === -->

            <!-- Lats — wing shape from armpit down to lower back (render first, under traps) -->
            <path d="M24,64 Q20,74 20,90 Q21,112 26,124 Q30,132 38,134 Q47,134 52,122 Q55,110 53,90 Q51,72 42,64 Q36,60 28,60 Z"
                  fill={color('lats')} opacity="0.85"/>
            <path d="M96,64 Q100,74 100,90 Q99,112 94,124 Q90,132 82,134 Q73,134 68,122 Q65,110 67,90 Q69,72 78,64 Q84,60 92,60 Z"
                  fill={color('lats')} opacity="0.85"/>

            <!-- Mid back / rhomboids — between lats -->
            <path d="M46,66 Q52,62 60,62 Q68,62 74,66 Q78,74 76,88 Q68,94 60,95 Q52,94 44,88 Q42,74 46,66 Z"
                  fill={color('back')} opacity="0.85"/>

            <!-- Trapezius — diamond from neck base outward, sits on top -->
            <path d="M60,42 Q74,44 84,52 Q90,62 84,72 Q74,78 60,80 Q46,78 36,72 Q30,62 36,52 Q46,44 60,42 Z"
                  fill={color('traps')} opacity="0.85"/>

            <!-- Triceps — posterior upper arm -->
            <path d="M11,68 Q8,78 8,96 Q9,112 13,118 Q15,120 17,116 Q18,108 17,90 Q16,74 13,68 Z"
                  fill={color('triceps')} opacity="0.85"/>
            <path d="M109,68 Q112,78 112,96 Q111,112 107,118 Q105,120 103,116 Q102,108 103,90 Q104,74 107,68 Z"
                  fill={color('triceps')} opacity="0.85"/>

            <!-- Glutes — rounded posterior hip -->
            <path d="M29,140 Q27,152 30,165 Q33,174 42,176 Q51,174 54,165 Q57,152 52,140 Q46,134 38,135 Q32,136 29,140 Z"
                  fill={color('glutes')} opacity="0.85"/>
            <path d="M91,140 Q93,152 90,165 Q87,174 78,176 Q69,174 66,165 Q63,152 68,140 Q74,134 82,135 Q88,136 91,140 Z"
                  fill={color('glutes')} opacity="0.85"/>

            <!-- Hamstrings — two-lobe posterior thigh -->
            <path d="M29,170 Q27,182 27,200 Q29,214 40,218 Q44,219 48,216 Q52,210 52,196 Q52,178 50,168 Q46,162 40,162 Q32,164 29,170 Z"
                  fill={color('hamstrings')} opacity="0.85"/>
            <path d="M91,170 Q93,182 93,200 Q91,214 80,218 Q76,219 72,216 Q68,210 68,196 Q68,178 70,168 Q74,162 80,162 Q88,164 91,170 Z"
                  fill={color('hamstrings')} opacity="0.85"/>

            <!-- Calves — gastrocnemius two-head shape -->
            <path d="M29,224 Q26,236 28,254 Q30,270 38,276 Q42,278 47,274 Q51,264 51,250 Q51,234 49,224 Q45,220 40,220 Q33,220 29,224 Z"
                  fill={color('calves')} opacity="0.85"/>
            <path d="M91,224 Q94,236 92,254 Q90,270 82,276 Q78,278 73,274 Q69,264 69,250 Q69,234 71,224 Q75,220 80,220 Q87,220 91,224 Z"
                  fill={color('calves')} opacity="0.85"/>
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
    width: 150px;
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
