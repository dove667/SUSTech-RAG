<script setup>
import { onMounted } from 'vue';
import { RouterView, useRoute } from 'vue-router';
import { useSettings, bindSystemThemeWatcher } from '@/stores/settings.js';

const settings = useSettings();
const route = useRoute();

onMounted(() => {
  settings.apply();
  bindSystemThemeWatcher(settings);

  // Auto-redirect small screens to the mobile view, unless we're already on
  // a non-desktop route (ball / embed / settings / mobile).
  const isMobile = window.matchMedia('(max-width: 768px)').matches;
  if (isMobile && route.path === '/') {
    const r = (window.location.hash || '').replace(/^#/, '');
    if (r === '' || r === '/') window.location.hash = '/mobile';
  }
});
</script>

<template>
  <RouterView />
</template>
