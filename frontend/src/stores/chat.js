import { defineStore } from 'pinia';
import { useSettings } from './settings.js';
import { chat as chatStream } from '@/utils/chatClient.js';

/**
 * A chat conversation is an ordered list of messages. Each message has:
 *   id, role ('user' | 'assistant' | 'system'), blocks: Block[]
 * Each Block has a `type`: 'text' | 'think' | 'tool' | 'image' | 'reference' | 'error'
 * The renderer decides how to present each block.
 */

const STORAGE_KEY = 'ragwebui:chats:v1';

function uid(prefix) {
  return `${prefix}_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

function loadConversations() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? []; }
  catch { return []; }
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
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(this.conversations)); } catch { /* quota */ }
    },
    ensureActive() {
      if (!this.active) {
        const c = createConversation();
        this.conversations.unshift(c);
        this.activeId = c.id;
        this.persist();
      }
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
      if (conv.messages.length === 2) {
        conv.title = text.slice(0, 24) || '新会话';
      }
      conv.updatedAt = Date.now();
      this.persist();

      this.streaming = true;

      // Plain-text messages for the API
      const apiMessages = conv.messages
        .filter(m => m !== aiMsg)
        .map(m => ({
          role: m.role,
          content: m.blocks.map(b => b.type === 'text' ? b.content : '').join('').trim(),
        }))
        .filter(m => m.content);

      const settings = useSettings();

      const getOrCreateBlock = (type, matcher = () => true) => {
        const found = aiMsg.blocks.find(b => b.type === type && matcher(b));
        if (found) return found;
        const b = { type };
        aiMsg.blocks.push(b);
        return b;
      };

      let currentText = null;
      let currentThink = null;

      const handlers = {
        onStart: () => {
          aiMsg.loading = true;
        },
        onThinkDelta: (t) => {
          if (!currentThink || currentThink.closed) {
            currentThink = { type: 'think', content: '', closed: false };
            aiMsg.blocks.push(currentThink);
          }
          currentThink.content += t;
        },
        onThinkEnd: () => {
          if (currentThink) currentThink.closed = true;
          currentThink = null;
        },
        onContentDelta: (t) => {
          if (!currentText) {
            currentText = { type: 'text', content: '' };
            aiMsg.blocks.push(currentText);
          }
          currentText.content += t;
        },
        onToolCall: (data) => {
          aiMsg.blocks.push({ type: 'tool', id: data.id, name: data.name, args: data.arguments, result: null });
          currentText = null; // break text stream — tool shows between text chunks
        },
        onToolResult: (data) => {
          const t = [...aiMsg.blocks].reverse().find(b => b.type === 'tool' && b.id === data.id);
          if (t) t.result = data.result;
        },
        onImage: (data) => {
          aiMsg.blocks.push({ type: 'image', url: data.url, alt: data.alt, caption: data.caption });
          currentText = null;
        },
        onReference: (data) => {
          const ref = getOrCreateBlock('reference');
          ref.items = [...(ref.items || []), ...(data.items || [])];
        },
        onFallback: () => {
          aiMsg.blocks.push({ type: 'error', level: 'info', message: '未连接后端，已切换到本地 Demo 模式。' });
        },
        onError: (data) => {
          aiMsg.blocks.push({ type: 'error', level: 'error', message: data?.message || '发生错误' });
        },
        onDone: (data) => {
          aiMsg.usage = data?.usage;
          aiMsg.finishReason = data?.finish_reason;
        },
        onFinish: () => {
          aiMsg.loading = false;
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
      if (last?.loading) {
        last.loading = false;
        last.blocks.push({ type: 'error', level: 'info', message: '用户已中止生成。' });
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
