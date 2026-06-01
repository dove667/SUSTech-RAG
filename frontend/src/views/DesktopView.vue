<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useChat } from '@/stores/chat.js';
import { useSettings } from '@/stores/settings.js';
import { showConfirm } from '@/utils/confirm.js';
import { buildApiUrl, fetchWithTimeout } from '@/utils/api.js';
import ChatWindow from '@/components/ChatWindow.vue';
import ChatInput from '@/components/ChatInput.vue';
import LogoIcon from '@/components/LogoIcon.vue';

const chat = useChat();
const settings = useSettings();

const backendStatus = ref('checking'); // 'checking' | 'ready' | 'error'
const backendMessage = ref('');

async function checkHealth() {
  backendStatus.value = 'checking';
  try {
    const res = await fetchWithTimeout(
      buildApiUrl(settings.apiBaseUrl, '/health'),
      {},
      5000,
    );
    if (res.ok) {
      backendStatus.value = 'ready';
      backendMessage.value = '';
    } else {
      backendStatus.value = 'error';
      try {
        const data = await res.json();
        backendMessage.value = data.message || res.statusText;
      } catch {
        backendMessage.value = res.statusText;
      }
    }
  } catch (err) {
    backendStatus.value = 'error';
    backendMessage.value = err instanceof DOMException && err.name === 'AbortError'
      ? '后端启动中或接口无响应'
      : '无法连接到后端服务';
  }
}

onMounted(() => {
  chat.ensureActive();
  checkHealth();
});

const list = computed(() => chat.conversations);
const active = computed(() => chat.active);

function pick(text) { chat.send(text); }
function send(text) { chat.send(text); }
function stop() { chat.cancel(); }
function newChat() { chat.newConversation(); }
function select(id) { chat.selectConversation(id); }
async function del(id) {
  const { confirmed } = await showConfirm({
    title: '删除会话',
    message: '确定要删除这个会话吗？此操作不可恢复。',
    confirmText: '删除',
    danger: true,
    storageKey: 'skip_delete_conversation',
  });
  if (confirmed) chat.deleteConversation(id);
}
function titleOf(c) {
  return c.title || '新会话';
}
function timeOf(c) {
  return new Date(c.updatedAt).toLocaleDateString();
}
</script>

<template>
  <div class="desktop">
    <aside class="sidebar">
      <div class="brand">
        <LogoIcon :size="45" />
        <span class="name">南科知识问答</span>
      </div>

      <button class="btn primary new" @click="newChat">
        + 新会话
      </button>

      <nav class="convs">
        <button
          v-for="c in list"
          :key="c.id"
          class="conv"
          :class="{ active: c.id === active?.id }"
          @click="select(c.id)"
          type="button"
        >
          <span class="title" :title="titleOf(c)">{{ titleOf(c) }}</span>
          <span class="time">{{ timeOf(c) }}</span>
          <span class="del" @click.stop="del(c.id)" title="删除">✕</span>
        </button>
        <div v-if="!list.length" class="hint">还没有会话</div>
      </nav>

      <div class="foot">
        <RouterLink to="/settings" class="btn ghost full">⚙ 设置</RouterLink>
        <div class="links">
          <RouterLink to="/mobile">手机版</RouterLink>
          <RouterLink to="/ball">精灵球</RouterLink>
          <RouterLink to="/embed">嵌入版</RouterLink>
        </div>
        <div class="status" :class="backendStatus" :title="backendMessage">
          <span class="dot" />
          <span class="label">{{ backendStatus === 'ready' ? '后端已连接' : backendStatus === 'error' ? '后端异常' : '检测中...' }}</span>
        </div>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div class="title">{{ active?.title || '南科知识问答' }}</div>
        <div class="spacer" />
        <button class="icon-btn" @click="chat.regenerate" title="重新生成" :disabled="chat.streaming">↻</button>
      </header>

      <ChatWindow
        :messages="active?.messages ?? []"
        @pick-suggestion="pick"
      />

      <div class="composer">
        <ChatInput
          :streaming="chat.streaming"
          @send="send"
          @cancel="stop"
        />
        <div class="foot-hint">
          回答由 AI 生成，请谨慎核对事实。 · <RouterLink to="/settings">调整配色与接口</RouterLink>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.desktop {
  display: grid;
  grid-template-columns: 280px 1fr;
  height: 100vh;
  background: var(--bg);
}

.sidebar {
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  gap: 12px;
  background: var(--bg-elevated);
  border-right: 1px solid var(--border);
  min-width: 0;
}
.brand {
  display: flex; align-items: center; gap: 10px;
  padding: 4px 6px 10px;
  font-weight: 700;
  font-size: 16px;
}
.new { justify-content: flex-start; font-weight: 600; }

.convs {
  flex: 1;
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 2px;
  padding: 4px 0;
}
.conv {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  text-align: left;
  font-size: 13px;
  cursor: pointer;
  transition: background 120ms ease;
}
.conv:hover { background: var(--bg-subtle); color: var(--text); }
.conv.active { background: var(--primary-soft); color: var(--primary); font-weight: 600; }
.conv .title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conv .time { color: var(--text-faint); font-size: 11px; }
.conv .del {
  width: 20px; height: 20px;
  display: inline-grid; place-items: center;
  border-radius: 4px;
  opacity: 0;
  transition: opacity 120ms ease;
  color: var(--text-muted);
}
.conv:hover .del { opacity: 1; }
.conv .del:hover { background: color-mix(in srgb, var(--danger) 18%, transparent); color: var(--danger); }

.hint {
  color: var(--text-faint); font-size: 12px; text-align: center; padding: 20px 0;
}

.foot { display: flex; flex-direction: column; gap: 8px; padding-top: 8px; border-top: 1px solid var(--border); }
.btn.full { justify-content: flex-start; }
.links {
  display: flex; gap: 10px; justify-content: center;
  font-size: 12px;
}
.links a { color: var(--text-muted); }

.status {
  display: flex; align-items: center; gap: 6px;
  justify-content: center; padding-top: 4px;
  font-size: 11px;
}
.status .dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status.checking .dot { background: var(--text-muted); }
.status.ready .dot { background: #22c55e; }
.status.error .dot { background: var(--danger); color: var(--danger); }
.status .label { color: var(--text-muted); }
.status.error .label { color: var(--danger); }

.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
}
.topbar .title {
  font-weight: 600;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.spacer { flex: 1; }

.composer {
  padding: 12px 20px 16px;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
}
.foot-hint {
  text-align: center; color: var(--text-faint); font-size: 11px; margin-top: 8px;
}
</style>
