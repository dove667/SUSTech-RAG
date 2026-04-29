<script setup>
import { onMounted, onUnmounted, watch } from 'vue';
import { RouterView, useRoute, useRouter } from 'vue-router';
import { useSettings, bindSystemThemeWatcher } from '@/stores/settings.js';
import ConfirmModal from '@/components/ConfirmModal.vue';

const settings = useSettings();
const route = useRoute();
const router = useRouter();

// 仅在「正常应用页面」（电脑版 / 手机版）之间根据窗口大小自动切换。
// 嵌入版、精灵球、设置页不参与自动切换。
const AUTO_SWITCH_ROUTES = new Set(['/', '/mobile']);
const BREAKPOINT = 768;
const mq = window.matchMedia(`(max-width: ${BREAKPOINT}px)`);

function maybeSwitch() {
  if (!AUTO_SWITCH_ROUTES.has(route.path)) return;
  if (mq.matches && route.path === '/') {
    router.replace('/mobile');
  } else if (!mq.matches && route.path === '/mobile') {
    router.replace('/');
  }
}

onMounted(async () => {
  settings.apply();
  bindSystemThemeWatcher(settings);

  // 初始化身份 ID：没有或为空则向后端申请
  if (!settings.identityId) {
    try {
      const res = await fetch(`${settings.apiBaseUrl.replace(/\/$/, '')}/identity`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        settings.identityId = data.identity_id;
      }
    } catch {
      // 降级：本地生成 fallback ID
    }
    if (!settings.identityId) {
      settings.identityId = `fallback_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    }
    settings.persist();
  }

  // 首次加载即检查窗口大小
  maybeSwitch();

  mq.addEventListener('change', maybeSwitch);
});

onUnmounted(() => {
  mq.removeEventListener('change', maybeSwitch);
});

// 用户手动导航到 / 或 /mobile 时也检查一次（例如从设置页返回）
watch(() => route.path, () => maybeSwitch());
</script>

<template>
  <RouterView />
  <ConfirmModal />
</template>
