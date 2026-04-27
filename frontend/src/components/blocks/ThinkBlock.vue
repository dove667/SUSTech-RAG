<script setup>
import { ref, watch } from 'vue';
import { useSettings } from '@/stores/settings.js';

const props = defineProps({
  content: { type: String, default: '' },
  closed:  { type: Boolean, default: false },
});

const settings = useSettings();
const collapsed = ref(false);

// Auto-collapse on close
watch(() => props.closed, (c) => {
  if (c && settings.autoCollapseThink) collapsed.value = true;
});
</script>

<template>
  <div class="think-block" :class="{ collapsed, live: !closed }">
    <button class="head" @click="collapsed = !collapsed" type="button">
      <span class="dot" />
      <span class="title">{{ closed ? '思考过程' : '思考中…' }}</span>
      <span class="chev">{{ collapsed ? '▸' : '▾' }}</span>
    </button>
    <div v-if="!collapsed" class="body">
      <pre>{{ content }}</pre>
    </div>
  </div>
</template>

<style scoped>
.think-block {
  background: var(--bg-think);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  margin: 8px 0;
  overflow: hidden;
  font-size: 0.92em;
}
.head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  font-size: 13px;
}
.head:hover { background: rgba(0,0,0,0.03); }
.dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--warning);
}
.live .dot { animation: pulse 1s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
.title { flex: 1; text-align: left; }
.chev { font-size: 11px; opacity: 0.6; }
.body pre {
  margin: 0;
  padding: 4px 14px 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: var(--text-muted);
  font-family: var(--font);
  font-size: 0.94em;
  line-height: 1.55;
}
</style>
