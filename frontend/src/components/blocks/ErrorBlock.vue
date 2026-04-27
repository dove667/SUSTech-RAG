<script setup>
defineProps({
  level: { type: String, default: 'error' },  // 'error' | 'info' | 'warn'
  message: { type: String, default: '' },
});
</script>

<template>
  <div class="err-block" :class="level">
    <span class="ico">
      <template v-if="level === 'error'">⚠</template>
      <template v-else-if="level === 'warn'">!</template>
      <template v-else>ⓘ</template>
    </span>
    <span>{{ message }}</span>
  </div>
</template>

<style scoped>
.err-block {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  margin: 6px 0;
}
.error {
  background: color-mix(in srgb, var(--danger) 12%, transparent);
  color: var(--danger);
  border: 1px solid color-mix(in srgb, var(--danger) 30%, transparent);
}
.warn {
  background: color-mix(in srgb, var(--warning) 12%, transparent);
  color: var(--warning);
}
.info {
  background: var(--bg-subtle);
  color: var(--text-muted);
  border: 1px solid var(--border);
}
.ico { font-weight: bold; flex-shrink: 0; }
</style>
