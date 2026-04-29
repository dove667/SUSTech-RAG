<script setup>
import { ref, watch } from 'vue';
import { useConfirm } from '@/utils/confirm.js';

const { visible, opts, confirm, cancel } = useConfirm();

const skip = ref(false);

watch(visible, (v) => {
  if (v) skip.value = false;
});

// Sync checkbox state back into shared opts so confirm() can read it.
watch(skip, (v) => {
  opts.value.skipNext = v;
});

function onKeydown(e) {
  if (e.key === 'Escape') cancel();
  if (e.key === 'Enter') confirm();
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="confirm-overlay"
      @click.self="cancel"
      @keydown="onKeydown"
    >
      <div class="confirm-card" role="dialog" aria-modal="true">
        <div class="title">{{ opts.title || '确认' }}</div>
        <div class="message">{{ opts.message || '确定执行此操作吗？' }}</div>

        <label v-if="opts.storageKey" class="skip-row">
          <input v-model="skip" type="checkbox" />
          <span>不再提醒</span>
        </label>

        <div class="actions">
          <button class="btn ghost" @click="cancel" autofocus>
            {{ opts.cancelText || '取消' }}
          </button>
          <button
            class="btn"
            :class="opts.danger ? 'danger' : 'primary'"
            @click="confirm"
          >
            {{ opts.confirmText || '确定' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  animation: fadeIn 150ms ease;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

.confirm-card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  padding: 24px;
  min-width: 320px;
  max-width: 440px;
  width: calc(100vw - 40px);
  animation: scaleIn 180ms ease;
}
@keyframes scaleIn {
  from { transform: scale(0.92); opacity: 0; }
  to   { transform: scale(1);    opacity: 1; }
}

.title {
  font-weight: 700;
  font-size: 17px;
  margin-bottom: 8px;
}

.message {
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.55;
  margin-bottom: 16px;
}

.skip-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 16px;
  cursor: pointer;
  user-select: none;
}
.skip-row input[type="checkbox"] {
  accent-color: var(--primary);
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
