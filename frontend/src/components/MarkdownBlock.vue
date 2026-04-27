<script setup>
import { computed, onMounted, onUpdated, ref } from 'vue';
import { renderMarkdown } from '@/utils/renderer.js';
import { useSettings } from '@/stores/settings.js';

const props = defineProps({
  source: { type: String, default: '' },
});

const settings = useSettings();
const rootRef = ref(null);

const html = computed(() =>
  renderMarkdown(props.source || '', { renderLatex: settings.renderLatex }),
);

function bindCopy() {
  if (!rootRef.value) return;
  rootRef.value.querySelectorAll('button[data-copy]').forEach((btn) => {
    if (btn._bound) return;
    btn._bound = true;
    btn.addEventListener('click', () => {
      const pre = btn.closest('.code-block')?.querySelector('pre code');
      if (!pre) return;
      navigator.clipboard?.writeText(pre.textContent ?? '');
      const prev = btn.textContent;
      btn.textContent = '已复制';
      setTimeout(() => { btn.textContent = prev; }, 1200);
    });
  });
}

onMounted(bindCopy);
onUpdated(bindCopy);
</script>

<template>
  <div ref="rootRef" class="md" v-html="html" />
</template>

<style>
/* Code block — global so DOMPurify output is styled. */
.code-block {
  background: var(--bg-code);
  color: var(--text-code);
  border-radius: var(--radius-sm);
  margin: 0.6em 0;
  overflow: hidden;
  font-size: 0.92em;
}
.code-block .code-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 10px 4px 12px;
  background: rgba(255,255,255,0.04);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  font-size: 12px;
  color: #9ca3af;
}
.code-block .lang { text-transform: lowercase; letter-spacing: 0.5px; }
.code-block .copy-btn {
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}
.code-block .copy-btn:hover { background: rgba(255,255,255,0.08); color: #fff; }
.code-block pre { margin: 0; padding: 10px 14px; overflow-x: auto; }
.code-block code { font-family: var(--font-mono); background: none; color: inherit; padding: 0; }

.katex-error {
  color: var(--danger);
  background: rgba(220, 38, 38, 0.08);
  padding: 1px 4px;
  border-radius: 4px;
}
</style>
