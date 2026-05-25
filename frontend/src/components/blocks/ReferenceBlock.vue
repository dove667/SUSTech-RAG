<script setup>
import { ref, reactive } from 'vue';

defineProps({
  items: { type: Array, default: () => [] },
});

const expanded = ref(true);
const snippetExpanded = reactive({});

const SOURCE_LABEL = {
  dense: '向量检索',
  sparse: 'BM25',
  hybrid: '混合检索',
};

function toggleSnippet(idx) {
  snippetExpanded[idx] = !snippetExpanded[idx];
}
</script>

<template>
  <div class="ref-block">
    <button class="head" @click="expanded = !expanded" type="button">
      <span>引用 {{ items.length }} 条</span>
      <span class="chev">{{ expanded ? '▾' : '▸' }}</span>
    </button>
    <ol v-if="expanded" class="list">
      <li v-for="(it, i) in items" :key="i">
        <div class="ref-header">
          <a v-if="it.url" :href="it.url" target="_blank" rel="noopener noreferrer">
            {{ it.title || it.url }}
          </a>
          <span v-else>{{ it.title }}</span>
          <span v-if="it.source" class="source-tag" :class="it.source">
            {{ SOURCE_LABEL[it.source] || it.source }}
          </span>
        </div>
        <div v-if="it.snippet" class="snippet-area">
          <div
            class="snippet"
            :class="{ open: snippetExpanded[i] }"
          >
            {{ it.snippet }}
          </div>
          <div
            v-if="!snippetExpanded[i]"
            class="snippet-mask"
            @click="toggleSnippet(i)"
          >
            <span class="expand-icon">▾</span>
          </div>
          <button
            v-if="snippetExpanded[i]"
            class="collapse-btn"
            type="button"
            @click="toggleSnippet(i)"
          >
            ▴ 收起
          </button>
        </div>
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
  border: none;
  padding: 4px 0;
  cursor: pointer;
}
.chev {
  font-size: 11px;
}
.list {
  margin: 4px 0 6px;
  padding-left: 22px;
}
.list li {
  margin: 6px 0;
}

/* --- headline row --- */
.ref-header {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}

/* --- source tag --- */
.source-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;
  line-height: 18px;
}
.source-tag.dense {
  background: #fce8e6;
  color: #c5221f;
}
.source-tag.sparse {
  background: #fef7e0;
  color: #b06000;
}
.source-tag.hybrid {
  background: #e6f4ea;
  color: #137333;
}

/* --- snippet area --- */
.snippet-area {
  position: relative;
  margin-top: 4px;
}
.snippet {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.6;
  background: var(--bg);
  padding: 6px 10px;
  border-radius: 4px;
  border: 1px solid var(--border);
  white-space: pre-wrap;
  word-break: break-word;
}
/* 默认截断 1 行 */
.snippet:not(.open) {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  /* 为底部的蒙版和图标留空间 */
  padding-bottom: 24px;
}

/* 渐变半透明蒙版 */
.snippet-mask {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 35px;
  background: linear-gradient(to top, var(--bg) 0%, transparent 100%);
  border-radius: 0 0 4px 4px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  cursor: pointer;
}
.expand-icon {
  font-size: 14px;
  color: var(--text-muted);
  background: linear-gradient(to top, var(--bg-subtle) 30%, transparent 100%);
  border: 1px solid var(--border);
  border-top: none;
  padding: 0px 13px 1px;
  line-height: 14px;
  transition: color 0.15s;
}
.snippet-mask:hover .expand-icon {
  color: var(--text);
}

/* 收起按钮 */
.collapse-btn {
  display: block;
  margin: 2px auto 0;
  font-size: 11px;
  color: var(--text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 2px 0;
}
.collapse-btn:hover {
  color: var(--text);
}
</style>
