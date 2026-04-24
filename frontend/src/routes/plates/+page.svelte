<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let unit = 'lbs';
  let targetWeight = '';
  let barWeight = 45;
  let result = null;

  const BAR_OPTIONS_LBS = [
    { label: '45 lb (Olympic)', value: 45 },
    { label: '35 lb (Women\'s)', value: 35 },
    { label: '25 lb (Junior)', value: 25 },
    { label: '15 lb (Trainer)', value: 15 },
  ];

  const BAR_OPTIONS_KG = [
    { label: '20 kg (Olympic)', value: 20 },
    { label: '15 kg (Women\'s)', value: 15 },
    { label: '10 kg (Junior)', value: 10 },
    { label: '5 kg (Trainer)', value: 5 },
  ];

  const PLATES_LBS = [
    { weight: 45,   color: '#c0392b', label: '45' },
    { weight: 35,   color: '#f39c12', label: '35' },
    { weight: 25,   color: '#27ae60', label: '25' },
    { weight: 10,   color: '#ddd',    label: '10', textColor: '#333' },
    { weight: 5,    color: '#2980b9', label: '5' },
    { weight: 2.5,  color: '#333',    label: '2.5' },
    { weight: 1.25, color: '#999',    label: '1.25' },
  ];

  const PLATES_KG = [
    { weight: 20,   color: '#c0392b', label: '20' },
    { weight: 15,   color: '#f39c12', label: '15' },
    { weight: 10,   color: '#27ae60', label: '10' },
    { weight: 5,    color: '#ddd',    label: '5',  textColor: '#333' },
    { weight: 2.5,  color: '#2980b9', label: '2.5' },
    { weight: 1.25, color: '#333',    label: '1.25' },
    { weight: 0.5,  color: '#999',    label: '0.5' },
  ];

  $: plateOptions = unit === 'lbs' ? PLATES_LBS : PLATES_KG;
  $: barOptions = unit === 'lbs' ? BAR_OPTIONS_LBS : BAR_OPTIONS_KG;

  // Which plates the user has available
  let availablePlates = new Set(PLATES_LBS.map(p => p.weight));

  function switchUnit(newUnit) {
    unit = newUnit;
    barWeight = (newUnit === 'lbs' ? BAR_OPTIONS_LBS : BAR_OPTIONS_KG)[0].value;
    availablePlates = new Set((newUnit === 'lbs' ? PLATES_LBS : PLATES_KG).map(p => p.weight));
    result = null;
    if (targetWeight) calculate();
  }

  onMount(async () => {
    try {
      const profile = await api.profile.get();
      if (profile.unit_preference && profile.unit_preference !== unit) {
        switchUnit(profile.unit_preference);
      }
    } catch (e) {
      // graceful fallback
    }
  });

  function togglePlate(weight) {
    const s = new Set(availablePlates);
    if (s.has(weight)) s.delete(weight); else s.add(weight);
    availablePlates = s;
    if (targetWeight) calculate();
  }

  function calculate() {
    const target = parseFloat(targetWeight);
    if (!target || target <= 0 || target <= barWeight) {
      result = null;
      return;
    }

    const perSide = (target - barWeight) / 2;
    const available = plateOptions
      .filter(p => availablePlates.has(p.weight))
      .sort((a, b) => b.weight - a.weight);

    function greedySolve(remaining, plates) {
      const used = [];
      let rem = remaining;
      for (const plate of plates) {
        while (rem >= plate.weight - 0.001) {
          used.push(plate);
          rem -= plate.weight;
          rem = Math.round(rem * 1000) / 1000;
        }
      }
      return { plates: used, remainder: rem };
    }

    const exact = greedySolve(perSide, available);

    let below = null;
    let above = null;

    if (exact.remainder > 0.001) {
      // Try rounding down: remove last plate that makes it over
      const { plates: belowPlates } = greedySolve(perSide - exact.remainder, available);
      const belowTotal = barWeight + belowPlates.reduce((s, p) => s + p.weight, 0) * 2;
      below = { plates: belowPlates, total: belowTotal };

      // Try rounding up: add smallest available plate
      const smallestAvailable = available[available.length - 1];
      if (smallestAvailable) {
        const aboveSide = perSide - exact.remainder + smallestAvailable.weight;
        const { plates: abovePlates } = greedySolve(aboveSide, available);
        const aboveTotal = barWeight + abovePlates.reduce((s, p) => s + p.weight, 0) * 2;
        above = { plates: abovePlates, total: aboveTotal };
      }
    }

    result = {
      target,
      perSide,
      exact: exact.remainder < 0.001 ? exact.plates : null,
      below,
      above,
      isExact: exact.remainder < 0.001,
    };
  }

  function plateBreakdown(plates) {
    const counts = {};
    for (const p of plates) {
      counts[p.weight] = (counts[p.weight] || 0) + 1;
    }
    return Object.entries(counts)
      .map(([w, n]) => n > 1 ? `${n}×${w}` : `${w}`)
      .join(' + ');
  }

  function plateForWeight(weight) {
    return plateOptions.find(p => p.weight === weight) || { color: '#555', label: String(weight), weight };
  }

  $: displayPlates = result?.isExact ? result.exact : (result?.below?.plates || []);
</script>

<svelte:head><title>Plate Calculator — LiftForge</title></svelte:head>

<div style="max-width:640px;">
  <h2 style="font-size:20px; font-weight:700; margin-bottom:24px;">Plate Calculator</h2>

  <div class="card mb-4">
    <!-- Unit toggle -->
    <div class="flex gap-2 mb-4">
      <button
        on:click={() => switchUnit('lbs')}
        style="padding:7px 20px; border-radius:4px; border:2px solid {unit === 'lbs' ? 'var(--primary)' : 'var(--border)'}; background:{unit === 'lbs' ? 'rgba(232,160,64,0.12)' : 'var(--surface-2)'}; color:{unit === 'lbs' ? 'var(--primary)' : 'var(--text-muted)'}; font-weight:{unit === 'lbs' ? '700' : '400'}; cursor:pointer; transition:all 0.15s;"
      >lbs</button>
      <button
        on:click={() => switchUnit('kg')}
        style="padding:7px 20px; border-radius:4px; border:2px solid {unit === 'kg' ? 'var(--primary)' : 'var(--border)'}; background:{unit === 'kg' ? 'rgba(232,160,64,0.12)' : 'var(--surface-2)'}; color:{unit === 'kg' ? 'var(--primary)' : 'var(--text-muted)'}; font-weight:{unit === 'kg' ? '700' : '400'}; cursor:pointer; transition:all 0.15s;"
      >kg</button>
    </div>

    <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;">
      <!-- Target weight -->
      <div style="flex:1; min-width:140px;">
        <label for="targetWeight">Target Weight ({unit})</label>
        <input
          id="targetWeight"
          type="number"
          min="0"
          step={unit === 'lbs' ? 2.5 : 1.25}
          bind:value={targetWeight}
          on:input={calculate}
          placeholder="e.g. 185"
          style="font-size:20px; font-weight:700; padding:10px 14px;"
        />
      </div>
      <!-- Bar weight -->
      <div style="flex:1; min-width:160px;">
        <label for="barWeight">Bar Weight</label>
        <select id="barWeight" bind:value={barWeight} on:change={calculate}>
          {#each barOptions as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
      </div>
    </div>

    <!-- Available plates -->
    <div class="section-title mb-2">Available Plates ({unit})</div>
    <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:20px;">
      {#each plateOptions as plate}
        <button
          on:click={() => togglePlate(plate.weight)}
          style="
            width:52px; height:52px; border-radius:50%; border:3px solid {availablePlates.has(plate.weight) ? plate.color : 'var(--border)'};
            background:{availablePlates.has(plate.weight) ? plate.color : 'var(--surface-2)'};
            color:{availablePlates.has(plate.weight) ? (plate.textColor || '#fff') : 'var(--text-muted)'};
            font-size:11px; font-weight:700; cursor:pointer; transition:all 0.15s;
            display:flex; align-items:center; justify-content:center;
          "
        >{plate.label}</button>
      {/each}
    </div>
  </div>

  <!-- Result -->
  {#if result && targetWeight}
    <div class="card">
      {#if result.isExact}
        <div style="color:var(--success); font-size:13px; font-weight:600; margin-bottom:12px;">Exact match</div>
        <div style="font-size:24px; font-weight:700; color:var(--primary); margin-bottom:4px;">
          {result.perSide} {unit} per side
        </div>
        <div style="color:var(--text-muted); font-size:13px; margin-bottom:16px;">
          {plateBreakdown(result.exact)} = {result.perSide} {unit}
        </div>

        <!-- Visual plate diagram -->
        <div style="display:flex; align-items:center; gap:0; margin-top:8px; overflow-x:auto; padding:8px 0;">
          <!-- Collar -->
          <div style="width:12px; height:48px; background:var(--border-2); border-radius:2px 0 0 2px; flex-shrink:0;"></div>
          <!-- Bar end -->
          <div style="width:30px; height:16px; background:var(--border-2); flex-shrink:0;"></div>
          <!-- Plates (outermost first = heaviest) -->
          {#each [...result.exact].reverse() as plate}
            {@const pd = plateForWeight(plate.weight)}
            <div style="
              width:{Math.max(14, Math.round(plate.weight / plateOptions[0].weight * 44))}px;
              height:{Math.max(32, Math.round(plate.weight / plateOptions[0].weight * 72))}px;
              background:{pd.color};
              border-radius:3px;
              flex-shrink:0;
              display:flex; align-items:center; justify-content:center;
              font-size:{plate.weight >= 10 ? 10 : 9}px;
              font-weight:700;
              color:{pd.textColor || '#fff'};
              writing-mode:vertical-rl;
              text-orientation:mixed;
              border:1px solid rgba(255,255,255,0.1);
            ">{pd.label}</div>
          {/each}
          <!-- Bar sleeve -->
          <div style="width:60px; height:12px; background:var(--border-2); flex-shrink:0;"></div>
          <!-- Sleeve cap -->
          <div style="width:8px; height:20px; background:var(--border-2); border-radius:0 2px 2px 0; flex-shrink:0;"></div>
        </div>

      {:else}
        <div style="color:var(--text-muted); font-size:13px; margin-bottom:16px;">
          Can't hit {result.target} {unit} exactly with available plates.
        </div>
        <div style="display:flex; gap:12px; flex-wrap:wrap;">
          {#if result.below}
            <div style="flex:1; min-width:180px; background:var(--surface-2); border-radius:var(--radius-lg); padding:14px; border:1px solid var(--border);">
              <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">Below</div>
              <div style="font-size:20px; font-weight:700; color:var(--text);">{result.below.total} {unit}</div>
              <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">
                {result.below.plates.length > 0 ? plateBreakdown(result.below.plates) + ' per side' : 'Just the bar'}
              </div>
            </div>
          {/if}
          {#if result.above}
            <div style="flex:1; min-width:180px; background:var(--surface-2); border-radius:var(--radius-lg); padding:14px; border:1px solid var(--border);">
              <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">Above</div>
              <div style="font-size:20px; font-weight:700; color:var(--text);">{result.above.total} {unit}</div>
              <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">
                {plateBreakdown(result.above.plates)} per side
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {:else if targetWeight && parseFloat(targetWeight) <= barWeight}
    <div class="card">
      <div style="color:var(--text-muted); font-size:13px;">Target weight must be greater than bar weight ({barWeight} {unit}).</div>
    </div>
  {/if}
</div>
