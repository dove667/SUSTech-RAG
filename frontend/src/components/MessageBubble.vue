<script setup>
import MarkdownBlock from './MarkdownBlock.vue';
import ThinkBlock from './blocks/ThinkBlock.vue';
import ToolBlock from './blocks/ToolBlock.vue';
import ImageBlock from './blocks/ImageBlock.vue';
import ReferenceBlock from './blocks/ReferenceBlock.vue';
import ErrorBlock from './blocks/ErrorBlock.vue';
import { useSettings } from '@/stores/settings.js';
import { computed } from 'vue';

const props = defineProps({
  message: { type: Object, required: true },
});

const emit = defineEmits(['copy']);

const settings = useSettings();
const isUser = computed(() => props.message.role === 'user');

function copyAll() {
  const text = props.message.blocks
    .map(b => {
      if (b.type === 'text' || b.type === 'think') return b.content;
      if (b.type === 'image') return b.url;
      return '';
    })
    .filter(Boolean)
    .join('\n\n');
  navigator.clipboard?.writeText(text);
  emit('copy');
}
</script>

<template>
  <div class="bubble-row" :class="{ user: isUser, ai: !isUser }">
    <div class="avatar" :class="{ user: isUser }">
      <span v-if="isUser">你</span>
      <span v-else>AI</span>
    </div>

    <div class="bubble">
      <div v-for="(b, i) in message.blocks" :key="i" class="block">
        <MarkdownBlock v-if="b.type === 'text'" :source="b.content" />

        <ThinkBlock
          v-else-if="b.type === 'think' && settings.enableThink"
          :content="b.content"
          :closed="b.closed"
        />

        <ToolBlock
          v-else-if="b.type === 'tool' && settings.enableTools"
          :name="b.name"
          :args="b.args"
          :result="b.result"
        />

        <ImageBlock
          v-else-if="b.type === 'image'"
          :url="b.url"
          :alt="b.alt"
          :caption="b.caption"
        />

        <ReferenceBlock
          v-else-if="b.type === 'reference' && settings.showReferences"
          :items="b.items"
        />

        <ErrorBlock
          v-else-if="b.type === 'error'"
          :level="b.level"
          :message="b.message"
        />
      </div>

      <div v-if="message.loading" class="typing">
        <span /><span /><span />
      </div>

      <div v-if="!isUser && !message.loading && message.blocks.length" class="actions">
        <button class="btn ghost sm" type="button" @click="copyAll">复制</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bubble-row {
  display: flex;
  gap: 12px;
  margin: 16px 0;
  align-items: flex-start;
}
.bubble-row.user { flex-direction: row-reverse; }

.avatar {
  flex-shrink: 0;
  width: 32px; height: 32px;
  border-radius: 50%;
  background: var(--primary);
  color: var(--text-on-primary);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px;
  font-weight: 600;
}
.avatar.user {
  background: var(--bg-subtle);
  color: var(--text);
  border: 1px solid var(--border);
}

.bubble {
  max-width: min(100%, 760px);
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  background: var(--bg-bubble-ai);
  border: 1px solid var(--border);
  word-break: break-word;
}
.bubble-row.user .bubble {
  background: var(--bg-bubble-user);
  border-color: transparent;
}

.block + .block { margin-top: 4px; }

.typing {
  display: inline-flex; gap: 4px; padding: 6px 2px;
}
.typing span {
  width: 6px; height: 6px; background: var(--text-faint);
  border-radius: 50%;
  animation: bounce 1.2s infinite ease-in-out;
}
.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce { 0%,80%,100%{transform:scale(0.6);opacity:0.4} 40%{transform:scale(1);opacity:1} }

.actions {
  margin-top: 6px;
  display: flex; gap: 6px;
  opacity: 0; transition: opacity 150ms ease;
}
.bubble:hover .actions { opacity: 1; }
.btn.sm { padding: 3px 8px; font-size: 12px; color: var(--text-muted); }
.btn.sm:hover { color: var(--text); }
</style>
