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

  // Landmarks
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

  const REST_PRESETS = [
    { label: '60s',  value: 60 },
    { label: '90s',  value: 90 },
    { label: '2min', value: 120 },
    { label: '3min', value: 180 },
  ];

  onMount(async () => {
    const p = await api.profile.get();
    displayName = p.display_name;
    unitPreference = p.unit_preference;
    experienceLevel = p.experience_level;
    defaultRestSeconds = p.default_rest_seconds ?? 90;
    equipment = new Set(p.equipment || []);

    try {
      landmarks = await api.landmarks.get();
      landmarks = landmarks.map(lm => ({ ...lm }));
    } catch (e) {
      console.error('Failed to load landmarks', e);
    }
  });

  async function saveProfile() {
    saving = true;
    try {
      await api.profile.update({
        display_name: displayName,
        unit_preference: unitPreference,
        experience_level: experienceLevel,
        default_rest_seconds: defaultRestSeconds,
      });
      await refreshProfile();
      saved = true;
      setTimeout(() => (saved = false), 2500);
    } catch (e) {
      console.error(e);
    }
    saving = false;
  }

  async function saveEquipment() {
    savingEquip = true;
    try {
      await api.profile.updateEquipment([...equipment]);
      savedEquip = true;
      setTimeout(() => (savedEquip = false), 2500);
    } catch (e) {
      console.error(e);
    }
    savingEquip = false;
  }

  function toggleEquipment(key) {
    if (equipment.has(key)) {
      equipment.delete(key);
    } else {
      equipment.add(key);
    }
    equipment = new Set(equipment);
  }

  async function saveLandmarks() {
    savingLandmarks = true;
    try {
      await api.landmarks.update(landmarks.map(lm => ({
        muscle: lm.muscle,
        mev: Number(lm.mev),
        mav_low: Number(lm.mav_low),
        mav_high: Number(lm.mav_high),
        mrv: Number(lm.mrv),
      })));
      savedLandmarks = true;
      setTimeout(() => (savedLandmarks = false), 2500);
    } catch (e) {
      console.error(e);
    }
    savingLandmarks = false;
  }
</script>

<svelte:head><title>Settings — LiftForge</title></svelte:head>

<div style="max-width:640px;">
  <h2 style="font-size:20px; font-weight:700; margin-bottom:24px;">Settings</h2>

  <!-- Profile -->
  <div class="card mb-4">
    <div class="section-title mb-3">Profile</div>

    <div style="display:flex; flex-direction:column; gap:14px;">
      <div>
        <label for="displayName">Display Name</label>
        <input id="displayName" bind:value={displayName} placeholder="Your name" />
      </div>

      <div>
        <label for="units">Weight Units</label>
        <select id="units" bind:value={unitPreference}>
          <option value="lbs">lbs</option>
          <option value="kg">kg</option>
        </select>
      </div>

      <div>
        <label for="exp">Experience Level</label>
        <select id="exp" bind:value={experienceLevel}>
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>
      </div>
    </div>

    <div class="flex items-center gap-3 mt-4">
      <button class="btn-primary" on:click={saveProfile} disabled={saving}>
        {saving ? 'Saving...' : 'Save Profile'}
      </button>
      {#if saved}
        <span style="color:var(--success); font-size:13px;">Saved!</span>
      {/if}
    </div>
  </div>

  <!-- Rest Timer Default -->
  <div class="card mb-4">
    <div class="section-title mb-3">Rest Timer Default</div>
    <p style="color:var(--text-muted); font-size:13px; margin-bottom:14px; line-height:1.6;">
      Default rest period shown after logging a set.
    </p>

    <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px;">
      {#each REST_PRESETS as preset}
        <button
          on:click={() => (defaultRestSeconds = preset.value)}
          style="padding:8px 16px; border-radius:4px; border:2px solid {defaultRestSeconds === preset.value ? 'var(--primary)' : 'var(--border)'}; background:{defaultRestSeconds === preset.value ? 'rgba(232,160,64,0.12)' : 'var(--surface-2)'}; color:{defaultRestSeconds === preset.value ? 'var(--primary)' : 'var(--text)'}; font-size:13px; font-weight:{defaultRestSeconds === preset.value ? '700' : '400'}; cursor:pointer; transition:all 0.15s;"
        >
          {preset.label}
        </button>
      {/each}
    </div>

    <div style="display:flex; align-items:center; gap:8px; margin-bottom:16px;">
      <label for="restSeconds" style="font-size:13px; color:var(--text-muted);">Custom:</label>
      <input
        id="restSeconds"
        type="number"
        min="10"
        max="600"
        step="5"
        bind:value={defaultRestSeconds}
        style="width:90px;"
      />
      <span style="font-size:13px; color:var(--text-muted);">seconds</span>
    </div>

    <div class="flex items-center gap-3">
      <button class="btn-primary" on:click={saveProfile} disabled={saving}>
        {saving ? 'Saving...' : 'Save'}
      </button>
      {#if saved}
        <span style="color:var(--success); font-size:13px;">Saved!</span>
      {/if}
    </div>
  </div>

  <!-- Equipment -->
  <div class="card mb-4">
    <div class="section-title mb-3">Available Equipment</div>
    <p style="color:var(--text-muted); font-size:13px; margin-bottom:16px; line-height:1.6;">
      Mark what you have access to. This determines which exercises are suggested in your programs.
    </p>

    {#each EQUIPMENT_GROUPS as group}
      <div style="margin-bottom:18px;">
        <div style="font-size:12px; font-weight:600; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px;">
          {group.label}
        </div>
        <div style="display:flex; flex-direction:column; gap:8px;">
          {#each group.items as item}
            <label
              style="display:flex; align-items:center; gap:10px; cursor:pointer; padding:8px 10px; background:var(--surface-2); border:1px solid {equipment.has(item.key) ? 'rgba(232,160,64,0.3)' : 'var(--border)'}; border-radius:4px; transition:border-color 0.15s;"
            >
              <input
                type="checkbox"
                checked={equipment.has(item.key)}
                on:change={() => toggleEquipment(item.key)}
                style="width:auto; accent-color:var(--primary);"
              />
              <span style="color:var(--text); font-size:13px;">{item.label}</span>
            </label>
          {/each}
        </div>
      </div>
    {/each}

    <div class="flex items-center gap-3 mt-2">
      <button class="btn-primary" on:click={saveEquipment} disabled={savingEquip}>
        {savingEquip ? 'Saving...' : 'Save Equipment'}
      </button>
      {#if savedEquip}
        <span style="color:var(--success); font-size:13px;">Saved!</span>
      {/if}
    </div>
  </div>

  <!-- Export Data -->
  <div class="card mb-4">
    <div class="section-title mb-1">Export Data</div>
    <p style="color:var(--text-muted); font-size:12px; margin-bottom:16px; line-height:1.6;">
      Your data stays on your server. These files contain everything.
    </p>
    <div style="display:flex; flex-direction:column; gap:8px;">
      <button
        class="btn-secondary"
        on:click={() => (window.location.href = '/api/export/workouts.csv')}
        style="text-align:left; justify-content:flex-start;"
      >
        Download Workouts CSV
      </button>
      <button
        class="btn-secondary"
        on:click={() => (window.location.href = '/api/export/measurements.csv')}
        style="text-align:left; justify-content:flex-start;"
      >
        Download Measurements CSV
      </button>
      <button
        class="btn-secondary"
        on:click={() => (window.location.href = '/api/export/exercises.csv')}
        style="text-align:left; justify-content:flex-start;"
      >
        Download Exercise Library CSV
      </button>
      <button
        class="btn-secondary"
        on:click={() => (window.location.href = '/api/export/backup.json')}
        style="text-align:left; justify-content:flex-start;"
      >
        Download Full Backup (JSON)
      </button>
    </div>
  </div>

  <!-- Volume Landmarks -->
  {#if landmarks.length > 0}
    <div class="card">
      <div class="section-title mb-1">Volume Landmarks</div>
      <p style="color:var(--text-muted); font-size:12px; margin-bottom:14px; line-height:1.6;">
        MEV = Minimum Effective Volume · MAV = Maximum Adaptive Volume · MRV = Maximum Recoverable Volume (sets/week)
      </p>

      <div style="overflow-x:auto;">
        <table style="width:100%; font-size:12px;">
          <thead>
            <tr>
              <th style="text-align:left; padding:6px 8px; color:var(--text-muted); font-weight:600; min-width:90px;">Muscle</th>
              <th style="padding:6px 8px; color:var(--text-muted); font-weight:600;">MEV</th>
              <th style="padding:6px 8px; color:var(--text-muted); font-weight:600;">MAV Low</th>
              <th style="padding:6px 8px; color:var(--text-muted); font-weight:600;">MAV High</th>
              <th style="padding:6px 8px; color:var(--text-muted); font-weight:600;">MRV</th>
            </tr>
          </thead>
          <tbody>
            {#each landmarks as lm}
              <tr style="border-top:1px solid var(--border);">
                <td style="padding:7px 8px; color:var(--text); text-transform:capitalize; font-weight:500;">{lm.muscle}</td>
                {#each ['mev', 'mav_low', 'mav_high', 'mrv'] as field}
                  <td style="padding:4px 8px;">
                    <input
                      type="number"
                      min="0"
                      max="60"
                      step="1"
                      bind:value={lm[field]}
                      style="width:52px; text-align:center;"
                    />
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="flex items-center gap-3 mt-4">
        <button class="btn-primary" on:click={saveLandmarks} disabled={savingLandmarks}>
          {savingLandmarks ? 'Saving...' : 'Save Landmarks'}
        </button>
        {#if savedLandmarks}
          <span style="color:var(--success); font-size:13px;">Saved!</span>
        {/if}
      </div>
    </div>
  {/if}
</div>
