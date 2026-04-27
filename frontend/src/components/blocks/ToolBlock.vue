<script setup>
import { ref } from 'vue';

const props = defineProps({
  name:   { type: String, required: true },
  args:   { type: [Object, Array, String, Number], default: null },
  result: { type: [Object, Array, String, Number], default: null },
});

const open = ref(false);

function fmt(v) {
  if (v === null || v === undefined) return '';
  if (typeof v === 'string') return v;
  try { return JSON.stringify(v, null, 2); } catch { return String(v); }
}
</script>

<template>
  <div class="tool-block">
    <button class="head" @click="open = !open" type="button">
      <span class="icon">⚙</span>
      <span class="name">工具：{{ name }}</span>
      <span class="status">
        <template v-if="result === null">调用中…</template>
        <template v-else>已完成</template>
      </span>
      <span class="chev">{{ open ? '▾' : '▸' }}</span>
    </button>
    <div v-if="open" class="body">
      <div class="section">
        <div class="label">参数</div>
        <pre>{{ fmt(args) }}</pre>
      </div>
      <div v-if="result !== null" class="section">
        <div class="label">结果</div>
        <pre>{{ fmt(result) }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tool-block {
  background: var(--bg-tool);
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
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  background: transparent;
}
.head:hover { background: rgba(0,0,0,0.04); }
.icon { color: var(--primary); }
.name { font-weight: 600; flex: 1; text-align: left; }
.status { color: var(--text-muted); font-size: 12px; }
.chev { font-size: 11px; opacity: 0.6; margin-left: 4px; }
.body { padding: 4px 12px 12px; }
.section + .section { margin-top: 8px; }
.label { color: var(--text-muted); font-size: 12px; margin-bottom: 2px; }
pre {
  margin: 0;
  padding: 8px 10px;
  background: rgba(0,0,0,0.04);
  border-radius: 6px;
  font-family: var(--font-mono);
  font-size: 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 240px;
  overflow: auto;
}
</style>
