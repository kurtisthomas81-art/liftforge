<script>
  import { toasts } from './stores.js';
</script>

{#if $toasts.length > 0}
  <div class="toast-container" aria-live="polite" aria-atomic="false">
    {#each $toasts as toast (toast.id)}
      <div class="toast toast-{toast.type}">
        {toast.message}
      </div>
    {/each}
  </div>
{/if}

<style>
  .toast-container {
    position: fixed;
    bottom: calc(var(--tab-h, 60px) + 12px);
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    gap: 6px;
    z-index: 1000;
    pointer-events: none;
    width: max-content;
    max-width: calc(100vw - 32px);
  }

  .toast {
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 600;
    font-family: var(--sans);
    text-align: center;
    animation: toast-in 0.18s ease;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  }

  .toast-success {
    background: var(--success);
    color: #0a0a10;
  }

  .toast-error {
    background: var(--danger, #e8365d);
    color: #fff;
  }

  @keyframes toast-in {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
</style>
