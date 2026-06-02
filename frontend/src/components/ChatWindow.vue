<script setup>
import { nextTick, ref, watch } from 'vue';
import MessageBubble from './MessageBubble.vue';
import LogoIcon from '@/components/LogoIcon.vue';

const props = defineProps({
  messages: { type: Array, default: () => [] },
  emptyTitle: { type: String, default: '南科知识问答' },
  emptyHint:  { type: String, default: '你可以用自然语言提问，我会结合知识库回答。' },
  suggestions: {
    type: Array,
    default: () => [
      '什么是 RAG？它的核心思想是什么？',
      '给我一段 Python 写的向量检索示例',
      '解释公式 $P(y|x) = \\sum_z P(y|x,z) P(z|x)$',
      '如何降低大模型的幻觉？',
    ],
  },
});
const emit = defineEmits(['pick-suggestion']);

const scroller = ref(null);
let pinned = true;

function isAtBottom() {
  if (!scroller.value) return true;
  const el = scroller.value;
  return el.scrollHeight - el.scrollTop - el.clientHeight < 60;
}

function onScroll() {
  pinned = isAtBottom();
}

async function scrollToBottom(force = false) {
  await nextTick();
  if (!scroller.value) return;
  if (force || pinned) {
    scroller.value.scrollTop = scroller.value.scrollHeight;
  }
}

watch(
  () => props.messages.map((m) => m.blocks.reduce(
    (n, b) => n
      + (b.content?.length || 0)
      + (b.items?.length || 0)
      + (b.events?.length || 0)
      + (b.url ? 1 : 0),
    0,
  ) + (m.loading ? 1 : 0)),
  () => scrollToBottom(),
  { deep: true },
);

watch(() => props.messages.length, () => scrollToBottom(true));
</script>

<template>
  <div ref="scroller" class="chat-window" @scroll="onScroll">
    <div class="inner">
      <template v-if="messages.length === 0">
        <div class="empty">
          <div class="hero">
            <div class="logo">
              <LogoIcon :size="96" />
            </div>
            <h1>{{ emptyTitle }}</h1>
            <p>{{ emptyHint }}</p>
          </div>
          <div class="suggestions">
            <button
              v-for="(s, i) in suggestions"
              :key="i"
              class="suggestion"
              type="button"
              @click="$emit('pick-suggestion', s)"
            >
              {{ s }}
            </button>
          </div>
        </div>
      </template>
      <template v-else>
        <MessageBubble v-for="m in messages" :key="m.id" :message="m" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.chat-window {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px 20px;
  scroll-behavior: smooth;
}
.inner {
  max-width: 960px;
  margin: 0 auto;
  padding-bottom: 20px;
}

.empty {
  padding: 40px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 28px;
}
.hero { text-align: center; color: var(--text-muted); }
.hero .logo {
  width: 120px; height: 120px;
  margin: 0 auto 12px;
  display: flex; align-items: center; justify-content: center;
}
.hero h1 { margin: 0 0 6px; color: var(--text); font-size: 24px; font-weight: 700; }
.hero p { margin: 0; font-size: 14px; }

.suggestions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
  width: 100%;
  max-width: 640px;
}
.suggestion {
  padding: 12px 14px;
  border-radius: var(--radius);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text);
  text-align: left;
  cursor: pointer;
  font-size: 13px;
  line-height: 1.45;
  transition: all 150ms ease;
}
.suggestion:hover {
  transform: translateY(-1px);
  border-color: var(--primary);
  box-shadow: var(--shadow);
}
</style>
