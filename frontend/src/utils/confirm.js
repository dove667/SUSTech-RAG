/**
 * Custom confirmation dialog — replaces browser ``confirm()`` with a styled
 * modal that supports a "don't ask again" checkbox.
 *
 * Usage::
 *
 *   import { showConfirm } from '@/utils/confirm.js';
 *   const { confirmed, skipNext } = await showConfirm({
 *     title: '删除会话',
 *     message: '确定要删除这个会话吗？',
 *     confirmText: '删除',
 *     danger: true,
 *     storageKey: 'skip_delete_conversation',
 *   });
 *   if (confirmed) { ... }
 *   // if (skipNext) persist "don't ask again" preference
 */

import { ref } from 'vue';

const visible = ref(false);
const opts = ref({});
let _resolve = null;

const SKIP_PREFIX = 'ragwebui:confirm:skip:';

function skipKey(key) {
  return key ? (SKIP_PREFIX + key) : '';
}

/**
 * Show a confirmation dialog.  Returns a promise that resolves when the
 * user clicks confirm or cancel.
 *
 * If ``storageKey`` is set and the user previously checked "不再提醒",
 * the dialog is skipped entirely and ``{ confirmed: true, skipNext: true }``
 * is returned immediately.
 */
export function showConfirm(options) {
  const key = skipKey(options.storageKey);
  if (key && localStorage.getItem(key) === '1') {
    return Promise.resolve({ confirmed: true, skipNext: true });
  }
  return new Promise((resolve) => {
    opts.value = { ...options, skipNext: false };
    visible.value = true;
    _resolve = resolve;
  });
}

export function useConfirm() {
  function confirm() {
    const key = skipKey(opts.value.storageKey);
    if (key && opts.value.skipNext) {
      localStorage.setItem(key, '1');
    }
    _resolve?.({ confirmed: true, skipNext: opts.value.skipNext ?? false });
    visible.value = false;
  }

  function cancel() {
    _resolve?.({ confirmed: false, skipNext: false });
    visible.value = false;
  }

  return { visible, opts, confirm, cancel };
}
