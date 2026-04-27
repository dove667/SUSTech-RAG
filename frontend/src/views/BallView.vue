<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useChat } from '@/stores/chat.js';
import ChatWindow from '@/components/ChatWindow.vue';
import ChatInput from '@/components/ChatInput.vue';

/**
 * Floating spirit ball — can be used as a standalone page *or* dropped into
 * any other site via an <iframe> or by mounting this component inside a
 * container page.  The ball lives in the bottom-right corner, opens a chat
 * panel when clicked, and is fully draggable.
 */

const chat = useChat();
onMounted(() => chat.ensureActive());

const open = ref(false);
const active = computed(() => chat.active);

// ——— Drag ———
const pos = ref(loadPos());
const dragging = ref(false);
let startX = 0, startY = 0, startLeft = 0, startTop = 0, moved = false;

function loadPos() {
  try { return JSON.parse(localStorage.getItem('ragwebui:ball:pos')) ?? null; } catch { return null; }
}
function savePos(p) {
  try { localStorage.setItem('ragwebui:ball:pos', JSON.stringify(p)); } catch { /* ignore */ }
}

function onDown(e) {
  const t = e.touches?.[0] ?? e;
  dragging.value = true;
  moved = false;
  startX = t.clientX; startY = t.clientY;
  const box = e.currentTarget.getBoundingClientRect();
  startLeft = box.left; startTop = box.top;
  window.addEventListener('mousemove', onMove);
  window.addEventListener('touchmove', onMove, { passive: false });
  window.addEventListener('mouseup', onUp);
  window.addEventListener('touchend', onUp);
}
function onMove(e) {
  if (!dragging.value) return;
  e.preventDefault?.();
  const t = e.touches?.[0] ?? e;
  const dx = t.clientX - startX;
  const dy = t.clientY - startY;
  if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
  const left = Math.min(Math.max(0, startLeft + dx), window.innerWidth - 56);
  const top  = Math.min(Math.max(0, startTop  + dy), window.innerHeight - 56);
  pos.value = { left, top };
}
function onUp() {
  dragging.value = false;
  if (pos.value) savePos(pos.value);
  window.removeEventListener('mousemove', onMove);
  window.removeEventListener('touchmove', onMove);
  window.removeEventListener('mouseup', onUp);
  window.removeEventListener('touchend', onUp);
  // If user just tapped (didn't drag), toggle the panel
  if (!moved) open.value = !open.value;
}

onUnmounted(() => {
  window.removeEventListener('mousemove', onMove);
  window.removeEventListener('mouseup', onUp);
});

const ballStyle = computed(() => {
  if (pos.value) return { left: pos.value.left + 'px', top: pos.value.top + 'px', right: 'auto', bottom: 'auto' };
  return { right: '24px', bottom: '24px' };
});

function pick(t) { chat.send(t); }
</script>

<template>
  <div class="ball-stage">
    <div class="stage-bg">
      <div class="info">
        <h1>🧚 悬浮精灵球</h1>
        <p>把鼠标移到右下角 → 点击蓝色小球 → 拖动可换位。</p>
        <p class="muted">
          本视图可直接嵌入到任何页面（通过 <code>&lt;iframe src="/ball"&gt;</code>
          或将组件挂载到你的站点上），始终悬浮在视窗角落。
        </p>
        <div class="links">
          <RouterLink to="/" class="btn">电脑版</RouterLink>
          <RouterLink to="/mobile" class="btn">手机版</RouterLink>
          <RouterLink to="/embed" class="btn">嵌入版</RouterLink>
          <RouterLink to="/settings" class="btn">设置</RouterLink>
        </div>
      </div>
    </div>

    <!-- Ball -->
    <button
      class="ball"
      :class="{ active: open, dragging }"
      :style="ballStyle"
      type="button"
      @mousedown="onDown"
      @touchstart="onDown"
      aria-label="打开 AI 助手"
    >
      <span class="emoji">{{ open ? '✕' : '✨' }}</span>
      <span class="pulse" />
    </button>

    <!-- Panel -->
    <transition name="panel">
      <section v-if="open" class="panel" @mousedown.stop @touchstart.stop>
        <header class="panel-head">
          <strong>AI 助手</strong>
          <div class="spacer" />
          <button class="icon-btn" @click="chat.newConversation" title="新会话">＋</button>
          <RouterLink class="icon-btn" to="/settings" title="设置">⚙</RouterLink>
          <button class="icon-btn" @click="open = false" title="收起">—</button>
        </header>

        <ChatWindow
          class="panel-window"
          :messages="active?.messages ?? []"
          empty-title="你好 ✨"
          empty-hint="我随时在侧边陪你。"
          @pick-suggestion="pick"
        />

        <div class="panel-input">
          <ChatInput
            compact
            :streaming="chat.streaming"
            placeholder="说点什么…"
            @send="(t) => chat.send(t)"
            @cancel="chat.cancel"
          />
        </div>
      </section>
    </transition>
  </div>
</template>

<style scoped>
.ball-stage {
  position: fixed; inset: 0;
  overflow: hidden;
}
.stage-bg {
  position: absolute; inset: 0;
  display: grid; place-items: center;
  background:
    radial-gradient(60% 60% at 20% 10%, var(--primary-soft), transparent 70%),
    radial-gradient(60% 60% at 90% 90%, var(--primary-soft), transparent 70%),
    var(--bg);
  padding: 20px;
}
.info {
  max-width: 520px;
  text-align: center;
  color: var(--text);
}
.info h1 { font-size: 28px; margin: 0 0 8px; }
.info p { color: var(--text-muted); margin: 6px 0; }
.info .muted { color: var(--text-faint); font-size: 13px; }
.info code { background: var(--bg-subtle); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); font-size: 12px; }
.info .links { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-top: 16px; }

.ball {
  position: fixed;
  width: 56px; height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary), var(--primary-hover));
  color: var(--text-on-primary);
  box-shadow: var(--shadow-lg);
  border: none;
  cursor: grab;
  z-index: 9999;
  display: grid; place-items: center;
  touch-action: none;
  transition: transform 150ms ease, box-shadow 150ms ease;
}
.ball:hover { transform: scale(1.05); }
.ball.active { transform: scale(0.95); }
.ball.dragging { cursor: grabbing; transition: none; }
.ball .emoji { font-size: 24px; line-height: 1; }
.ball .pulse {
  position: absolute; inset: 0;
  border-radius: 50%;
  border: 2px solid var(--primary);
  opacity: 0.6;
  animation: ring 2s ease-out infinite;
  pointer-events: none;
}
@keyframes ring {
  0%   { transform: scale(1);    opacity: 0.5; }
  100% { transform: scale(1.8);  opacity: 0;   }
}

.panel {
  position: fixed;
  right: 24px; bottom: 96px;
  width: min(92vw, 400px);
  height: min(72vh, 620px);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 9998;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
@media (max-width: 520px) {
  .panel {
    right: 12px; left: 12px; bottom: 88px;
    width: auto; height: min(70vh, 560px);
  }
}

.panel-head {
  display: flex; align-items: center; gap: 4px;
  padding: 10px 10px 10px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
  font-size: 14px;
}
.spacer { flex: 1; }

.panel-window { flex: 1; }
.panel-input { padding: 8px 10px 10px; border-top: 1px solid var(--border); background: var(--bg-elevated); }

.panel-enter-active, .panel-leave-active { transition: transform 180ms ease, opacity 180ms ease; transform-origin: bottom right; }
.panel-enter-from, .panel-leave-to { transform: scale(0.92) translateY(12px); opacity: 0; }
</style>
