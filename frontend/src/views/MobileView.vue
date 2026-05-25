<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useChat } from '@/stores/chat.js';
import { showConfirm } from '@/utils/confirm.js';
import ChatWindow from '@/components/ChatWindow.vue';
import ChatInput from '@/components/ChatInput.vue';

const chat = useChat();
onMounted(() => chat.ensureActive());

const active = computed(() => chat.active);
const drawer = ref(false);

function pick(t) { chat.send(t); drawer.value = false; }
function newChat() { chat.newConversation(); drawer.value = false; }
function select(id) { chat.selectConversation(id); drawer.value = false; }
async function del(id) {
  const { confirmed } = await showConfirm({
    title: '删除会话',
    message: '确定要删除这个会话吗？',
    confirmText: '删除',
    danger: true,
    storageKey: 'skip_delete_conversation',
  });
  if (confirmed) chat.deleteConversation(id);
}
</script>

<template>
  <div class="mobile">
    <header class="topbar">
      <button class="icon-btn" @click="drawer = true" aria-label="菜单">☰</button>
      <div class="title">{{ active?.title || '南科问答' }}</div>
      <RouterLink class="icon-btn" to="/settings" aria-label="设置">⚙</RouterLink>
    </header>

    <ChatWindow
      :messages="active?.messages ?? []"
      empty-title="南科问答"
      empty-hint="向知识库提问，我会结合检索结果回答。"
      @pick-suggestion="pick"
    />

    <div class="composer">
      <ChatInput
        :streaming="chat.streaming"
        compact
        @send="(t) => chat.send(t)"
        @cancel="chat.cancel"
      />
    </div>

    <!-- Drawer -->
    <div v-if="drawer" class="drawer-mask" @click.self="drawer = false">
      <aside class="drawer">
        <div class="head">
          <span>会话列表</span>
          <button class="icon-btn" @click="drawer = false">✕</button>
        </div>
        <button class="btn primary new" @click="newChat">+ 新会话</button>
        <nav class="list">
          <div
            v-for="c in chat.conversations"
            :key="c.id"
            class="row"
            :class="{ active: c.id === active?.id }"
            @click="select(c.id)"
          >
            <span class="t">{{ c.title || '新会话' }}</span>
            <button class="del" @click.stop="del(c.id)">✕</button>
          </div>
          <div v-if="!chat.conversations.length" class="hint">还没有会话</div>
        </nav>
        <div class="links">
          <RouterLink to="/">电脑版</RouterLink>
          <RouterLink to="/ball">精灵球</RouterLink>
          <RouterLink to="/embed">嵌入版</RouterLink>
          <RouterLink to="/settings">设置</RouterLink>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.mobile {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 100%;
  background: var(--bg);
}
.topbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  padding-top: calc(8px + env(safe-area-inset-top));
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
  position: sticky; top: 0; z-index: 10;
}
.title {
  flex: 1;
  font-weight: 600;
  font-size: 15px;
  text-align: center;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.composer {
  padding: 8px 10px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
  background: var(--bg-elevated);
  border-top: 1px solid var(--border);
}

.drawer-mask {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 1000;
  display: flex;
  animation: fade 150ms ease;
}
@keyframes fade { from { opacity: 0 } to { opacity: 1 } }

.drawer {
  width: min(86vw, 320px);
  height: 100%;
  background: var(--bg);
  border-right: 1px solid var(--border);
  padding: 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  animation: slide 200ms ease;
}
@keyframes slide { from { transform: translateX(-100%) } to { transform: translateX(0) } }

.head {
  display: flex; align-items: center; justify-content: space-between;
  font-weight: 700;
}
.list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.row {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  font-size: 14px; color: var(--text-muted);
  cursor: pointer;
}
.row.active { background: var(--primary-soft); color: var(--primary); font-weight: 600; }
.row .t { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row .del { color: var(--text-faint); background: none; border: none; padding: 4px; cursor: pointer; }
.hint { text-align: center; color: var(--text-faint); padding: 20px; font-size: 13px; }

.links {
  display: flex; gap: 12px; flex-wrap: wrap;
  padding-top: 10px; border-top: 1px solid var(--border);
  font-size: 13px;
}
.links a { color: var(--text-muted); }
</style>
