<script>
  export let label = '';
  export let sets = 0;
  export let landmarks = null;
  export let fatigued = false;

  const STATUS_COLOR = {
    below_mev: '#e8365d',
    in_mav:    '#36c87a',
    above_mav: '#e8a036',
    at_mrv:    '#e87820',
    unknown:   '#6868a0',
  };

  const STATUS_LABEL = {
    below_mev: 'Under floor',
    in_mav:    'Sweet spot',
    above_mav: 'Above sweet spot',
    at_mrv:    'At limit',
    unknown:   '—',
  };

  function getStatus(s, lm) {
    if (!lm) return 'unknown';
    if (s < lm.mev)       return 'below_mev';
    if (s <= lm.mav_high) return 'in_mav';
    if (s < lm.mrv)       return 'above_mav';
    return 'at_mrv';
  }

  function toPct(val, max) {
    if (!max) return 0;
    return Math.min(100, (val / max) * 100);
  }

  $: lm = landmarks;
  $: status = getStatus(sets, lm);
  $: color = STATUS_COLOR[status];
  $: fillPct  = lm ? toPct(sets,       lm.mrv) : 0;
  $: mevPct   = lm ? toPct(lm.mev,     lm.mrv) : 0;
  $: mavLoPct = lm ? toPct(lm.mav_low, lm.mrv) : 0;
  $: mavHiPct = lm ? toPct(lm.mav_high,lm.mrv) : 0;
</script>

<div style="padding:10px 0 6px; border-bottom:1px solid var(--bdr);">
  <!-- Header: name + fatigue badge + count + status -->
  <div style="display:flex; align-items:baseline; gap:5px; margin-bottom:9px;">
    <span style="font-size:13px; font-weight:600; color:var(--text);">{label}</span>
    {#if fatigued}
      <span
        title="Fatigue flagged — consider deloading this pattern"
        style="font-size:11px; color:#e8a036; cursor:default; line-height:1;"
      >⚠</span>
    {/if}
    <span style="margin-left:auto; font-size:12px; font-weight:700; color:{color};">{sets}</span>
    {#if lm}
      <span style="font-size:11px; color:var(--muted); font-weight:400;">/ {lm.mrv} sets/wk</span>
    {/if}
    <span style="font-size:11px; color:{color}; font-weight:500; min-width:108px; text-align:right;">{STATUS_LABEL[status]}</span>
  </div>

  {#if lm}
    <!-- Gauge track + thumb -->
    <div style="position:relative; height:20px; margin:0 4px;">
      <!-- Segmented zone background (clipped to track shape) -->
      <div style="position:absolute; left:0; right:0; top:50%; transform:translateY(-50%); height:8px; border-radius:4px; overflow:hidden; background:rgba(255,255,255,0.05);">
        <!-- Zone 0 → MEV: red tint (under floor) -->
        <div style="position:absolute;left:0;top:0;width:{mevPct}%;height:100%;background:rgba(232,54,93,0.20);"></div>
        <!-- Zone MEV → mav_low: soft green (building) -->
        <div style="position:absolute;left:{mevPct}%;top:0;width:{mavLoPct - mevPct}%;height:100%;background:rgba(54,200,122,0.11);"></div>
        <!-- Zone mav_low → mav_high: green sweet spot -->
        <div style="position:absolute;left:{mavLoPct}%;top:0;width:{mavHiPct - mavLoPct}%;height:100%;background:rgba(54,200,122,0.24);"></div>
        <!-- Zone mav_high → MRV: amber -->
        <div style="position:absolute;left:{mavHiPct}%;top:0;width:{100 - mavHiPct}%;height:100%;background:rgba(232,160,54,0.20);"></div>
        <!-- Filled bar (status color, 0 → current) -->
        {#if fillPct > 0}
          <div style="position:absolute;left:0;top:0;width:{fillPct}%;height:100%;background:{color};opacity:0.72;"></div>
        {/if}
        <!-- Tick marks at zone boundaries -->
        <div style="position:absolute;left:{mevPct}%;top:0;width:1px;height:100%;background:rgba(255,255,255,0.38);"></div>
        <div style="position:absolute;left:{mavLoPct}%;top:0;width:1px;height:100%;background:rgba(255,255,255,0.25);"></div>
        <div style="position:absolute;left:{mavHiPct}%;top:0;width:1px;height:100%;background:rgba(255,255,255,0.25);"></div>
      </div>
      <!-- Thumb circle (outside the clipped zone div so it renders over the track) -->
      {#if fillPct > 0}
        <div style="
          position:absolute;
          left:{fillPct}%;
          top:50%;
          transform:translate(-50%,-50%);
          width:14px;height:14px;
          border-radius:50%;
          background:{color};
          box-shadow:0 0 0 2px rgba(0,0,0,0.55), 0 0 8px {color}55;
          pointer-events:none;
        "></div>
      {/if}
    </div>

    <!-- Landmark labels -->
    <div style="display:flex; justify-content:space-between; margin:4px 4px 0; font-size:9px; color:var(--muted); line-height:1.3;">
      <span>MEV (Floor) · {lm.mev}</span>
      <span style="text-align:center; color:rgba(54,200,122,0.65);">Sweet Spot · {lm.mav_low}–{lm.mav_high}</span>
      <span style="text-align:right;">MRV (Limit) · {lm.mrv}</span>
    </div>
  {:else}
    <div style="height:8px; border-radius:4px; background:rgba(255,255,255,0.05); margin:0 4px;"></div>
    <div style="font-size:10px; color:var(--muted); margin:4px 4px 0;">No targets configured</div>
  {/if}
</div>
