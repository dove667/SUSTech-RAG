<script setup>
import { ref, nextTick, watch } from 'vue';
import { useSettings } from '@/stores/settings.js';

const props = defineProps({
  streaming: { type: Boolean, default: false },
  placeholder: { type: String, default: '向 RAG 知识库提问…  (Enter 发送，Shift+Enter 换行)' },
  compact: { type: Boolean, default: false },
});
const emit = defineEmits(['send', 'cancel']);

const settings = useSettings();
const text = ref('');
const ta = ref(null);

async function autosize() {
  await nextTick();
  if (!ta.value) return;
  ta.value.style.height = 'auto';
  const max = props.compact ? 120 : 220;
  ta.value.style.height = `${Math.min(ta.value.scrollHeight, max)}px`;
}
watch(text, autosize);

function submit() {
  const v = text.value.trim();
  if (!v || props.streaming) return;
  emit('send', v);
  text.value = '';
  autosize();
}

function onKey(e) {
  if (e.key === 'Enter') {
    const shouldSend = settings.sendWithEnter ? !e.shiftKey : (e.ctrlKey || e.metaKey);
    if (shouldSend) {
      e.preventDefault();
      submit();
    }
  }
}
</script>

<template>
  <div class="input-wrap" :class="{ compact }">
    <textarea
      ref="ta"
      v-model="text"
      :placeholder="placeholder"
      rows="1"
      @keydown="onKey"
    />
    <div class="actions">
      <slot name="left" />
      <div class="spacer" />
      <button
        v-if="streaming"
        class="btn danger"
        type="button"
        @click="$emit('cancel')"
      >
        <span class="dot live" /> 停止生成
      </button>
      <button
        v-else
        class="btn primary"
        type="button"
        :disabled="!text.trim()"
        @click="submit"
      >
        发送
      </button>
    </div>
  </div>
</template>

<style scoped>
.input-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  transition: border-color 150ms ease;
}
.input-wrap:focus-within {
  border-color: var(--primary);
}

textarea {
  width: 100%;
  min-height: 36px;
  max-height: 220px;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  line-height: 1.5;
  font-size: 15px;
  color: var(--text);
  padding: 4px 2px;
  font-family: inherit;
}
textarea::placeholder { color: var(--text-faint); }

.actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.spacer { flex: 1; }

.dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--danger);
  display: inline-block; margin-right: 4px;
}
.dot.live { animation: blink 1s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

.compact { padding: 8px 10px 6px; }
.compact textarea { font-size: 14px; max-height: 120px; }
</style>
