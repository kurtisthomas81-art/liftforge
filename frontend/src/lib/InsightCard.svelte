<script>
  import { goto } from '$app/navigation';
  export let card;
  let dismissed = false;

  const TYPE_COLOR = {
    recovery: 'var(--success)',
    overload:  'var(--accent)',
    deload:    'var(--warn)',
    streak:    'var(--warn)',
    goal:      '#4a9eff',
    volume:    'var(--muted)',
  };

  $: color = TYPE_COLOR[card.type] || 'var(--muted)';
</script>

{#if !dismissed}
  <div class="insight-card" style="border-left-color:{color}">
    <div class="insight-content">
      <div class="insight-headline">{card.headline}</div>
      <div class="insight-body">{card.body}</div>
      {#if card.action}
        <button class="insight-action" style="color:{color};border-color:{color}40"
          on:click={() => goto(card.action.url)}>
          {card.action.label} →
        </button>
      {/if}
    </div>
    <button class="insight-dismiss" aria-label="Dismiss" on:click={() => dismissed = true}>×</button>
  </div>
{/if}

<style>
  .insight-card {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-left: 3px solid;
    border-radius: var(--radius-lg);
    padding: 14px 12px 14px 14px;
    margin-bottom: 8px;
  }

  .insight-content { flex: 1; min-width: 0; }

  .insight-headline {
    font-family: var(--sans);
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 4px;
  }

  .insight-body {
    font-size: 0.78rem;
    color: var(--muted);
    line-height: 1.5;
    margin-bottom: 8px;
  }

  .insight-action {
    background: transparent;
    border: 1px solid;
    border-radius: var(--radius);
    padding: 5px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .insight-action:hover { opacity: 0.75; }

  .insight-dismiss {
    background: none;
    border: none;
    color: var(--muted);
    font-size: 1.1rem;
    cursor: pointer;
    padding: 0 2px;
    line-height: 1;
    flex-shrink: 0;
    margin-top: -2px;
  }

  .insight-dismiss:hover { color: var(--text); }
</style>
