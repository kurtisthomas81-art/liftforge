<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';

  let step = 1;
  let loading = true;
  let creating = false;
  let error = null;

  // Step 1
  let selectedDays = null;

  // Step 2
  let splitGroups = [];
  let selectedSplit = null;
  let isCustom = false;
  let customDays = [];   // [{ name: '', muscle_focus: [] }]

  // Step 3
  let selectedGoal = 'hypertrophy';
  let selectedWeeks = 5;
  let startDate = new Date().toISOString().slice(0, 10);
  let mesoName = '';
  let daysOfWeek = [];   // array of 0-6 per split day

  // Step 4 (review)
  let previewData = null;
  let previewLoading = false;

  const DOW_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const ALL_MUSCLES = ['chest', 'back', 'quads', 'hamstrings', 'glutes', 'shoulders',
                       'biceps', 'triceps', 'calves', 'abs', 'lats', 'traps'];
  const GOALS = [
    { key: 'hypertrophy', label: 'Hypertrophy', desc: '8-12 reps, RIR 2' },
    { key: 'strength',    label: 'Strength',    desc: '3-6 reps, RIR 1' },
    { key: 'recomp',      label: 'Recomp',      desc: '10-15 reps, RIR 2-3' },
  ];

  onMount(async () => {
    try {
      const raw = await api.programs.getSplits();
      splitGroups = raw;
    } catch (e) {
      error = e.message;
    }
    loading = false;
    // Default name
    const now = new Date();
    mesoName = `Mesocycle ${now.toLocaleString('default', { month: 'long' })} ${now.getFullYear()}`;
  });

  function selectDays(n) {
    selectedDays = n;
    selectedSplit = null;
    isCustom = false;
    customDays = Array.from({ length: n }, (_, i) => ({ name: `Day ${i + 1}`, muscle_focus: [] }));
    daysOfWeek = Array.from({ length: n }, (_, i) => Math.min(i * Math.floor(7 / n), 6));
    step = 2;
  }

  function selectSplit(split) {
    isCustom = false;
    selectedSplit = split;
    step = 3;
  }

  function selectCustom() {
    isCustom = true;
    selectedSplit = null;
    customDays = Array.from({ length: selectedDays }, (_, i) => ({ name: `Day ${i + 1}`, muscle_focus: [] }));
  }

  function toggleMuscleForDay(dayIdx, muscle) {
    const day = customDays[dayIdx];
    if (day.muscle_focus.includes(muscle)) {
      day.muscle_focus = day.muscle_focus.filter(m => m !== muscle);
    } else {
      day.muscle_focus = [...day.muscle_focus, muscle];
    }
    customDays = [...customDays];
  }

  function filteredSplits() {
    const group = splitGroups.find(g => g.days_per_week === selectedDays);
    return group ? group.templates : [];
  }

  async function goToReview() {
    step = 4;
  }

  async function createMesocycle() {
    creating = true;
    error = null;
    try {
      const payload = {
        goal: selectedGoal,
        weeks: selectedWeeks,
        start_date: startDate,
        name: mesoName,
        days_of_week: daysOfWeek,
      };
      if (isCustom) {
        payload.custom_days = customDays;
      } else {
        payload.split_slug = selectedSplit.slug;
      }
      await api.programs.createMesocycle(payload);
      goto('/program');
    } catch (e) {
      error = e.message;
    }
    creating = false;
  }

  function stepLabel(n) {
    if (step > n) return '✓';
    return n;
  }
</script>

<svelte:head><title>Build Program — LiftForge</title></svelte:head>

<div style="max-width:720px;">
  <div class="flex items-center gap-3 mb-5">
    <a href="/program" class="btn-ghost btn-sm">← Back</a>
    <h2 style="font-size:20px; font-weight:700;">Build Mesocycle</h2>
  </div>

  <!-- Step indicator -->
  <div style="display:flex; align-items:center; gap:0; margin-bottom:28px;">
    {#each [1,2,3,4] as n}
      <div style="display:flex; align-items:center; flex:1;">
        <div style="width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; background:{step >= n ? 'var(--primary)' : 'var(--surface-2)'}; color:{step >= n ? '#000' : 'var(--text-muted)'}; border:2px solid {step >= n ? 'var(--primary)' : 'var(--border)'}; flex-shrink:0; transition:all 0.2s;">
          {stepLabel(n)}
        </div>
        {#if n < 4}
          <div style="flex:1; height:2px; background:{step > n ? 'var(--primary)' : 'var(--border)'}; transition:background 0.2s;"></div>
        {/if}
      </div>
    {/each}
  </div>

  {#if loading}
    <div class="flex items-center gap-3" style="padding:32px 0;">
      <div class="spinner"></div>
    </div>

  {:else if step === 1}
    <!-- Step 1: Days per week -->
    <div class="card">
      <div class="section-title mb-4">How many days per week?</div>
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        {#each [2, 3, 4, 5] as n}
          <button
            on:click={() => selectDays(n)}
            style="flex:1; min-width:80px; padding:20px 12px; border-radius:8px; border:2px solid {selectedDays === n ? 'var(--primary)' : 'var(--border)'}; background:{selectedDays === n ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:{selectedDays === n ? 'var(--primary)' : 'var(--text)'}; font-size:24px; font-weight:700; cursor:pointer; transition:all 0.15s;"
          >
            {n}
            <div style="font-size:11px; font-weight:400; margin-top:4px; color:var(--text-muted);">days / week</div>
          </button>
        {/each}
      </div>
    </div>

  {:else if step === 2}
    <!-- Step 2: Choose split -->
    <div class="card">
      <div class="flex items-center gap-3 mb-4">
        <button class="btn-ghost btn-sm" on:click={() => step = 1}>← Back</button>
        <div class="section-title">{selectedDays}-Day Splits</div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
        {#each filteredSplits() as split}
          <button
            on:click={() => selectSplit(split)}
            style="text-align:left; padding:16px; border-radius:8px; border:2px solid {selectedSplit?.slug === split.slug ? 'var(--primary)' : 'var(--border)'}; background:{selectedSplit?.slug === split.slug ? 'rgba(232,160,64,0.07)' : 'var(--surface-2)'}; cursor:pointer; transition:all 0.15s; position:relative;"
          >
            {#if split.is_recommended}
              <span style="position:absolute; top:8px; right:8px; font-size:14px;" title="Recommended">⭐</span>
            {/if}
            <div style="font-weight:600; font-size:13px; color:var(--text); margin-bottom:4px;">{split.name}</div>
            <div style="font-size:11px; color:var(--primary); margin-bottom:6px;">{split.frequency_note}</div>
            <div style="font-size:11px; color:var(--text-muted); line-height:1.5;">{split.description}</div>
          </button>
        {/each}

        <!-- Custom option -->
        <button
          on:click={selectCustom}
          style="text-align:left; padding:16px; border-radius:8px; border:2px solid {isCustom ? 'var(--primary)' : 'var(--border)'}; background:{isCustom ? 'rgba(232,160,64,0.07)' : 'var(--surface-2)'}; cursor:pointer; transition:all 0.15s;"
        >
          <div style="font-weight:600; font-size:13px; color:var(--text); margin-bottom:4px;">Custom Split →</div>
          <div style="font-size:11px; color:var(--text-muted);">Design your own day structure</div>
        </button>
      </div>

      <!-- Custom day editor -->
      {#if isCustom}
        <div style="margin-top:20px; border-top:1px solid var(--border); padding-top:20px;">
          <div class="section-title mb-3">Configure Days</div>
          {#each customDays as day, i}
            <div style="margin-bottom:16px; padding:12px; background:var(--surface-2); border-radius:6px; border:1px solid var(--border);">
              <input
                bind:value={day.name}
                placeholder="Day name (e.g. Push)"
                style="font-weight:600; margin-bottom:10px; width:100%;"
              />
              <div style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">Muscle focus:</div>
              <div style="display:flex; flex-wrap:wrap; gap:6px;">
                {#each ALL_MUSCLES as muscle}
                  <button
                    on:click={() => toggleMuscleForDay(i, muscle)}
                    style="padding:4px 10px; border-radius:3px; border:1px solid {day.muscle_focus.includes(muscle) ? 'var(--primary)' : 'var(--border)'}; background:{day.muscle_focus.includes(muscle) ? 'rgba(232,160,64,0.15)' : 'transparent'}; color:{day.muscle_focus.includes(muscle) ? 'var(--primary)' : 'var(--text-muted)'}; font-size:11px; cursor:pointer; text-transform:capitalize;"
                  >
                    {muscle}
                  </button>
                {/each}
              </div>
            </div>
          {/each}
          <button class="btn-primary" on:click={() => step = 3}>Continue →</button>
        </div>
      {/if}
    </div>

  {:else if step === 3}
    <!-- Step 3: Goal & duration -->
    <div class="card">
      <div class="flex items-center gap-3 mb-4">
        <button class="btn-ghost btn-sm" on:click={() => step = 2}>← Back</button>
        <div class="section-title">Goal & Duration</div>
      </div>

      <!-- Goal -->
      <div style="margin-bottom:20px;">
        <label style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Training Goal</label>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          {#each GOALS as goal}
            <button
              on:click={() => selectedGoal = goal.key}
              style="flex:1; min-width:100px; padding:14px 10px; border-radius:6px; border:2px solid {selectedGoal === goal.key ? 'var(--primary)' : 'var(--border)'}; background:{selectedGoal === goal.key ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:{selectedGoal === goal.key ? 'var(--primary)' : 'var(--text)'}; cursor:pointer; transition:all 0.15s; text-align:center;"
            >
              <div style="font-weight:700; margin-bottom:4px;">{goal.label}</div>
              <div style="font-size:11px; opacity:0.8;">{goal.desc}</div>
            </button>
          {/each}
        </div>
      </div>

      <!-- Weeks -->
      <div style="margin-bottom:20px;">
        <label style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Duration (weeks)</label>
        <div style="display:flex; gap:10px;">
          {#each [4, 5, 6] as w}
            <button
              on:click={() => selectedWeeks = w}
              style="padding:10px 20px; border-radius:6px; border:2px solid {selectedWeeks === w ? 'var(--primary)' : 'var(--border)'}; background:{selectedWeeks === w ? 'rgba(232,160,64,0.1)' : 'var(--surface-2)'}; color:{selectedWeeks === w ? 'var(--primary)' : 'var(--text)'}; font-weight:700; cursor:pointer; transition:all 0.15s;"
            >
              {w} weeks
            </button>
          {/each}
        </div>
        <div style="font-size:11px; color:var(--text-faint); margin-top:6px;">Week {selectedWeeks} will be a deload week</div>
      </div>

      <!-- Start date -->
      <div style="margin-bottom:20px;">
        <label for="startDate" style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Start Date</label>
        <input id="startDate" type="date" bind:value={startDate} style="width:200px;" />
      </div>

      <!-- Mesocycle name -->
      <div style="margin-bottom:20px;">
        <label for="mesoName" style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Mesocycle Name</label>
        <input id="mesoName" bind:value={mesoName} placeholder="e.g. Mesocycle April 2026" style="width:100%; max-width:400px;" />
      </div>

      <!-- Day of week assignment -->
      <div style="margin-bottom:24px;">
        <label style="font-size:13px; color:var(--text-muted); margin-bottom:8px; display:block;">Training Days</label>
        {#each (isCustom ? customDays : (selectedSplit?.days ?? [])) as day, i}
          <div class="flex items-center gap-3" style="margin-bottom:8px;">
            <span style="font-size:13px; color:var(--text); min-width:130px;">{day.name}</span>
            <select bind:value={daysOfWeek[i]} style="width:120px;">
              {#each DOW_LABELS as label, di}
                <option value={di}>{label}</option>
              {/each}
            </select>
          </div>
        {/each}
      </div>

      <button class="btn-primary" on:click={goToReview}>Review Exercises →</button>
    </div>

  {:else if step === 4}
    <!-- Step 4: Review -->
    <div class="card">
      <div class="flex items-center gap-3 mb-4">
        <button class="btn-ghost btn-sm" on:click={() => step = 3}>← Back</button>
        <div class="section-title">Review & Generate</div>
      </div>

      <div style="margin-bottom:20px; display:flex; flex-direction:column; gap:8px;">
        <div class="flex justify-between" style="font-size:13px;">
          <span style="color:var(--text-muted);">Name</span>
          <span style="font-weight:600;">{mesoName}</span>
        </div>
        <div class="flex justify-between" style="font-size:13px;">
          <span style="color:var(--text-muted);">Split</span>
          <span>{isCustom ? 'Custom' : selectedSplit?.name}</span>
        </div>
        <div class="flex justify-between" style="font-size:13px;">
          <span style="color:var(--text-muted);">Goal</span>
          <span style="text-transform:capitalize;">{selectedGoal}</span>
        </div>
        <div class="flex justify-between" style="font-size:13px;">
          <span style="color:var(--text-muted);">Duration</span>
          <span>{selectedWeeks} weeks (week {selectedWeeks} = deload)</span>
        </div>
        <div class="flex justify-between" style="font-size:13px;">
          <span style="color:var(--text-muted);">Start date</span>
          <span>{startDate}</span>
        </div>
        <div class="flex justify-between" style="font-size:13px;">
          <span style="color:var(--text-muted);">Training days</span>
          <span>
            {#each (isCustom ? customDays : (selectedSplit?.days ?? [])) as day, i}
              {day.name} ({DOW_LABELS[daysOfWeek[i]]})
              {#if i < (isCustom ? customDays.length : selectedSplit?.days?.length ?? 0) - 1}, {/if}
            {/each}
          </span>
        </div>
      </div>

      <div style="background:var(--surface-2); border:1px solid var(--border); border-radius:6px; padding:12px; margin-bottom:20px; font-size:12px; color:var(--text-muted); line-height:1.6;">
        Exercises will be auto-selected based on your available equipment and volume landmarks, starting at MEV and progressing toward MRV over the cycle. You can adjust exercises after creation.
      </div>

      {#if error}
        <div style="color:var(--danger); font-size:13px; margin-bottom:12px;">{error}</div>
      {/if}

      <button class="btn-primary" on:click={createMesocycle} disabled={creating}
        style="padding:12px 28px; font-size:15px;">
        {creating ? 'Building...' : 'Generate Mesocycle'}
      </button>
    </div>
  {/if}
</div>
