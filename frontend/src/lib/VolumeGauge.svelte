<script>
  export let exercises = [];
  export let exerciseIndex = {};
  export let landmarks = {};
  export let expanded = false;

  const MUSCLE_GROUPS = [
    { label: 'Push',         muscles: ['chest', 'shoulders', 'triceps'] },
    { label: 'Pull',         muscles: ['back', 'lats', 'biceps'] },
    { label: 'Legs',         muscles: ['quads', 'hamstrings', 'glutes', 'calves'] },
    { label: 'Core & Traps', muscles: ['abs', 'traps'] },
  ];

  const FRIENDLY = {
    chest: 'Chest', shoulders: 'Shoulders', triceps: 'Triceps',
    back: 'Back', lats: 'Lats', biceps: 'Biceps',
    quads: 'Quads', hamstrings: 'Hamstrings', glutes: 'Glutes', calves: 'Calves',
    abs: 'Core', traps: 'Traps',
  };

  const STATUS = {
    below_mev: { color: '#e8365d', bg: 'rgba(232,54,93,0.12)', label: 'Not enough to grow' },
    in_mav:    { color: '#36c87a', bg: 'rgba(54,200,122,0.12)', label: 'Sweet spot' },
    above_mav: { color: '#e8a036', bg: 'rgba(232,160,54,0.12)', label: 'Getting high' },
    at_mrv:    { color: '#e87820', bg: 'rgba(232,120,32,0.12)', label: 'Too much' },
    unknown:   { color: '#6868a0', bg: 'rgba(104,104,160,0.08)', label: '—' },
  };

  function computeMuscleSets(exs, idx) {
    const sets = {};
    for (const ex of exs) {
      const data = idx[ex.exercise_id];
      if (!data) continue;
      const w = ex.target_sets ?? 0;
      for (const m of (data.primary_muscles ?? [])) sets[m] = (sets[m] ?? 0) + w;
      for (const m of (data.secondary_muscles ?? [])) sets[m] = (sets[m] ?? 0) + w * 0.5;
    }
    return sets;
  }

  function getStatus(sets, lm) {
    if (!lm) return 'unknown';
    if (sets < lm.mev) return 'below_mev';
    if (sets <= lm.mav_high) return 'in_mav';
    if (sets < lm.mrv) return 'above_mav';
    return 'at_mrv';
  }

  function barFill(sets, lm) {
    if (!lm || lm.mrv === 0) return 0;
    return Math.min(100, Math.round((sets / lm.mrv) * 100));
  }

  $: muscleSets = computeMuscleSets(exercises, exerciseIndex);
  $: hasData = exercises.length > 0 && Object.keys(exerciseIndex).length > 0;
</script>

<div style="margin-bottom:16px; border:1px solid var(--border); border-radius:10px; overflow:hidden; background:var(--surface);">
  <button
    on:click={() => expanded = !expanded}
    style="width:100%; display:flex; align-items:center; gap:8px; padding:11px 14px; background:var(--surface-2); border:none; border-bottom:1px solid {expanded ? 'var(--border)' : 'transparent'}; cursor:pointer; text-align:left; transition:border-color 0.15s;"
  >
    <span style="font-size:13px; font-weight:700; color:var(--text);">Volume Check</span>
    <span style="font-size:11px; color:var(--text-muted);">vs. your goal targets</span>
    <span style="margin-left:auto; font-size:11px; color:var(--text-faint);">{expanded ? '▲' : '▼'}</span>
  </button>

  {#if expanded}
    <div style="padding:12px 14px;">
      {#if !hasData}
        <div style="font-size:12px; color:var(--text-faint); padding:4px 0;">Add exercises to see volume coverage.</div>
      {:else}
        {#each MUSCLE_GROUPS as group}
          {@const groupHasData = group.muscles.some(m => !!landmarks[m])}
          {#if groupHasData}
            <div style="margin-bottom:12px;">
              <div style="font-size:10px; font-weight:700; color:var(--text-faint); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;">{group.label}</div>
              {#each group.muscles as muscle}
                {@const sets = muscleSets[muscle] ?? 0}
                {@const lm = landmarks[muscle]}
                {#if lm}
                  {@const status = getStatus(sets, lm)}
                  {@const cfg = STATUS[status]}
                  {@const fill = barFill(sets, lm)}
                  <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;" title="{lm ? `MEV ${lm.mev} · MAV ${lm.mav_low}–${lm.mav_high} · MRV ${lm.mrv}` : 'No landmark data'}">
                    <span style="font-size:11px; color:var(--text-muted); min-width:80px;">{FRIENDLY[muscle] ?? muscle}</span>
                    <div style="flex:1; height:6px; border-radius:3px; background:var(--surface-2); overflow:hidden; position:relative;">
                      <div style="position:absolute; left:0; top:0; height:100%; width:{fill}%; background:{cfg.color}; border-radius:3px; transition:width 0.3s;"></div>
                      {#if lm}
                        <div style="position:absolute; left:{Math.min(100, Math.round(lm.mev / lm.mrv * 100))}%; top:0; height:100%; width:1px; background:rgba(255,255,255,0.2);"></div>
                      {/if}
                    </div>
                    <span style="font-size:10px; color:{cfg.color}; min-width:110px; font-weight:500;">{cfg.label}</span>
                  </div>
                {/if}
              {/each}
            </div>
          {/if}
        {/each}
        <div style="font-size:10px; color:var(--text-faint); margin-top:4px; border-top:1px solid var(--border); padding-top:8px; line-height:1.7;">
          <span style="color:var(--text-muted);">MEV</span> = floor &nbsp;·&nbsp; <span style="color:var(--text-muted);">MAV</span> = target zone &nbsp;·&nbsp; <span style="color:var(--text-muted);">MRV</span> = ceiling &nbsp;·&nbsp; bar fills to MRV. Secondary muscles count as 0.5 sets.
        </div>
      {/if}
    </div>
  {/if}
</div>
