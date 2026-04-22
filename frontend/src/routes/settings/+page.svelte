<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { userProfile, refreshProfile } from '$lib/stores.js';

  let displayName = '';
  let unitPreference = 'lbs';
  let experienceLevel = 'intermediate';
  let equipment = new Set();
  let saving = false;
  let savingEquip = false;
  let saved = false;
  let savedEquip = false;

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

  onMount(async () => {
    const p = await api.profile.get();
    displayName = p.display_name;
    unitPreference = p.unit_preference;
    experienceLevel = p.experience_level;
    equipment = new Set(p.equipment || []);
  });

  async function saveProfile() {
    saving = true;
    try {
      await api.profile.update({ display_name: displayName, unit_preference: unitPreference, experience_level: experienceLevel });
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
    equipment = new Set(equipment); // trigger reactivity
  }
</script>

<svelte:head><title>Settings — LiftForge</title></svelte:head>

<div style="max-width:600px;">
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

  <!-- Equipment -->
  <div class="card">
    <div class="section-title mb-3">Available Equipment</div>
    <p style="color:var(--text-muted); font-size:13px; margin-bottom:16px; line-height:1.6;">
      Mark what you have access to. This helps the AI coach give relevant suggestions.
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
</div>
