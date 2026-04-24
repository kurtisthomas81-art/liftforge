<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { userProfile, refreshProfile } from '$lib/stores.js';

  let displayName = '';
  let unitPreference = 'lbs';
  let experienceLevel = 'intermediate';
  let equipment = new Set();
  let defaultRestSeconds = 90;
  let saving = false;
  let savingEquip = false;
  let saved = false;
  let savedEquip = false;

  let landmarks = [];
  let savingLandmarks = false;
  let savedLandmarks = false;

  const EQUIPMENT_GROUPS = [
    {
      label: 'Free Weights',
      items: [
        { key: 'barbell',    label: 'Barbell' },
        { key: 'dumbbells',  label: 'Dumbbells' },
        { key: 'ez_bar',     label: 'EZ Bar' },
        { key: 'trap_bar',   label: 'Trap Bar' },
        { key: 'kettlebell', label: 'Kettlebell' },
      ],
    },
    {
      label: 'Racks & Benches',
      items: [
        { key: 'rack',          label: 'Squat / Power Rack' },
        { key: 'bench',         label: 'Flat Bench' },
        { key: 'incline_bench', label: 'Incline Bench' },
      ],
    },
    {
      label: 'Machines & Cables',
      items: [
        { key: 'cable_machine', label: 'Cable Machine' },
        { key: 'machine',       label: 'Plate-Loaded Machines' },
        { key: 'leg_press',     label: 'Leg Press' },
      ],
    },
    {
      label: 'Bodyweight & Accessories',
      items: [
        { key: 'pull_up_bar', label: 'Pull-Up Bar' },
        { key: 'dip_bars',    label: 'Dip Bars' },
        { key: 'bodyweight',  label: 'Bodyweight' },
        { key: 'bands',       label: 'Resistance Bands' },
      ],
    },
  ];

  const EXP_LEVELS = [
    { value: 'beginner',     label: 'Beginner' },
    { value: 'intermediate', label: 'Intermediate' },
    { value: 'advanced',     label: 'Advanced' },
  ];

  const EXPORT_ROWS = [
    { label: 'Workouts CSV',        href: '/api/export/workouts.csv' },
    { label: 'Measurements CSV',    href: '/api/export/measurements.csv' },
    { label: 'Exercise Library CSV',href: '/api/export/exercises.csv' },
    { label: 'Full Backup (JSON)',   href: '/api/export/backup.json' },
  ];

  $: avatarInitial = (displayName || '?')[0].toUpperCase();

  onMount(async () => {
    const p = await api.profile.get();
    displayName = p.display_name;
    unitPreference = p.unit_preference;
    experienceLevel = p.experience_level;
    defaultRestSeconds = p.default_rest_seconds ?? 90;
    equipment = new Set(p.equipment || []);
    try {
      landmarks = (await api.landmarks.get()).map(lm => ({ ...lm }));
    } catch {}
  });

  async function saveProfile() {
    saving = true;
    try {
      await api.profile.update({ display_name: displayName, unit_preference: unitPreference, experience_level: experienceLevel, default_rest_seconds: defaultRestSeconds });
      await refreshProfile();
      saved = true; setTimeout(() => saved = false, 2500);
    } catch {}
    saving = false;
  }

  async function saveEquipment() {
    savingEquip = true;
    try {
      await api.profile.updateEquipment([...equipment]);
      savedEquip = true; setTimeout(() => savedEquip = false, 2500);
    } catch {}
    savingEquip = false;
  }

  function toggleEquipment(key) {
    if (equipment.has(key)) equipment.delete(key);
    else equipment.add(key);
    equipment = new Set(equipment);
  }

  async function saveLandmarks() {
    savingLandmarks = true;
    try {
      await api.landmarks.update(landmarks.map(lm => ({
        muscle: lm.muscle,
        mev: Number(lm.mev), mav_low: Number(lm.mav_low),
        mav_high: Number(lm.mav_high), mrv: Number(lm.mrv),
      })));
      savedLandmarks = true; setTimeout(() => savedLandmarks = false, 2500);
    } catch {}
    savingLandmarks = false;
  }

  function adjustRest(delta) {
    defaultRestSeconds = Math.max(10, Math.min(600, defaultRestSeconds + delta));
  }
</script>

<svelte:head><title>Settings — LiftForge</title></svelte:head>

<div class="page-title">Account <em>Settings</em></div>

<!-- Profile card -->
<div class="profile-card">
  <div class="avatar">{avatarInitial}</div>
  <div class="profile-info">
    <input class="name-input" bind:value={displayName} placeholder="Display name" />
    <div class="profile-sub">LiftForge</div>
  </div>
</div>

<!-- Profile settings -->
<div class="settings-section">
  <div class="section-title">Profile</div>

  <div class="setting-row">
    <div class="setting-lbl">Weight Units</div>
    <div class="unit-toggle">
      <button class="unit-btn" class:active={unitPreference === 'lbs'} on:click={() => unitPreference = 'lbs'}>lbs</button>
      <button class="unit-btn" class:active={unitPreference === 'kg'} on:click={() => unitPreference = 'kg'}>kg</button>
    </div>
  </div>

  <div class="setting-row">
    <div class="setting-lbl">Experience Level</div>
    <div class="exp-pills">
      {#each EXP_LEVELS as lvl}
        <button class="exp-pill" class:active={experienceLevel === lvl.value}
          on:click={() => experienceLevel = lvl.value}>{lvl.label}</button>
      {/each}
    </div>
  </div>

  <div class="setting-row">
    <div class="setting-lbl">Default Rest</div>
    <div class="rest-stepper">
      <button class="step-btn" on:click={() => adjustRest(-15)}>−</button>
      <span class="rest-val">{defaultRestSeconds}s</span>
      <button class="step-btn" on:click={() => adjustRest(15)}>+</button>
    </div>
  </div>

  <div class="save-row">
    <button class="btn-primary" on:click={saveProfile} disabled={saving}>
      {saving ? 'Saving…' : 'Save Profile'}
    </button>
    {#if saved}<span class="saved-badge">Saved!</span>{/if}
  </div>
</div>

<!-- Equipment -->
<div class="settings-section">
  <div class="section-title">Available Equipment</div>
  <p class="section-desc">Controls which exercises appear in your programs.</p>

  {#each EQUIPMENT_GROUPS as group}
    <div class="equip-group-label">{group.label}</div>
    {#each group.items as item}
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <div class="equip-row" class:checked={equipment.has(item.key)} on:click={() => toggleEquipment(item.key)}>
        <span class="equip-label">{item.label}</span>
        <span class="equip-check" class:on={equipment.has(item.key)}>
          {equipment.has(item.key) ? '✓' : ''}
        </span>
      </div>
    {/each}
  {/each}

  <div class="save-row mt-3">
    <button class="btn-primary" on:click={saveEquipment} disabled={savingEquip}>
      {savingEquip ? 'Saving…' : 'Save Equipment'}
    </button>
    {#if savedEquip}<span class="saved-badge">Saved!</span>{/if}
  </div>
</div>

<!-- Export Data -->
<div class="settings-section">
  <div class="section-title">Export Data</div>
  <p class="section-desc">Your data stays on your server. Download any time.</p>
  {#each EXPORT_ROWS as row}
    <a class="data-row" href={row.href}>
      <span>{row.label}</span>
      <span class="data-row-arrow">↓</span>
    </a>
  {/each}
</div>

<!-- Volume Landmarks -->
{#if landmarks.length > 0}
  <div class="settings-section">
    <div class="section-title">Volume Landmarks</div>
    <p class="section-desc">MEV · MAV · MRV — sets per week per muscle group.</p>
    <div class="landmarks-wrap">
      <table class="landmarks-table">
        <thead>
          <tr>
            <th>Muscle</th>
            <th>MEV</th>
            <th>MAV Lo</th>
            <th>MAV Hi</th>
            <th>MRV</th>
          </tr>
        </thead>
        <tbody>
          {#each landmarks as lm}
            <tr>
              <td class="lm-muscle">{lm.muscle}</td>
              {#each ['mev', 'mav_low', 'mav_high', 'mrv'] as field}
                <td><input type="number" min="0" max="60" step="1" bind:value={lm[field]} /></td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <div class="save-row mt-3">
      <button class="btn-primary" on:click={saveLandmarks} disabled={savingLandmarks}>
        {savingLandmarks ? 'Saving…' : 'Save Landmarks'}
      </button>
      {#if savedLandmarks}<span class="saved-badge">Saved!</span>{/if}
    </div>
  </div>
{/if}

<style>
  .page-title { font-family:var(--serif); font-size:26px; color:var(--text); margin-bottom:16px; line-height:1; }
  .page-title em { font-style:italic; color:var(--accent); }

  /* Profile card */
  .profile-card {
    display:flex; align-items:center; gap:14px;
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:16px;
    margin-bottom:16px;
  }
  .avatar {
    width:52px; height:52px; border-radius:50%;
    background:var(--accent-bg); border:1.5px solid var(--accent);
    display:flex; align-items:center; justify-content:center;
    font-family:var(--serif); font-size:24px; color:var(--accent);
    flex-shrink:0;
  }
  .profile-info { flex:1; }
  .name-input {
    background:transparent; border:none; padding:0;
    font-family:var(--serif); font-size:20px; color:var(--text);
    width:100%; outline:none;
  }
  .name-input:focus { color:var(--accent); }
  .profile-sub { font-size:11px; color:var(--muted); margin-top:2px; }

  /* Sections */
  .settings-section {
    background:var(--surf); border:1px solid var(--bdr);
    border-radius:var(--radius-lg); padding:16px;
    margin-bottom:12px;
  }
  .section-desc { font-size:12px; color:var(--muted); margin-bottom:14px; line-height:1.6; margin-top:4px; }

  /* Setting rows */
  .setting-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:10px 0; border-bottom:1px solid var(--bdr);
  }
  .setting-row:last-of-type { border-bottom:none; }
  .setting-lbl { font-size:13px; color:var(--text); }

  /* Unit toggle */
  .unit-toggle { display:flex; background:var(--surf-2); border:1px solid var(--bdr-2); border-radius:6px; overflow:hidden; }
  .unit-btn {
    padding:5px 14px; background:transparent; border:none;
    font-size:12px; font-weight:600; color:var(--muted); cursor:pointer;
    transition:all 0.15s;
  }
  .unit-btn.active { background:var(--accent); color:#fff; }

  /* Exp pills */
  .exp-pills { display:flex; gap:4px; }
  .exp-pill {
    padding:4px 10px; background:transparent; border:1px solid var(--bdr-2);
    border-radius:4px; font-size:11px; color:var(--muted); cursor:pointer;
    transition:all 0.15s;
  }
  .exp-pill.active { border-color:var(--accent); color:var(--accent); background:var(--accent-bg); }

  /* Rest stepper */
  .rest-stepper { display:flex; align-items:center; gap:10px; }
  .step-btn {
    width:28px; height:28px; border-radius:50%;
    background:var(--surf-2); border:1px solid var(--bdr-2);
    color:var(--text); font-size:16px; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    transition:all 0.15s;
  }
  .step-btn:hover { border-color:var(--accent); color:var(--accent); }
  .rest-val { font-family:var(--serif); font-size:17px; color:var(--text); min-width:40px; text-align:center; }

  .save-row { display:flex; align-items:center; gap:10px; margin-top:14px; }
  .saved-badge { font-size:12px; color:var(--success); font-weight:600; }

  /* Equipment rows */
  .equip-group-label {
    font-size:10px; color:var(--muted); text-transform:uppercase;
    letter-spacing:0.08em; font-weight:600;
    margin:14px 0 6px;
  }
  .equip-group-label:first-of-type { margin-top:0; }
  .equip-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:10px 12px; border:1px solid var(--bdr);
    border-radius:var(--radius); margin-bottom:4px;
    cursor:pointer; transition:all 0.15s;
    background:var(--surf-2);
  }
  .equip-row.checked { border-color:rgba(232,54,93,0.3); background:var(--accent-bg); }
  .equip-label { font-size:13px; color:var(--text); }
  .equip-check {
    width:20px; height:20px; border-radius:50%;
    border:1.5px solid var(--bdr-2);
    display:flex; align-items:center; justify-content:center;
    font-size:10px; color:transparent;
    transition:all 0.15s;
  }
  .equip-check.on { border-color:var(--accent); background:var(--accent); color:#fff; }

  /* Export rows */
  .data-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:12px 0; border-bottom:1px solid var(--bdr);
    font-size:13px; color:var(--text); text-decoration:none;
    transition:color 0.15s;
  }
  .data-row:last-child { border-bottom:none; }
  .data-row:hover { color:var(--accent); }
  .data-row-arrow { font-size:14px; color:var(--muted); }

  /* Landmarks table */
  .landmarks-wrap { overflow-x:auto; }
  .landmarks-table { width:100%; border-collapse:collapse; font-size:12px; }
  .landmarks-table th {
    text-align:center; padding:6px 4px;
    color:var(--muted); font-size:10px; text-transform:uppercase;
    letter-spacing:0.06em; font-weight:600;
  }
  .landmarks-table th:first-child { text-align:left; }
  .landmarks-table tr { border-top:1px solid var(--bdr); }
  .landmarks-table tr:first-child { border-top:none; }
  .lm-muscle { padding:7px 4px; color:var(--text); text-transform:capitalize; font-weight:500; }
  .landmarks-table td { padding:4px; }
  .landmarks-table input { width:50px; text-align:center; }
  .mt-3 { margin-top:12px; }
</style>
