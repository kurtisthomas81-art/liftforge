<script>
  import { onMount, afterUpdate, tick } from 'svelte';
  import { api } from '$lib/api.js';
  import { activeSession } from '$lib/stores.js';

  const SUGGESTIONS = [
    "How's my recovery looking?",
    "Should I deload?",
    "How did my last session go?",
    "What should I focus on this week?",
  ];

  let messages = [
    {
      role: 'assistant',
      content: "Hey — I'm your AI coach. Ask me anything about your training, recovery, or current program. I have access to your full training data, so I can give you grounded answers based on what you've actually logged.",
    },
  ];
  let input = '';
  let sending = false;
  let messagesEl;
  let contextSummary = null;

  async function sendMessage(text) {
    text = (text || input).trim();
    if (!text || sending) return;
    input = '';
    sending = true;

    messages = [...messages, { role: 'user', content: text }];

    const context_type = $activeSession ? 'session' : 'general';

    try {
      const res = await api.chat.send(text, context_type);
      messages = [...messages, { role: 'assistant', content: res.reply }];
      if (res.context_summary) contextSummary = res.context_summary;
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
    messages = [messages[0]];
  }

  $: showSuggestions = messages.length === 1 && !sending;

  afterUpdate(() => {
    if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
  });
</script>

<svelte:head><title>AI Coach — LiftForge</title></svelte:head>

<div style="max-width:720px; height:calc(100vh - 96px); display:flex; flex-direction:column;">

  <!-- Header -->
  <div class="flex items-center justify-between mb-1">
    <div>
      <h2 style="font-size:20px; font-weight:700;">AI Coach</h2>
      <div style="font-size:12px; color:var(--text-muted); margin-top:2px; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
        <span>Powered by Ollama · llama3.1:8b</span>
        {#if contextSummary?.mesocycle}
          <span style="color:var(--border);">·</span>
          <span style="color:var(--primary);">{contextSummary.mesocycle}</span>
        {/if}
        {#if contextSummary?.fatigue_score != null}
          <span style="color:var(--border);">·</span>
          <span style="color:{contextSummary.fatigue_level === 'critical' ? 'var(--danger)' : contextSummary.fatigue_level === 'high' ? 'var(--warn)' : 'var(--text-muted)'};">
            fatigue {contextSummary.fatigue_score}/10
          </span>
        {/if}
        {#if contextSummary?.injury_count > 0}
          <span style="color:var(--border);">·</span>
          <span style="color:var(--danger);">{contextSummary.injury_count} injury active</span>
        {/if}
        {#if $activeSession}
          <span style="color:var(--border);">·</span>
          <span style="color:var(--primary);">live session context</span>
        {/if}
      </div>
    </div>
    <button class="btn-ghost btn-sm" on:click={clearConversation}>Clear</button>
  </div>

  <!-- Safety disclaimer -->
  <div style="font-size:11px; color:var(--text-muted); padding:6px 10px; background:var(--surface); border:1px solid var(--border); border-radius:6px; margin-bottom:12px; line-height:1.4;">
    AI recommendations are informational only and based on your logged data.
    For injury concerns, consult a sports medicine professional.
  </div>

  <!-- Messages -->
  <div
    bind:this={messagesEl}
    style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:12px; padding-bottom:8px;"
  >
    {#each messages as msg}
      <div style="display:flex; justify-content:{msg.role === 'user' ? 'flex-end' : 'flex-start'};">
        <div style="
          max-width:85%; padding:12px 14px;
          border-radius:{msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px'};
          background:{msg.role === 'user' ? 'rgba(232,160,64,0.12)' : 'var(--surface)'};
          border:1px solid {msg.role === 'user' ? 'rgba(232,160,64,0.25)' : 'var(--border)'};
          color:var(--text); font-size:14px; line-height:1.6; white-space:pre-wrap;
        ">
          {msg.content}
        </div>
      </div>
    {/each}

    <!-- Suggestion chips (shown only before first message) -->
    {#if showSuggestions}
      <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:4px;">
        {#each SUGGESTIONS as s}
          <button
            class="suggestion-chip"
            on:click={() => sendMessage(s)}
          >{s}</button>
        {/each}
      </div>
    {/if}

    {#if sending}
      <div style="display:flex; justify-content:flex-start;">
        <div style="background:var(--surface); border:1px solid var(--border); border-radius:12px 12px 12px 2px; padding:14px 16px; display:flex; align-items:center; gap:8px;">
          <div class="spinner" style="width:16px; height:16px;"></div>
          <span style="color:var(--text-muted); font-size:13px;">Thinking…</span>
        </div>
      </div>
    {/if}
  </div>

  <!-- Input -->
  <div style="display:flex; gap:8px; padding-top:12px; border-top:1px solid var(--border);">
    <textarea
      bind:value={input}
      on:keydown={handleKey}
      placeholder="Ask your coach…"
      rows="2"
      style="flex:1; resize:none; padding:10px 12px; font-size:14px; line-height:1.5;"
      disabled={sending}
    ></textarea>
    <button
      class="btn-primary"
      on:click={() => sendMessage()}
      disabled={sending || !input.trim()}
      style="padding:10px 18px; align-self:flex-end;"
    >
      Send
    </button>
  </div>
</div>

<style>
  .suggestion-chip {
    padding: 6px 12px;
    border-radius: 16px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-muted);
    font-size: 12px;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }
  .suggestion-chip:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
</style>
