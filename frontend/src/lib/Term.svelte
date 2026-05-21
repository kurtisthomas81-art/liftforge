<script>
  import { TERMS } from './terms.js';
  export let t = '';

  $: term = TERMS[t] || null;

  let open = false;

  function toggle() {
    open = !open;
  }

  function onKeydown(e) {
    if (e.key === 'Escape') open = false;
  }

  function clickOutside(node) {
    function handleClick(e) {
      if (!node.contains(e.target)) open = false;
    }
    document.addEventListener('click', handleClick, true);
    return { destroy() { document.removeEventListener('click', handleClick, true); } };
  }
</script>

<svelte:window on:keydown={onKeydown} />

{#if term}
  <span class="term-wrap" use:clickOutside>
    <button
      class="term-trigger"
      type="button"
      aria-label="{term.full} — tap for definition"
      on:click|stopPropagation={toggle}
    >{term.short}</button>

    {#if open}
      <span class="term-popover" role="tooltip">
        <strong>{term.full}</strong>
        <span class="term-def">{term.def}</span>
      </span>
    {/if}
  </span>
{/if}

<style>
  .term-wrap {
    position: relative;
    display: inline-block;
  }

  .term-trigger {
    background: none;
    border: none;
    padding: 0;
    color: var(--accent);
    font: inherit;
    font-size: inherit;
    cursor: pointer;
    border-bottom: 1px dotted var(--accent);
    line-height: inherit;
  }

  .term-trigger:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
    border-radius: 2px;
  }

  .term-popover {
    position: absolute;
    bottom: calc(100% + 6px);
    left: 50%;
    transform: translateX(-50%);
    background: var(--surf);
    border: 1px solid var(--bdr);
    border-radius: var(--radius);
    padding: 10px 12px;
    width: 240px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    z-index: 200;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    pointer-events: none;
  }

  .term-popover strong {
    font-size: 0.75rem;
    color: var(--accent);
    font-family: var(--sans);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .term-def {
    font-size: 0.78rem;
    color: var(--text);
    line-height: 1.45;
    font-family: var(--sans);
  }
</style>
