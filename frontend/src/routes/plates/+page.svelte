<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let mode = 'barbell'; // 'barbell' | 'cable' | 'percent'
  let unit = 'lbs';

  // ── Plate definitions ───────────────────────────────────────────────────────
  const PLATES_LBS = [
    { weight: 45,   color: '#c0392b', label: '45' },
    { weight: 35,   color: '#f39c12', label: '35' },
    { weight: 25,   color: '#27ae60', label: '25' },
    { weight: 10,   color: '#ddd',    label: '10', textColor: '#333' },
    { weight: 5,    color: '#2980b9', label: '5' },
    { weight: 2.5,  color: '#444',    label: '2.5' },
    { weight: 1.25, color: '#888',    label: '1.25' },
  ];
  const PLATES_KG = [
    { weight: 20,   color: '#c0392b', label: '20' },
    { weight: 15,   color: '#f39c12', label: '15' },
    { weight: 10,   color: '#27ae60', label: '10' },
    { weight: 5,    color: '#ddd',    label: '5', textColor: '#333' },
    { weight: 2.5,  color: '#2980b9', label: '2.5' },
    { weight: 1.25, color: '#444',    label: '1.25' },
    { weight: 0.5,  color: '#888',    label: '0.5' },
  ];

  const BAR_OPTIONS_LBS = [
    { label: '45 lb (Olympic)', value: 45 },
    { label: "35 lb (Women's)", value: 35 },
    { label: '25 lb (Junior)',  value: 25 },
    { label: '15 lb (Trainer)', value: 15 },
  ];
  const BAR_OPTIONS_KG = [
    { label: '20 kg (Olympic)', value: 20 },
    { label: "15 kg (Women's)", value: 15 },
    { label: '10 kg (Junior)',  value: 10 },
    { label: '5 kg (Trainer)',  value: 5 },
  ];

  const STACK_OPTIONS_LBS = [5, 10, 15, 20];
  const STACK_OPTIONS_KG  = [2.5, 5, 7.5, 10];

  $: plateOptions      = unit === 'lbs' ? PLATES_LBS : PLATES_KG;
  $: barOptions        = unit === 'lbs' ? BAR_OPTIONS_LBS : BAR_OPTIONS_KG;
  $: stackPlateOptions = unit === 'lbs' ? STACK_OPTIONS_LBS : STACK_OPTIONS_KG;

  // ── Barbell state ────────────────────────────────────────────────────────────
  let barWeight   = 45;
  let targetWeight = '';
  let result = null;

  // plate counts: total owned per weight (0 = don't have it)
  let plateCounts = Object.fromEntries(PLATES_LBS.map(p => [p.weight, 0]));

  function initCounts(plates) {
    plateCounts = Object.fromEntries(plates.map(p => [p.weight, 0]));
    result = null;
  }

  function setCount(weight, delta) {
    plateCounts = { ...plateCounts, [weight]: Math.max(0, (plateCounts[weight] ?? 0) + delta) };
    if (targetWeight) calculate();
    persistInventory();
  }

  function switchUnit(u) {
    unit = u;
    barWeight = (u === 'lbs' ? BAR_OPTIONS_LBS : BAR_OPTIONS_KG)[0].value;
    stackPlateWeight = (u === 'lbs' ? STACK_OPTIONS_LBS : STACK_OPTIONS_KG)[1];
    initCounts(u === 'lbs' ? PLATES_LBS : PLATES_KG);
    cableResult = null;
    if (targetWeight) calculate();
    if (cableTarget) calculateCable();
  }

  let persistTimer = null;
  function persistInventory() {
    clearTimeout(persistTimer);
    persistTimer = setTimeout(async () => {
      try {
        const barbell = Object.fromEntries(Object.entries(plateCounts).map(([w, cnt]) => [String(w), cnt]));
        await api.profile.update({ plate_inventory: { barbell } });
      } catch (_) {}
    }, 1200);
  }

  onMount(async () => {
    try {
      const profile = await api.profile.get();
      if (profile.unit_preference && profile.unit_preference !== unit) {
        switchUnit(profile.unit_preference);
      }
      const inv = profile.plate_inventory || {};
      const barbellInv = inv.barbell || {};
      const current = { ...plateCounts };
      for (const [w, cnt] of Object.entries(barbellInv)) {
        const numW = parseFloat(w);
        if (numW in current) current[numW] = cnt;
      }
      plateCounts = current;
      if (targetWeight) calculate();
    } catch (_) {}
  });

  function greedySolve(remaining, plates, limits = null) {
    const used = [];
    const usedCount = {};
    let rem = remaining;
    for (const plate of plates) {
      const max = limits ? (limits[plate.weight] ?? Infinity) : Infinity;
      usedCount[plate.weight] = 0;
      while (rem >= plate.weight - 0.001 && usedCount[plate.weight] < max) {
        used.push(plate);
        rem -= plate.weight;
        rem = Math.round(rem * 1000) / 1000;
        usedCount[plate.weight]++;
      }
    }
    return { plates: used, remainder: rem };
  }

  function calculate() {
    const target = parseFloat(targetWeight);
    if (!target || target <= 0 || target <= barWeight) { result = null; return; }

    const perSide  = (target - barWeight) / 2;
    const available = plateOptions
      .filter(p => (plateCounts[p.weight] ?? 0) > 0)
      .sort((a, b) => b.weight - a.weight);

    if (!available.length) { result = null; return; }

    const limits = {};
    for (const p of available) limits[p.weight] = Math.floor((plateCounts[p.weight] ?? 0) / 2);

    const exact = greedySolve(perSide, available, limits);

    let below = null, above = null;
    if (exact.remainder > 0.001) {
      const { plates: bp } = greedySolve(perSide - exact.remainder, available, limits);
      below = { plates: bp, total: barWeight + bp.reduce((s, p) => s + p.weight, 0) * 2 };

      const smallest = available[available.length - 1];
      if (smallest) {
        const { plates: ap } = greedySolve(perSide - exact.remainder + smallest.weight, available, limits);
        above = { plates: ap, total: barWeight + ap.reduce((s, p) => s + p.weight, 0) * 2 };
      }
    }

    result = {
      target, perSide,
      exact: exact.remainder < 0.001 ? exact.plates : null,
      below, above,
      isExact: exact.remainder < 0.001,
    };
  }

  function plateBreakdown(plates) {
    const counts = {};
    for (const p of plates) counts[p.weight] = (counts[p.weight] || 0) + 1;
    return Object.entries(counts).map(([w, n]) => n > 1 ? `${n}×${w}` : `${w}`).join(' + ');
  }

  function plateForWeight(w) {
    return plateOptions.find(p => p.weight === w) || { color: '#555', label: String(w), weight: w };
  }

  $: displayPlates = result?.isExact ? result.exact : (result?.below?.plates || []);

  // ── Cable machine state ──────────────────────────────────────────────────────
  let stackPlateWeight = 10;
  let numStackPlates   = 20;
  let pulleyRatio      = 2;   // 1 = two-arm (1:1), 2 = single arm (2:1)
  let cableTarget      = '';
  let cableResult      = null;

  $: totalCapacity     = stackPlateWeight * numStackPlates;
  $: resistancePerPlate = stackPlateWeight / pulleyRatio;
  $: maxResistance     = totalCapacity / pulleyRatio;

  // ── 1RM % state ─────────────────────────────────────────────────────────────
  let pctOneRM = '';
  const PCT_ROWS = [100, 97.5, 95, 92.5, 90, 87.5, 85, 82.5, 80, 77.5, 75, 70, 65, 60, 55, 50];

  function round25(v) { return Math.round(v / 2.5) * 2.5; }

  $: pctTable = (() => {
    const max = parseFloat(pctOneRM);
    if (!max || max <= 0) return [];
    return PCT_ROWS.map(pct => ({
      pct,
      exact: max * pct / 100,
      rounded: round25(max * pct / 100),
    }));
  })();

  function calculateCable() {
    const target = parseFloat(cableTarget);
    if (!target || target <= 0) { cableResult = null; return; }

    if (target > maxResistance) {
      cableResult = { overCapacity: true, maxResistance };
      return;
    }

    const exactPlates = target / resistancePerPlate;
    const floorP = Math.floor(exactPlates);
    const ceilP  = Math.ceil(exactPlates);

    if (Math.abs(exactPlates - Math.round(exactPlates)) < 0.001) {
      cableResult = { isExact: true, plates: Math.round(exactPlates), resistance: target };
    } else {
      cableResult = {
        isExact: false,
        below: { plates: floorP, resistance: Math.round(floorP * resistancePerPlate * 10) / 10 },
        above: ceilP <= numStackPlates
          ? { plates: ceilP, resistance: Math.round(ceilP * resistancePerPlate * 10) / 10 }
          : null,
      };
    }
  }
</script>

<svelte:head><title>Plate Calculator — LiftForge</title></svelte:head>

<div class="page">
  <h2>Plate Calculator</h2>

  <!-- Mode tabs -->
  <div class="tabs">
    <button class="tab" class:active={mode === 'barbell'} on:click={() => mode = 'barbell'}>
      Barbell
    </button>
    <button class="tab" class:active={mode === 'cable'} on:click={() => mode = 'cable'}>
      Cable Machine
    </button>
    <button class="tab" class:active={mode === 'percent'} on:click={() => mode = 'percent'}>
      1RM %
    </button>
  </div>

  <!-- Unit toggle -->
  <div class="unit-row">
    <button class="unit-btn" class:active={unit === 'lbs'} on:click={() => switchUnit('lbs')}>lbs</button>
    <button class="unit-btn" class:active={unit === 'kg'}  on:click={() => switchUnit('kg')}>kg</button>
  </div>

  <!-- ── BARBELL MODE ─────────────────────────────────────────────────────── -->
  {#if mode === 'barbell'}
    <div class="card">
      <div class="row-inputs">
        <div class="field">
          <label for="tw">Target Weight ({unit})</label>
          <input id="tw" type="number" min="0"
            step={unit === 'lbs' ? 2.5 : 1.25}
            bind:value={targetWeight}
            on:input={calculate}
            placeholder="e.g. 185"
            style="font-size:20px; font-weight:700;"
          />
        </div>
        <div class="field">
          <label for="bw">Bar Weight</label>
          <select id="bw" bind:value={barWeight} on:change={calculate}>
            {#each barOptions as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        </div>
      </div>

      <!-- Plate inventory -->
      <div class="section-title">Your Plates ({unit}) — tap to set count</div>
      <div class="plate-grid">
        {#each plateOptions as plate}
          {@const count = plateCounts[plate.weight] ?? 0}
          {@const active = count > 0}
          <div class="plate-item">
            <div class="plate-circle" style="
              border-color: {active ? plate.color : 'var(--border-2)'};
              background:   {active ? plate.color : 'var(--surface-2)'};
              color:        {active ? (plate.textColor || '#fff') : 'var(--text-muted)'};
            ">
              {plate.label}
            </div>
            <div class="stepper">
              <button class="step-btn" on:click={() => setCount(plate.weight, -1)} aria-label="Remove">−</button>
              <span class="step-val" style="color:{active ? 'var(--text)' : 'var(--text-muted)'}">{count}</span>
              <button class="step-btn" on:click={() => setCount(plate.weight, 1)} aria-label="Add">+</button>
            </div>
          </div>
        {/each}
      </div>
    </div>

    <!-- Barbell result -->
    {#if targetWeight && parseFloat(targetWeight) <= barWeight}
      <div class="card muted-note">Target must be greater than bar weight ({barWeight} {unit}).</div>
    {:else if result && targetWeight}
      <div class="card">
        {#if result.isExact}
          <div class="exact-label">Exact match</div>
          <div class="result-weight">{result.perSide} {unit} per side</div>
          <div class="result-sub">{plateBreakdown(result.exact)} = {result.perSide} {unit}</div>

          <!-- Visual bar diagram -->
          <div class="bar-diagram">
            <div class="bar-collar"></div>
            <div class="bar-end"></div>
            {#each [...result.exact].reverse() as plate}
              {@const pd = plateForWeight(plate.weight)}
              <div class="bar-plate" style="
                width: {Math.max(14, Math.round(plate.weight / plateOptions[0].weight * 44))}px;
                height:{Math.max(32, Math.round(plate.weight / plateOptions[0].weight * 72))}px;
                background:{pd.color};
                color:{pd.textColor || '#fff'};
              ">{pd.label}</div>
            {/each}
            <div class="bar-sleeve"></div>
            <div class="bar-cap"></div>
          </div>

        {:else}
          <div class="muted-note" style="margin-bottom:14px;">
            Can't hit {result.target} {unit} exactly with your plates.
          </div>
          <div class="nearest-row">
            {#if result.below}
              <div class="nearest-card">
                <div class="nearest-label">Below</div>
                <div class="nearest-weight">{result.below.total} {unit}</div>
                <div class="nearest-sub">
                  {result.below.plates.length > 0 ? plateBreakdown(result.below.plates) + ' per side' : 'Just the bar'}
                </div>
              </div>
            {/if}
            {#if result.above}
              <div class="nearest-card">
                <div class="nearest-label">Above</div>
                <div class="nearest-weight">{result.above.total} {unit}</div>
                <div class="nearest-sub">{plateBreakdown(result.above.plates)} per side</div>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    {/if}
  {/if}

  <!-- ── CABLE MACHINE MODE ──────────────────────────────────────────────── -->
  {#if mode === 'cable'}
    <div class="card">
      <!-- Stack setup -->
      <div class="section-title">Machine Setup</div>
      <div class="cable-setup">
        <div class="field">
          <label>Stack Plate Weight ({unit})</label>
          <div class="chip-row">
            {#each stackPlateOptions as opt}
              <button
                class="chip"
                class:active={stackPlateWeight === opt}
                on:click={() => { stackPlateWeight = opt; calculateCable(); }}
              >{opt}</button>
            {/each}
          </div>
        </div>

        <div class="field">
          <label>Number of Plates</label>
          <div class="inline-stepper">
            <button class="step-btn lg" on:click={() => { numStackPlates = Math.max(1, numStackPlates - 1); calculateCable(); }}>−</button>
            <span class="step-val lg">{numStackPlates}</span>
            <button class="step-btn lg" on:click={() => { numStackPlates += 1; calculateCable(); }}>+</button>
            <span class="capacity-label">= {totalCapacity} {unit} total stack</span>
          </div>
        </div>

        <div class="field">
          <label>Exercise Type</label>
          <div class="chip-row">
            <button class="chip" class:active={pulleyRatio === 1}
              on:click={() => { pulleyRatio = 1; calculateCable(); }}>
              Two-arm (1:1)
            </button>
            <button class="chip" class:active={pulleyRatio === 2}
              on:click={() => { pulleyRatio = 2; calculateCable(); }}>
              Single arm (2:1)
            </button>
          </div>
          <div class="hint">
            {#if pulleyRatio === 2}
              {stackPlateWeight} {unit} plates → {resistancePerPlate} {unit} increments at the handle · max {maxResistance} {unit}
            {:else}
              {stackPlateWeight} {unit} plates → {resistancePerPlate} {unit} increments · max {maxResistance} {unit}
            {/if}
          </div>
        </div>
      </div>

      <!-- Target input -->
      <div class="field" style="margin-top:4px;">
        <label for="ct">Target Resistance ({unit})</label>
        <input id="ct" type="number" min="0"
          step={resistancePerPlate}
          bind:value={cableTarget}
          on:input={calculateCable}
          placeholder="e.g. 65"
          style="font-size:20px; font-weight:700;"
        />
      </div>
    </div>

    <!-- Cable result -->
    {#if cableResult}
      <div class="card">
        {#if cableResult.overCapacity}
          <div style="color:var(--danger); font-size:13px;">
            Exceeds machine capacity ({cableResult.maxResistance} {unit} max).
          </div>
        {:else if cableResult.isExact}
          <div class="exact-label">Exact match</div>
          <div class="result-weight">{cableResult.plates} plates</div>
          <div class="result-sub">{cableResult.plates} × {stackPlateWeight} {unit} ÷ {pulleyRatio} = {cableResult.resistance} {unit} at handle</div>
        {:else}
          <div class="muted-note" style="margin-bottom:14px;">
            {parseFloat(cableTarget)} {unit} isn't a exact stack setting — nearest options:
          </div>
          <div class="nearest-row">
            {#if cableResult.below}
              <div class="nearest-card">
                <div class="nearest-label">Below</div>
                <div class="nearest-weight">{cableResult.below.resistance} {unit}</div>
                <div class="nearest-sub">{cableResult.below.plates} plates on the stack</div>
              </div>
            {/if}
            {#if cableResult.above}
              <div class="nearest-card">
                <div class="nearest-label">Above</div>
                <div class="nearest-weight">{cableResult.above.resistance} {unit}</div>
                <div class="nearest-sub">{cableResult.above.plates} plates on the stack</div>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    {/if}
  {/if}

  <!-- ── 1RM % Calculator ── -->
  {#if mode === 'percent'}
    <div style="margin-top:16px;">
      <div style="margin-bottom:20px;">
        <label style="font-size:13px; color:var(--text-muted); display:block; margin-bottom:8px;">Your 1RM ({unit})</label>
        <input
          type="number"
          bind:value={pctOneRM}
          placeholder="e.g. 225"
          style="font-size:28px; font-weight:800; width:160px;"
        />
      </div>

      {#if pctTable.length}
        <div class="pct-table">
          <div class="pct-header">
            <span>%</span>
            <span>Weight</span>
            <span style="color:var(--text-faint); font-size:10px;">Rounded 2.5</span>
          </div>
          {#each pctTable as row}
            <div class="pct-row" class:pct-key={[100,90,80,70,60].includes(row.pct)}>
              <span class="pct-label">{row.pct}%</span>
              <span class="pct-val">{row.rounded} <span style="font-size:11px; color:var(--text-muted);">{unit}</span></span>
              <span style="font-size:11px; color:var(--text-faint);">{row.exact.toFixed(1)}</span>
            </div>
          {/each}
        </div>
      {:else}
        <div style="font-size:13px; color:var(--text-faint); padding:8px 0;">Enter your 1RM to see the percentage table.</div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .page {
    max-width: 640px;
    padding: 1.5rem;
  }

  h2 {
    font-size: 1.25rem;
    font-weight: 700;
    margin: 0 0 1.25rem;
    color: var(--text);
  }

  /* ── Tabs ── */
  .tabs {
    display: flex;
    gap: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 3px;
    margin-bottom: 1rem;
    width: 100%;
  }

  .tab {
    flex: 1;
    padding: 8px 0;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--text-muted);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }

  .tab.active {
    background: var(--primary);
    color: #000;
    font-weight: 700;
  }

  /* ── Unit toggle ── */
  .unit-row {
    display: flex;
    gap: 8px;
    margin-bottom: 1rem;
  }

  .unit-btn {
    padding: 6px 20px;
    border-radius: var(--radius);
    border: 2px solid var(--border);
    background: var(--surface-2);
    color: var(--text-muted);
    font-weight: 400;
    cursor: pointer;
    transition: all 0.15s;
  }

  .unit-btn.active {
    border-color: var(--primary);
    background: rgba(232,160,64,0.12);
    color: var(--primary);
    font-weight: 700;
  }

  /* ── Card / fields ── */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.25rem;
    margin-bottom: 1rem;
  }

  .row-inputs {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 1.25rem;
  }

  .field {
    flex: 1;
    min-width: 140px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  label {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  input, select {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    padding: 8px 12px;
    font-size: 0.875rem;
    width: 100%;
    box-sizing: border-box;
  }

  .section-title {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.75rem;
  }

  /* ── Plate grid ── */
  .plate-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .plate-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }

  .plate-circle {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    border: 3px solid;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    transition: all 0.15s;
    user-select: none;
  }

  .stepper {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .step-btn {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: 1px solid var(--border-2);
    background: var(--surface-2);
    color: var(--text);
    font-size: 14px;
    line-height: 1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    transition: background 0.1s;
  }

  .step-btn:active { background: var(--border); }

  .step-btn.lg {
    width: 30px;
    height: 30px;
    font-size: 16px;
  }

  .step-val {
    font-size: 13px;
    font-weight: 600;
    min-width: 18px;
    text-align: center;
  }

  .step-val.lg {
    font-size: 18px;
    min-width: 32px;
  }

  /* ── Barbell result ── */
  .exact-label {
    color: var(--success);
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 6px;
  }

  .result-weight {
    font-size: 24px;
    font-weight: 700;
    color: var(--primary);
    margin-bottom: 4px;
  }

  .result-sub {
    color: var(--text-muted);
    font-size: 13px;
    margin-bottom: 14px;
  }

  .bar-diagram {
    display: flex;
    align-items: center;
    overflow-x: auto;
    padding: 8px 0;
    gap: 0;
  }

  .bar-collar { width: 12px; height: 48px; background: var(--border-2); border-radius: 2px 0 0 2px; flex-shrink: 0; }
  .bar-end    { width: 30px; height: 16px; background: var(--border-2); flex-shrink: 0; }
  .bar-sleeve { width: 60px; height: 12px; background: var(--border-2); flex-shrink: 0; }
  .bar-cap    { width: 8px;  height: 20px; background: var(--border-2); border-radius: 0 2px 2px 0; flex-shrink: 0; }

  .bar-plate {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    writing-mode: vertical-rl;
    text-orientation: mixed;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 3px;
  }

  .nearest-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .nearest-card {
    flex: 1;
    min-width: 150px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 14px;
  }

  .nearest-label {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
  }

  .nearest-weight {
    font-size: 20px;
    font-weight: 700;
    color: var(--text);
  }

  .nearest-sub {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
  }

  .muted-note {
    color: var(--text-muted);
    font-size: 13px;
  }

  /* ── Cable machine ── */
  .cable-setup {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    margin-bottom: 1.25rem;
  }

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .chip {
    padding: 6px 14px;
    border-radius: var(--radius);
    border: 1px solid var(--border-2);
    background: var(--surface-2);
    color: var(--text-muted);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .chip.active {
    border-color: var(--primary);
    background: rgba(232,160,64,0.12);
    color: var(--primary);
    font-weight: 600;
  }

  .inline-stepper {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .capacity-label {
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .hint {
    font-size: 0.78rem;
    color: var(--text-muted);
    margin-top: 2px;
  }

  @media (max-width: 480px) {
    .page { padding: 1rem; }
    .plate-grid { gap: 10px; }
    .plate-circle { width: 46px; height: 46px; font-size: 10px; }
  }

  /* 1RM % table */
  .pct-table { display: flex; flex-direction: column; border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; }
  .pct-header {
    display: grid; grid-template-columns: 70px 1fr 80px;
    padding: 8px 14px; background: var(--surface-2);
    font-size: 11px; color: var(--text-muted); font-weight: 600; text-transform: uppercase;
  }
  .pct-row {
    display: grid; grid-template-columns: 70px 1fr 80px;
    padding: 9px 14px; border-top: 1px solid var(--border);
    font-size: 13px; align-items: center;
  }
  .pct-row.pct-key { background: rgba(232,160,64,0.05); }
  .pct-label { color: var(--text-muted); font-weight: 600; }
  .pct-val { font-size: 16px; font-weight: 700; color: var(--text); }
</style>
