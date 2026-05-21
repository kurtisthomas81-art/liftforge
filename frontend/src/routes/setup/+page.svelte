<script>
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let step = 1;
  const TOTAL = 4;

  // Step 1
  let displayName = '';
  let goal = 'general_fitness';

  // Step 2
  let equipment = new Set(['bodyweight', 'dumbbells']);

  // Step 3
  let unitPreference = 'lbs';
  let sex = null;
  let experienceLevel = 'beginner';
  let preferredSessionMinutes = 60;

  let saving = false;

  const GOALS = [
    { key: 'general_fitness', label: 'General Fitness', desc: 'Athletic & functional — balanced training, 6–12 reps' },
    { key: 'hypertrophy',     label: 'Build Muscle',    desc: 'Maximize muscle size — higher volume, moderate weights' },
    { key: 'strength',        label: 'Build Strength',  desc: 'Get stronger on the big lifts — lower reps, heavy weights' },
    { key: 'recomp',          label: 'Body Recomp',     desc: 'Build muscle while losing fat — higher reps, moderate effort' },
  ];

  const EQUIPMENT_GROUPS = [
    {
      label: 'Free Weights',
      items: [
        { key: 'barbell',    label: 'Barbell' },
        { key: 'dumbbells',  label: 'Dumbbells' },
        { key: 'ez_bar',     label: 'EZ Bar' },
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
    { value: 'beginner',     label: 'Beginner',     desc: 'Less than 1 year of consistent training' },
    { value: 'intermediate', label: 'Intermediate', desc: '1–3 years; past the beginner gains phase' },
    { value: 'advanced',     label: 'Advanced',     desc: '3+ years; slow, hard-earned progress' },
  ];

  const SESSION_LENGTHS = [30, 45, 60, 75, 90];

  function toggleEquip(key) {
    if (equipment.has(key)) equipment.delete(key);
    else equipment.add(key);
    equipment = new Set(equipment);
  }

  function markDone() {
    if (typeof localStorage !== 'undefined') localStorage.setItem('lf_setup_done', '1');
  }

  async function finish(destination) {
    saving = true;
    try {
      await api.profile.update({
        display_name: displayName.trim() || 'Lifter',
        unit_preference: unitPreference,
        sex,
        experience_level: experienceLevel,
        preferred_session_minutes: preferredSessionMinutes,
      });
      await api.profile.updateEquipment([...equipment]);
    } catch { }
    markDone();
    saving = false;
    goto(destination);
  }

  function skip() {
    markDone();
    goto('/');
  }
</script>

<svelte:head><title>Setup — LiftForge</title></svelte:head>

<div class="setup-overlay">
  <div class="setup-card">

    <!-- Header row: progress + skip -->
    <div class="setup-header">
      <div class="progress-dots">
        {#each Array(TOTAL) as _, i}
          <span class="dot" class:active={i + 1 === step} class:done={i + 1 < step}></span>
        {/each}
      </div>
      {#if step < 4}
        <button class="skip-btn" on:click={skip}>Skip setup</button>
      {/if}
    </div>

    <!-- ── Step 1: Welcome + Goal ── -->
    {#if step === 1}
      <div class="step-content">
        <div class="step-eyebrow">Step 1 of 4</div>
        <h1 class="step-heading">Welcome to LiftForge</h1>
        <p class="step-sub">Let's set up your training in about 2 minutes.</p>

        <label class="field-label" for="dname">What should we call you?</label>
        <input id="dname" class="setup-input" bind:value={displayName} placeholder="Your name" maxlength="40" />

        <div class="field-label" style="margin-top:24px;">What's your main training goal?</div>
        <div class="goal-grid">
          {#each GOALS as g}
            <button
              class="goal-btn"
              class:selected={goal === g.key}
              on:click={() => goal = g.key}
            >
              <div class="goal-name">{g.label}</div>
              <div class="goal-desc">{g.desc}</div>
            </button>
          {/each}
        </div>
      </div>
      <div class="step-nav">
        <span></span>
        <button class="btn-primary" on:click={() => step = 2}>Next →</button>
      </div>
    {/if}

    <!-- ── Step 2: Equipment ── -->
    {#if step === 2}
      <div class="step-content">
        <div class="step-eyebrow">Step 2 of 4</div>
        <h1 class="step-heading">What do you have access to?</h1>
        <p class="step-sub">This controls which exercises appear in your programs.</p>

        {#each EQUIPMENT_GROUPS as group}
          <div class="equip-group-label">{group.label}</div>
          <div class="equip-grid">
            {#each group.items as item}
              <button
                class="equip-btn"
                class:selected={equipment.has(item.key)}
                on:click={() => toggleEquip(item.key)}
              >
                {item.label}
              </button>
            {/each}
          </div>
        {/each}
      </div>
      <div class="step-nav">
        <button class="btn-ghost" on:click={() => step = 1}>← Back</button>
        <button class="btn-primary" on:click={() => step = 3}>Next →</button>
      </div>
    {/if}

    <!-- ── Step 3: About You ── -->
    {#if step === 3}
      <div class="step-content">
        <div class="step-eyebrow">Step 3 of 4</div>
        <h1 class="step-heading">A bit about you</h1>
        <p class="step-sub">Used to tailor programs and strength grading to you.</p>

        <div class="field-label">Weight units</div>
        <div class="toggle-row">
          <button class="toggle-btn" class:active={unitPreference === 'lbs'} on:click={() => unitPreference = 'lbs'}>lbs</button>
          <button class="toggle-btn" class:active={unitPreference === 'kg'} on:click={() => unitPreference = 'kg'}>kg</button>
        </div>

        <div class="field-label" style="margin-top:20px;">Sex
          <span class="field-hint"> — used for strength level grading</span>
        </div>
        <div class="toggle-row">
          <button class="toggle-btn" class:active={sex === 'male'} on:click={() => sex = 'male'}>Male</button>
          <button class="toggle-btn" class:active={sex === 'female'} on:click={() => sex = 'female'}>Female</button>
          <button class="toggle-btn" class:active={sex === null} on:click={() => sex = null}>Prefer not to say</button>
        </div>

        <div class="field-label" style="margin-top:20px;">Training experience</div>
        <div class="exp-stack">
          {#each EXP_LEVELS as lvl}
            <button
              class="exp-btn"
              class:selected={experienceLevel === lvl.value}
              on:click={() => experienceLevel = lvl.value}
            >
              <span class="exp-name">{lvl.label}</span>
              <span class="exp-desc">{lvl.desc}</span>
            </button>
          {/each}
        </div>

        <div class="field-label" style="margin-top:20px;">Preferred session length</div>
        <div class="toggle-row">
          {#each SESSION_LENGTHS as mins}
            <button class="toggle-btn" class:active={preferredSessionMinutes === mins} on:click={() => preferredSessionMinutes = mins}>{mins}m</button>
          {/each}
        </div>
      </div>
      <div class="step-nav">
        <button class="btn-ghost" on:click={() => step = 2}>← Back</button>
        <button class="btn-primary" on:click={() => step = 4}>Next →</button>
      </div>
    {/if}

    <!-- ── Step 4: Let's go ── -->
    {#if step === 4}
      <div class="step-content">
        <div class="step-eyebrow">You're all set</div>
        <h1 class="step-heading">Let's go{displayName.trim() ? `, ${displayName.trim()}` : ''}.</h1>
        <p class="step-sub">Your profile is saved. You can change anything in Settings at any time.</p>

        <div class="cta-stack">
          <button class="btn-primary cta-big" on:click={() => finish('/program/builder')} disabled={saving}>
            {saving ? 'Saving…' : 'Build my first program →'}
          </button>
          <button class="btn-ghost cta-big" on:click={() => finish('/log')} disabled={saving}>
            Start a free workout →
          </button>
          <button class="btn-ghost cta-big" on:click={() => finish('/')} disabled={saving}>
            Take me to the home screen
          </button>
        </div>

        <p class="settings-hint">You can always revisit this in <a href="/settings" class="settings-link">⚙ Settings</a>.</p>
      </div>
      <div class="step-nav">
        <button class="btn-ghost" on:click={() => step = 3}>← Back</button>
        <span></span>
      </div>
    {/if}

  </div>
</div>

<style>
  .setup-overlay {
    position: fixed;
    inset: 0;
    z-index: 999;
    background: var(--bg, #0a0a10);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    overflow-y: auto;
    padding: 24px 16px 40px;
  }

  .setup-card {
    width: 100%;
    max-width: 480px;
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .setup-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 32px;
  }

  .progress-dots {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--bdr, #22222e);
    transition: background 0.2s, transform 0.2s;
  }
  .dot.done { background: var(--accent, #e8365d); opacity: 0.5; }
  .dot.active { background: var(--accent, #e8365d); transform: scale(1.25); }

  .skip-btn {
    background: none;
    border: none;
    color: var(--muted, #6868a0);
    font-size: 13px;
    cursor: pointer;
    padding: 4px 8px;
  }
  .skip-btn:hover { color: var(--text, #f8f8ff); }

  .step-content {
    flex: 1;
  }

  .step-eyebrow {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent, #e8365d);
    margin-bottom: 8px;
  }

  .step-heading {
    font-family: var(--serif, 'DM Serif Display'), serif;
    font-size: 1.8rem;
    font-weight: 400;
    color: var(--text, #f8f8ff);
    margin: 0 0 8px;
    line-height: 1.2;
  }

  .step-sub {
    font-size: 0.88rem;
    color: var(--muted, #6868a0);
    margin: 0 0 24px;
    line-height: 1.5;
  }

  .field-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text, #f8f8ff);
    margin-bottom: 8px;
    display: block;
  }

  .field-hint {
    font-size: 12px;
    font-weight: 400;
    color: var(--muted, #6868a0);
  }

  .setup-input {
    width: 100%;
    background: var(--surf, #12121a);
    border: 1px solid var(--bdr, #22222e);
    border-radius: var(--radius, 6px);
    color: var(--text, #f8f8ff);
    font-size: 15px;
    padding: 10px 12px;
    box-sizing: border-box;
    transition: border-color 0.15s;
  }
  .setup-input:focus {
    outline: none;
    border-color: var(--accent, #e8365d);
  }

  /* Goal grid */
  .goal-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .goal-btn {
    background: var(--surf, #12121a);
    border: 1.5px solid var(--bdr, #22222e);
    border-radius: var(--radius-lg, 14px);
    padding: 12px 14px;
    text-align: left;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
  }
  .goal-btn.selected {
    border-color: var(--accent, #e8365d);
    background: rgba(232,54,93,0.08);
  }
  .goal-btn:hover:not(.selected) { border-color: var(--muted, #6868a0); }

  .goal-name {
    font-family: var(--sans, 'DM Sans'), sans-serif;
    font-size: 13px;
    font-weight: 700;
    color: var(--text, #f8f8ff);
    margin-bottom: 4px;
  }
  .goal-desc {
    font-size: 11px;
    color: var(--muted, #6868a0);
    line-height: 1.4;
  }

  /* Equipment */
  .equip-group-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted, #6868a0);
    margin: 16px 0 6px;
  }
  .equip-group-label:first-of-type { margin-top: 0; }

  .equip-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .equip-btn {
    background: var(--surf, #12121a);
    border: 1px solid var(--bdr, #22222e);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 13px;
    color: var(--muted, #6868a0);
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s, background 0.15s;
  }
  .equip-btn.selected {
    border-color: var(--accent, #e8365d);
    color: var(--text, #f8f8ff);
    background: rgba(232,54,93,0.08);
  }
  .equip-btn:hover:not(.selected) { color: var(--text, #f8f8ff); }

  /* Toggle row */
  .toggle-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .toggle-btn {
    background: var(--surf, #12121a);
    border: 1px solid var(--bdr, #22222e);
    border-radius: var(--radius, 6px);
    padding: 8px 16px;
    font-size: 13px;
    color: var(--muted, #6868a0);
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s, background 0.15s;
  }
  .toggle-btn.active {
    border-color: var(--accent, #e8365d);
    color: var(--text, #f8f8ff);
    background: rgba(232,54,93,0.1);
    font-weight: 600;
  }

  /* Experience levels */
  .exp-stack {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .exp-btn {
    background: var(--surf, #12121a);
    border: 1.5px solid var(--bdr, #22222e);
    border-radius: var(--radius, 6px);
    padding: 10px 14px;
    text-align: left;
    cursor: pointer;
    display: flex;
    align-items: baseline;
    gap: 10px;
    transition: border-color 0.15s, background 0.15s;
  }
  .exp-btn.selected {
    border-color: var(--accent, #e8365d);
    background: rgba(232,54,93,0.08);
  }
  .exp-btn:hover:not(.selected) { border-color: var(--muted, #6868a0); }

  .exp-name {
    font-size: 13px;
    font-weight: 700;
    color: var(--text, #f8f8ff);
    flex-shrink: 0;
  }
  .exp-desc {
    font-size: 12px;
    color: var(--muted, #6868a0);
  }

  /* Step nav */
  .step-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 28px;
    margin-top: auto;
  }

  .btn-primary {
    background: var(--accent, #e8365d);
    border: none;
    border-radius: var(--radius, 6px);
    color: #fff;
    font-size: 14px;
    font-weight: 700;
    padding: 12px 24px;
    cursor: pointer;
    transition: opacity 0.15s;
  }
  .btn-primary:hover:not(:disabled) { opacity: 0.85; }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

  .btn-ghost {
    background: none;
    border: 1px solid var(--bdr, #22222e);
    border-radius: var(--radius, 6px);
    color: var(--muted, #6868a0);
    font-size: 14px;
    padding: 12px 20px;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
  }
  .btn-ghost:hover:not(:disabled) { color: var(--text, #f8f8ff); border-color: var(--muted, #6868a0); }
  .btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }

  /* Step 4 CTAs */
  .cta-stack {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 28px;
  }
  .cta-big { width: 100%; font-size: 15px; padding: 14px 20px; }

  .settings-hint {
    font-size: 12px;
    color: var(--muted, #6868a0);
    margin-top: 20px;
    text-align: center;
  }
  .settings-link {
    color: var(--muted, #6868a0);
  }
  .settings-link:hover { color: var(--text, #f8f8ff); }
</style>
