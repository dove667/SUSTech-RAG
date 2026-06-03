import { defineStore } from 'pinia';
import { useSettings } from './settings.js';
import { chat as chatStream } from '@/utils/chatClient.js';
import { buildApiUrl, fetchWithTimeout } from '@/utils/api.js';

/**
 * A chat conversation is an ordered list of messages. Each message has:
 *   id, role ('user' | 'assistant' | 'system'), blocks: Block[]
 * Each Block has a `type`: 'text' | 'think' | 'tool' | 'image' | 'reference' | 'self_rag_trace' | 'error'
 * The renderer decides how to present each block.
 */

const STORAGE_KEY = 'ragwebui:chats:v1';

function uid(prefix) {
  return `${prefix}_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

function loadConversations() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) ?? [];
  } catch {
    console.warn('[ragwebui] localStorage data corrupted — resetting conversations');
    return [];
  }
}

function createConversation() {
  return {
    id: uid('c'),
    title: '新会话',
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
}

export const useChat = defineStore('chat', {
  state: () => ({
    conversations: loadConversations(),
    activeId: null,
    cancelFn: null,
    streaming: false,
  }),
  getters: {
    active(state) {
      return state.conversations.find(c => c.id === state.activeId) || null;
    },
  },
  actions: {
    persist() {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(this.conversations)); } catch { console.warn('[ragwebui] localStorage quota exceeded — conversations not persisted'); }
    },
    ensureActive() {
      if (this.active) return;
      // 若已有空会话则复用，避免每次刷新都创建新会话
      const empty = this.conversations.find(c => c.messages.length === 0);
      if (empty) {
        this.activeId = empty.id;
        return;
      }
      const c = createConversation();
      this.conversations.unshift(c);
      this.activeId = c.id;
      this.persist();
    },
    newConversation() {
      const c = createConversation();
      this.conversations.unshift(c);
      this.activeId = c.id;
      this.persist();
      return c;
    },
    selectConversation(id) {
      this.activeId = id;
    },
    deleteConversation(id) {
      this.conversations = this.conversations.filter(c => c.id !== id);
      if (this.activeId === id) this.activeId = this.conversations[0]?.id ?? null;
      this.persist();
    },
    renameConversation(id, title) {
      const c = this.conversations.find(x => x.id === id);
      if (c) { c.title = title; c.updatedAt = Date.now(); this.persist(); }
    },
    clearAll() {
      this.conversations = [];
      this.activeId = null;
      this.persist();
    },

    /**
     * Send a user message; returns a promise that resolves when the stream is done.
     */
    async send(text) {
      if (!text?.trim()) return;
      this.ensureActive();
      const conv = this.active;

      const userMsg = {
        id: uid('m'),
        role: 'user',
        blocks: [{ type: 'text', content: text }],
        createdAt: Date.now(),
      };
      conv.messages.push(userMsg);

      const aiMsg = {
        id: uid('m'),
        role: 'assistant',
        blocks: [],
        createdAt: Date.now(),
        loading: true,
      };
      conv.messages.push(aiMsg);
      // MUST use the reactive proxy from the store; raw `aiMsg` mutations won't
      // trigger Vue re-renders (Pinia wraps every pushed object in a Proxy).
      const msg = conv.messages[conv.messages.length - 1];

      if (conv.messages.length === 2) {
        conv.title = text.slice(0, 24) || '新会话';
      }
      conv.updatedAt = Date.now();
      this.persist();

      this.streaming = true;

      // Plain-text messages for the API
      const apiMessages = conv.messages
        .filter(m => m.id !== msg.id)
        .map(m => ({
          role: m.role,
          content: m.blocks.map(b => b.type === 'text' ? b.content : '').join('').trim(),
        }))
        .filter(m => m.content);

      const settings = useSettings();

      const getOrCreateBlock = (type, matcher = () => true) => {
        const found = msg.blocks.find(b => b.type === type && matcher(b));
        if (found) return found;
        const b = { type };
        msg.blocks.push(b);
        // MUST return the reactive proxy from the store, not the raw object.
        // Mutations on the raw object bypass Vue's Proxy traps → no re-render.
        return msg.blocks[msg.blocks.length - 1];
      };

      let currentText = null;
      let currentThink = null;

      const getOrCreateTraceBlock = () => {
        const trace = getOrCreateBlock('self_rag_trace');
        if (!trace.events) trace.events = [];
        return trace;
      };

      const handlers = {
        onStart: () => {
          msg.loading = true;
        },
        onRetrievalDecision: (data) => {
          const trace = getOrCreateTraceBlock();
          trace.mode = data.mode || 'self_rag';
          trace.events.push({
            type: 'retrieval.decision',
            ...data,
          });
        },
        onRetrievalAssessment: (data) => {
          const trace = getOrCreateTraceBlock();
          trace.events.push({
            type: 'retrieval.assessment',
            ...data,
          });
        },
        onSupportDecision: (data) => {
          const trace = getOrCreateTraceBlock();
          trace.events.push({
            type: 'support.decision',
            ...data,
          });
        },
        onThinkDelta: (t) => {
          if (!currentThink || currentThink.closed) {
            msg.blocks.push({ type: 'think', content: '', closed: false });
            // Re-acquire through the reactive array (see getOrCreateBlock).
            currentThink = msg.blocks[msg.blocks.length - 1];
          }
          currentThink.content += t;
        },
        onThinkEnd: () => {
          if (currentThink) currentThink.closed = true;
          currentThink = null;
        },
        onContentDelta: (t) => {
          if (!currentText) {
            msg.blocks.push({ type: 'text', content: '' });
            // Re-acquire through the reactive array (see getOrCreateBlock).
            currentText = msg.blocks[msg.blocks.length - 1];
          }
          currentText.content += t;
        },
        onToolCall: (data) => {
          msg.blocks.push({ type: 'tool', id: data.id, name: data.name, args: data.arguments, result: null });
          currentText = null;
        },
        onToolResult: (data) => {
          const t = [...msg.blocks].reverse().find(b => b.type === 'tool' && b.id === data.id);
          if (t) t.result = data.result;
        },
        onImage: (data) => {
          msg.blocks.push({ type: 'image', url: data.url, alt: data.alt, caption: data.caption });
          currentText = null;
        },
        onReference: (data) => {
          if (msg.blocks.some(b => b.type === 'self_rag_trace')) return;
          const ref = getOrCreateBlock('reference');
          ref.items = [...(ref.items || []), ...(data.items || [])];
        },
        onError: (data) => {
          const code = data?.code || 'error';
          const msgText = data?.message || '发生未知错误';
          const detail = data?.detail ? ` (${data.detail})` : '';
          msg.blocks.push({ type: 'error', level: 'error', message: `[${code}] ${msgText}${detail}` });
        },
        onDone: (data) => {
          msg.usage = data?.usage;
          msg.finishReason = data?.finish_reason;
        },
        onFinish: () => {
          msg.loading = false;
          this.streaming = false;
          this.cancelFn = null;
          conv.updatedAt = Date.now();
          this.persist();
        },
      };

      this.cancelFn = chatStream(
        { settings, messages: apiMessages, conversationId: conv.id },
        handlers,
      );
    },

    cancel() {
      if (this.cancelFn) {
        this.cancelFn();
        this.cancelFn = null;
      }
      this.streaming = false;
      const last = this.active?.messages?.[this.active.messages.length - 1];
      const messageId = last?.id;
      if (last?.loading) {
        last.loading = false;
        last.blocks.push({ type: 'error', level: 'info', message: '用户已中止生成。' });
      }
      // 通知后端中断生成
      if (messageId) {
        const settings = useSettings();
        fetchWithTimeout(buildApiUrl(settings.apiBaseUrl, '/chat/cancel'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(settings.identityId ? { 'X-Identity-ID': settings.identityId } : {}),
          },
          body: JSON.stringify({ message_id: messageId }),
        }, 5000).catch(() => {});
      }
      this.persist();
    },

    regenerate() {
      const conv = this.active;
      if (!conv || conv.messages.length < 2) return;
      // drop last assistant message and resend last user
      const lastAi = [...conv.messages].reverse().find(m => m.role === 'assistant');
      if (lastAi) conv.messages = conv.messages.filter(m => m !== lastAi);
      const lastUser = [...conv.messages].reverse().find(m => m.role === 'user');
      if (lastUser) {
        // Remove it then resend to keep the send() flow simple
        conv.messages = conv.messages.filter(m => m !== lastUser);
        this.send(lastUser.blocks.map(b => b.content).join(''));
      }
    },
  },
});
