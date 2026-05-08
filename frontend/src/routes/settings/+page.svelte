<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { userProfile, refreshProfile } from '$lib/stores.js';

  let displayName = '';
  let unitPreference = 'lbs';
  let sex = null;
  let experienceLevel = 'intermediate';
  let equipment = new Set();
  let defaultRestSeconds = 90;
  let preferredSessionMinutes = 60;
  let saving = false;
  let savingEquip = false;
  let saved = false;
  let savedEquip = false;
  let saveError = '';

  let landmarks = [];
  let savingLandmarks = false;
  let savedLandmarks = false;

  let liftsaurToken = '';
  let liftsaurConnected = false;
  let savingToken = false;
  let syncing = false;
  let syncResult = null;
  let syncError = null;

  let injuries = [];
  let addingInjury = false;
  let newInjuryPart = '';
  let newInjurySeverity = 'mild';

  const BODY_PARTS = [
    { key: 'shoulder',   label: 'Shoulder' },
    { key: 'elbow',      label: 'Elbow' },
    { key: 'wrist',      label: 'Wrist' },
    { key: 'lower_back', label: 'Lower Back' },
    { key: 'upper_back', label: 'Upper Back' },
    { key: 'hip',        label: 'Hip' },
    { key: 'knee',       label: 'Knee' },
    { key: 'ankle',      label: 'Ankle' },
    { key: 'neck',       label: 'Neck' },
  ];
  const SEVERITIES = ['mild', 'moderate', 'severe'];

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
    sex = p.sex ?? null;
    experienceLevel = p.experience_level;
    defaultRestSeconds = p.default_rest_seconds ?? 90;
    preferredSessionMinutes = p.preferred_session_minutes ?? 60;
    equipment = new Set(p.equipment || []);
    try {
      landmarks = (await api.landmarks.get()).map(lm => ({ ...lm }));
    } catch {}
    try {
      const d = await api.liftsaur.getToken();
      liftsaurConnected = d.connected;
    } catch {}
    try { injuries = await api.injuries.list(); } catch {}
  });

  async function saveProfile() {
    saving = true;
    saveError = '';
    try {
      await api.profile.update({ display_name: displayName, unit_preference: unitPreference, sex, experience_level: experienceLevel, default_rest_seconds: defaultRestSeconds, preferred_session_minutes: preferredSessionMinutes });
      await refreshProfile();
      saved = true; setTimeout(() => saved = false, 2500);
    } catch (e) {
      saveError = e.message || 'Save failed';
    }
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

  async function addInjury() {
    if (!newInjuryPart) return;
    addingInjury = true;
    try {
      const inj = await api.injuries.create({ body_part: newInjuryPart, severity: newInjurySeverity });
      injuries = [...injuries.filter(i => i.body_part !== newInjuryPart), inj];
      newInjuryPart = '';
    } catch {}
    addingInjury = false;
  }

  async function removeInjury(id) {
    try {
      await api.injuries.delete(id);
      injuries = injuries.filter(i => i.id !== id);
    } catch {}
  }

  async function saveLiftsaurToken() {
    savingToken = true;
    try {
      await api.liftsaur.setToken(liftsaurToken);
      liftsaurConnected = true; liftsaurToken = '';
    } catch {}
    savingToken = false;
  }

  async function syncLiftosaur() {
    syncing = true; syncResult = null; syncError = null;
    try {
      syncResult = await api.liftsaur.sync();
    } catch (e) { syncError = e.message || 'Sync failed'; }
    syncing = false;
  }

  async function disconnectLiftosaur() {
    try { await api.liftsaur.setToken(''); } catch {}
    liftsaurConnected = false; syncResult = null; syncError = null;
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
    <div class="setting-lbl">Sex
      <div class="setting-hint">Used for strength level grading</div>
    </div>
    <div class="unit-toggle">
      <button class="unit-btn" class:active={sex === 'male'} on:click={() => sex = 'male'}>Male</button>
      <button class="unit-btn" class:active={sex === 'female'} on:click={() => sex = 'female'}>Female</button>
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

  <div class="setting-row">
    <div class="setting-lbl">Session Duration</div>
    <div class="dur-pills">
      {#each [30, 45, 60, 75, 90] as min}
        <button class="dur-pill" class:active={preferredSessionMinutes === min}
          on:click={() => preferredSessionMinutes = min}>{min}m</button>
      {/each}
    </div>
  </div>

  <div class="save-row">
    <button class="btn-primary" on:click={saveProfile} disabled={saving}>
      {saving ? 'Saving…' : 'Save Profile'}
    </button>
    {#if saved}<span class="saved-badge">Saved!</span>{/if}
  </div>
  {#if saveError}
    <div style="font-size:12px; color:var(--accent); margin-top:6px; word-break:break-all;">{saveError}</div>
  {/if}
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

<!-- Liftosaur Sync -->
<div class="settings-section">
  <div class="section-title">Liftosaur Sync</div>
  <p class="section-desc">Import your Liftosaur workout history using your API token (Settings → API in the Liftosaur app).</p>

  {#if !liftsaurConnected}
    <label class="setting-lbl">API Token</label>
    <input class="token-input" type="password" bind:value={liftsaurToken} placeholder="Paste your lftsk_… token" />
    <div class="save-row">
      <button class="btn-primary" on:click={saveLiftsaurToken} disabled={savingToken || !liftsaurToken}>
        {savingToken ? 'Saving…' : 'Connect Liftosaur'}
      </button>
    </div>
  {:else}
    <div class="connected-badge">Connected</div>
    <div class="save-row">
      <button class="btn-primary" on:click={syncLiftosaur} disabled={syncing}>
        {syncing ? 'Syncing…' : 'Sync Now'}
      </button>
      <button class="btn-ghost" on:click={disconnectLiftosaur}>Disconnect</button>
    </div>
    {#if syncResult}
      <div class="import-result">
        ✓ {syncResult.imported_sessions} sessions · {syncResult.imported_sets} sets imported
        {#if syncResult.skipped_sessions > 0} · {syncResult.skipped_sessions} already existed{/if}
        {#if syncResult.new_exercises.length > 0}
          <div class="new-exercises">New exercises created: {syncResult.new_exercises.join(', ')}</div>
        {/if}
      </div>
    {/if}
    {#if syncError}
      <div class="import-error">{syncError}</div>
    {/if}
  {/if}
</div>

<!-- Injuries & Limitations -->
<div class="settings-section">
  <div class="section-title">Injuries &amp; Limitations</div>
  <p class="section-desc">Active limitations — affected exercises show a ⚠ warning in the logger and library.</p>

  {#if injuries.length > 0}
    <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px;">
      {#each injuries as inj}
        {@const sev = inj.severity}
        <div style="display:flex; align-items:center; gap:6px; padding:6px 10px; border-radius:6px; border:1px solid {sev === 'severe' ? 'rgba(232,54,93,0.5)' : sev === 'moderate' ? 'rgba(255,160,40,0.5)' : 'var(--border)'}; background:{sev === 'severe' ? 'rgba(232,54,93,0.08)' : sev === 'moderate' ? 'rgba(255,160,40,0.08)' : 'var(--surface-2)'}; font-size:13px;">
          <span style="font-weight:600; text-transform:capitalize;">{inj.body_part.replace('_', ' ')}</span>
          <span style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">{sev}</span>
          <button on:click={() => removeInjury(inj.id)} style="background:none; border:none; cursor:pointer; color:var(--text-faint); font-size:14px; padding:0 2px; line-height:1;">×</button>
        </div>
      {/each}
    </div>
  {:else}
    <div style="font-size:12px; color:var(--text-faint); margin-bottom:16px;">No active limitations.</div>
  {/if}

  <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
    <select bind:value={newInjuryPart} style="flex:1; min-width:120px;">
      <option value="">Select body part…</option>
      {#each BODY_PARTS as p}
        {#if !injuries.some(i => i.body_part === p.key)}
          <option value={p.key}>{p.label}</option>
        {/if}
      {/each}
    </select>
    <select bind:value={newInjurySeverity} style="width:110px;">
      {#each SEVERITIES as s}
        <option value={s} style="text-transform:capitalize;">{s}</option>
      {/each}
    </select>
    <button class="btn-primary btn-sm" on:click={addInjury} disabled={!newInjuryPart || addingInjury}>
      + Add
    </button>
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
    <p class="section-desc">Sets per week per muscle group. <span class="landmark-legend">MEV = floor · MAV = target zone · MRV = ceiling</span></p>
    <div class="landmarks-wrap">
      <table class="landmarks-table">
        <thead>
          <tr>
            <th>Muscle</th>
            <th title="Minimum Effective Volume — floor">MEV</th>
            <th title="Minimum Adaptive Volume — target zone low">MAV Lo</th>
            <th title="Minimum Adaptive Volume — target zone high">MAV Hi</th>
            <th title="Maximum Recoverable Volume — ceiling">MRV</th>
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
  .setting-hint { font-size:10px; color:var(--muted); margin-top:2px; font-weight:400; }

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

  /* Duration pills */
  .dur-pills { display:flex; gap:4px; }
  .dur-pill {
    padding:4px 8px; background:transparent; border:1px solid var(--bdr-2);
    border-radius:4px; font-size:11px; color:var(--muted); cursor:pointer;
    transition:all 0.15s;
  }
  .dur-pill.active { border-color:var(--accent); color:var(--accent); background:var(--accent-bg); }

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

  /* Liftosaur sync */
  .connected-badge {
    display:inline-block; padding:3px 10px;
    background:rgba(34,197,94,0.15); border:1px solid rgba(34,197,94,0.3);
    border-radius:4px; font-size:11px; font-weight:600; color:#22c55e;
    margin-bottom:12px;
  }
  .token-input {
    width:100%; background:var(--surf-2); border:1px solid var(--bdr-2);
    border-radius:var(--radius); padding:8px 10px;
    font-size:12px; color:var(--text); outline:none; box-sizing:border-box;
    margin-bottom:4px;
  }
  .btn-ghost {
    padding:8px 14px; background:transparent;
    border:1px solid var(--bdr-2); border-radius:var(--radius);
    font-size:12px; color:var(--muted); cursor:pointer; transition:all 0.15s;
  }
  .btn-ghost:hover { border-color:var(--accent); color:var(--accent); }
  .import-result { font-size:12px; color:var(--success); margin-top:10px; line-height:1.6; }
  .new-exercises { color:var(--muted); margin-top:4px; }
  .import-error { font-size:12px; color:var(--accent); margin-top:10px; }

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
  .landmark-legend {
    display:inline-block; margin-top:3px;
    font-size:10px; color:var(--muted); letter-spacing:0.03em;
    opacity:0.8;
  }
</style>
