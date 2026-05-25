<script setup>
import { computed, onMounted } from 'vue';
import { useChat } from '@/stores/chat.js';
import ChatWindow from '@/components/ChatWindow.vue';
import ChatInput from '@/components/ChatInput.vue';

/**
 * Minimal, borderless chat view designed to be embedded inside an <iframe>.
 * It also listens to postMessage events from the host page so the embedder
 * can drive it:
 *
 *   parent.postMessage({ type: 'ragwebui:send', text: 'hello' }, '*')
 *   parent.postMessage({ type: 'ragwebui:reset' }, '*')
 *   parent.postMessage({ type: 'ragwebui:set-theme', preset: 'dark' }, '*')
 */

const chat = useChat();
const active = computed(() => chat.active);

onMounted(() => {
  chat.ensureActive();
  window.addEventListener('message', onMessage);
});

function onMessage(e) {
  const d = e.data;
  if (!d || typeof d !== 'object') return;
  if (d.type === 'ragwebui:send' && typeof d.text === 'string') {
    chat.send(d.text);
  } else if (d.type === 'ragwebui:reset') {
    chat.newConversation();
  } else if (d.type === 'ragwebui:set-theme') {
    // Lazy import to avoid circular dep in template
    import('@/stores/settings.js').then(({ useSettings }) => {
      const s = useSettings();
      s.setPreset(d.preset || 'light');
    });
  }
}

function notifyParent(event, payload) {
  try { window.parent?.postMessage({ type: `ragwebui:${event}`, ...payload }, '*'); }
  catch { /* ignore */ }
}

function send(text) {
  chat.send(text);
  notifyParent('sent', { text });
}
function pick(t) { send(t); }
</script>

<template>
  <div class="embed">
    <ChatWindow
      class="w"
      :messages="active?.messages ?? []"
      empty-title="南科知识问答"
      empty-hint="欢迎提问"
      @pick-suggestion="pick"
    />
    <div class="in">
      <ChatInput
        compact
        :streaming="chat.streaming"
        placeholder="有什么问题？"
        @send="send"
        @cancel="chat.cancel"
      />
    </div>
  </div>
</template>

<style scoped>
.embed {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg);
}
.w { flex: 1; padding: 10px 12px; }
.in { padding: 8px 10px 10px; border-top: 1px solid var(--border); background: var(--bg-elevated); }
</style>
