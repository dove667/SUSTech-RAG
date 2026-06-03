<script setup>
import { computed, reactive, ref } from 'vue';

const props = defineProps({
  mode: { type: String, default: 'self_rag' },
  events: { type: Array, default: () => [] },
});

const expanded = ref(true);
const snippetExpanded = reactive({});

const stageLabel = {
  'retrieval.decision': '是否检索',
  'retrieval.assessment': '文档筛选',
  'support.decision': '证据检查',
};

const stageClass = {
  'retrieval.decision': 'stage-decision',
  'retrieval.assessment': 'stage-assessment',
  'support.decision': 'stage-support',
};

const sourceLabel = {
  dense: '向量',
  sparse: 'BM25',
  hybrid: '混合',
};

const normalizedEvents = computed(() => props.events.map((event, index) => ({
  id: `${event.type || 'event'}_${event.round || 0}_${index}`,
  stageClass: stageClass[event.type] || 'stage-generic',
  ...event,
})));

function assessmentSummary(items = []) {
  const relevantCount = items.filter(item => item.relevant).length;
  if (!items.length) return '本轮没有候选资料。';
  return `保留 ${relevantCount} / ${items.length} 条资料`;
}

function toggleSnippet(id) {
  snippetExpanded[id] = !snippetExpanded[id];
}
</script>

<template>
  <div class="trace-block">
    <button class="head" type="button" @click="expanded = !expanded">
      <div class="head-copy">
        <span class="badge">Self-RAG</span>
        <span class="title">检索思路</span>
        <span class="meta">{{ normalizedEvents.length }} 个阶段</span>
      </div>
      <span class="chev">{{ expanded ? '▾' : '▸' }}</span>
    </button>

    <div v-if="expanded" class="body">
      <div
        v-for="event in normalizedEvents"
        :key="event.id"
        class="event-card"
        :class="event.stageClass"
      >
        <div class="event-head">
          <div class="event-title">
            <span class="stage">{{ stageLabel[event.type] || event.type }}</span>
            <span v-if="event.round" class="round">第 {{ event.round }} 轮</span>
          </div>
          <span
            v-if="event.type === 'retrieval.decision'"
            class="status"
            :class="event.should_retrieve ? 'yes' : 'no'"
          >
            {{ event.should_retrieve ? '需要检索' : '直接回答' }}
          </span>
          <span
            v-else-if="event.type === 'support.decision'"
            class="status"
            :class="event.supported ? 'yes' : 'no'"
          >
            {{ event.supported ? '证据充分' : '继续检索' }}
          </span>
          <span v-else-if="event.type === 'retrieval.assessment'" class="status neutral">
            {{ assessmentSummary(event.items) }}
          </span>
        </div>

        <p v-if="event.thought" class="thought">{{ event.thought }}</p>

        <ul v-if="event.type === 'retrieval.assessment' && event.items?.length" class="items">
          <li
            v-for="item in event.items"
            :key="`${event.id}_${item.candidate_index}`"
            class="item"
            :class="item.relevant ? 'relevant' : 'irrelevant'"
          >
            <div class="item-head">
              <span class="item-index">#{{ item.candidate_index }}</span>
              <a
                v-if="item.url"
                class="item-title link"
                :href="item.url"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ item.title || '未命名资料' }}
              </a>
              <span v-else class="item-title">{{ item.title || '未命名资料' }}</span>
              <span v-if="item.source" class="source">{{ sourceLabel[item.source] || item.source }}</span>
              <span class="item-status">{{ item.relevant ? '保留' : '排除' }}</span>
            </div>
            <p v-if="item.thought" class="item-thought">{{ item.thought }}</p>
            <div v-if="item.full_text" class="snippet-area">
              <button
                class="snippet-toggle"
                type="button"
                @click="toggleSnippet(`${event.id}_${item.candidate_index}`)"
              >
                {{ snippetExpanded[`${event.id}_${item.candidate_index}`] ? '收起检索原文' : '展开检索原文' }}
              </button>
              <div
                v-if="snippetExpanded[`${event.id}_${item.candidate_index}`]"
                class="snippet"
              >
                {{ item.full_text }}
              </div>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trace-block {
  margin: 10px 0;
  border: 1px solid color-mix(in srgb, var(--primary) 24%, var(--border));
  border-radius: var(--radius);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--primary) 7%, var(--bg)) 0%, var(--bg) 100%);
  overflow: hidden;
}

.head {
  width: 100%;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: transparent;
  border: none;
  cursor: pointer;
}

.head-copy {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--primary) 14%, transparent);
  color: var(--primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.title {
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
}

.meta,
.chev {
  color: var(--text-muted);
  font-size: 12px;
}

.body {
  padding: 0 14px 14px;
  display: grid;
  gap: 10px;
}

.event-card {
  border-left: 3px solid var(--border-strong);
  padding: 10px 12px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: color-mix(in srgb, var(--bg-elevated) 72%, transparent);
}

.event-card.stage-decision {
  border-left-color: #3b82f6;
}

.event-card.stage-assessment {
  border-left-color: #c0841a;
}

.event-card.stage-support {
  border-left-color: #059669;
}

.event-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.event-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.stage {
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
}

.round {
  color: var(--text-faint);
  font-size: 11px;
}

.status {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.status.yes {
  background: #e8f7ef;
  color: #0f7a46;
}

.status.no {
  background: #fff1f0;
  color: #c2410c;
}

.status.neutral {
  background: #f7f1e7;
  color: #8a5a12;
}

.thought {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.items {
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.item {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
}

.item.relevant {
  border-color: color-mix(in srgb, #0f7a46 24%, var(--border));
}

.item.irrelevant {
  border-color: color-mix(in srgb, #c2410c 22%, var(--border));
  opacity: 0.82;
}

.item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.item-index,
.source,
.item-status {
  font-size: 11px;
  color: var(--text-faint);
}

.item-title {
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
}

.item-title.link {
  text-decoration: none;
}

.item-title.link:hover {
  text-decoration: underline;
}

.item-status {
  margin-left: auto;
}

.item-thought {
  margin: 6px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.55;
}

.snippet-area {
  margin-top: 8px;
}

.snippet-toggle {
  padding: 0;
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 12px;
  cursor: pointer;
}

.snippet-toggle:hover {
  color: color-mix(in srgb, var(--primary) 82%, black);
}

.snippet {
  margin-top: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--bg-elevated) 84%, transparent);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
