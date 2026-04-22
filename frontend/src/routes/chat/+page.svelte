<script>
  import { onMount, afterUpdate, tick } from 'svelte';
  import { api } from '$lib/api.js';
  import { activeSession } from '$lib/stores.js';

  let messages = [
    {
      role: 'assistant',
      content: "Hey — I'm your AI coach. Ask me anything about training, programming, exercise selection, or your recent sessions. I understand RP Strength methodology, RIR autoregulation, and evidence-based hypertrophy principles.",
    },
  ];
  let input = '';
  let sending = false;
  let messagesEl;

  async function sendMessage() {
    const text = input.trim();
    if (!text || sending) return;
    input = '';
    sending = true;

    messages = [...messages, { role: 'user', content: text }];

    // Determine context_type
    const context_type = $activeSession ? 'session' : 'general';

    try {
      const res = await api.chat.send(text, context_type);
      messages = [...messages, { role: 'assistant', content: res.reply }];
    } catch (e) {
      messages = [...messages, {
        role: 'assistant',
        content: 'Something went wrong reaching the AI coach. Check your connection.',
      }];
    }

    sending = false;
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function clearConversation() {
    messages = [messages[0]]; // keep the intro message
  }

  afterUpdate(() => {
    if (messagesEl) {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  });
</script>

<svelte:head><title>AI Coach — LiftForge</title></svelte:head>

<div style="max-width:720px; height:calc(100vh - 96px); display:flex; flex-direction:column;">
  <div class="flex items-center justify-between mb-4">
    <div>
      <h2 style="font-size:20px; font-weight:700;">AI Coach</h2>
      <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">
        Powered by Ollama · llama3.1:8b
        {#if $activeSession}
          · <span style="color:var(--primary);">Using current session context</span>
        {/if}
      </div>
    </div>
    <button class="btn-ghost btn-sm" on:click={clearConversation}>Clear</button>
  </div>

  <!-- Messages -->
  <div
    bind:this={messagesEl}
    style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:12px; padding-bottom:8px;"
  >
    {#each messages as msg}
      <div
        style="
          display:flex;
          justify-content: {msg.role === 'user' ? 'flex-end' : 'flex-start'};
        "
      >
        <div
          style="
            max-width:85%;
            padding:12px 14px;
            border-radius:{msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px'};
            background:{msg.role === 'user' ? 'rgba(232,160,64,0.12)' : 'var(--surface)'};
            border:1px solid {msg.role === 'user' ? 'rgba(232,160,64,0.25)' : 'var(--border)'};
            color:var(--text);
            font-size:14px;
            line-height:1.6;
            white-space:pre-wrap;
          "
        >
          {msg.content}
        </div>
      </div>
    {/each}

    {#if sending}
      <div style="display:flex; justify-content:flex-start;">
        <div style="background:var(--surface); border:1px solid var(--border); border-radius:12px 12px 12px 2px; padding:14px 16px; display:flex; align-items:center; gap:8px;">
          <div class="spinner" style="width:16px; height:16px;"></div>
          <span style="color:var(--text-muted); font-size:13px;">Thinking...</span>
        </div>
      </div>
    {/if}
  </div>

  <!-- Input -->
  <div style="display:flex; gap:8px; padding-top:12px; border-top:1px solid var(--border);">
    <textarea
      bind:value={input}
      on:keydown={handleKey}
      placeholder="Ask your coach..."
      rows="2"
      style="flex:1; resize:none; padding:10px 12px; font-size:14px; line-height:1.5;"
      disabled={sending}
    ></textarea>
    <button
      class="btn-primary"
      on:click={sendMessage}
      disabled={sending || !input.trim()}
      style="padding:10px 18px; align-self:flex-end;"
    >
      Send
    </button>
  </div>
</div>
