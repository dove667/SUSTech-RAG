<script setup>
import { ref } from 'vue';

defineProps({
  items: { type: Array, default: () => [] },
});

const expanded = ref(true);
</script>

<template>
  <div class="ref-block">
    <button class="head" @click="expanded = !expanded" type="button">
      <span>📎 引用 {{ items.length }} 条</span>
      <span class="chev">{{ expanded ? '▾' : '▸' }}</span>
    </button>
    <ol v-if="expanded" class="list">
      <li v-for="(it, i) in items" :key="i">
        <a v-if="it.url" :href="it.url" target="_blank" rel="noopener noreferrer">{{ it.title || it.url }}</a>
        <span v-else>{{ it.title }}</span>
        <span v-if="typeof it.score === 'number'" class="score">· 匹配度 {{ it.score.toFixed(2) }}</span>
        <div v-if="it.snippet" class="snippet">{{ it.snippet }}</div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.ref-block {
  margin: 10px 0;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  font-size: 13px;
  background: var(--bg-subtle);
}
.head {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-muted);
  background: transparent;
  padding: 4px 0;
  cursor: pointer;
}
.list { margin: 4px 0 6px; padding-left: 22px; }
.list li { margin: 4px 0; }
.score { color: var(--text-faint); font-size: 12px; margin-left: 4px; }
.snippet {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
  line-height: 1.5;
  background: var(--bg);
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid var(--border);
}
</style>
