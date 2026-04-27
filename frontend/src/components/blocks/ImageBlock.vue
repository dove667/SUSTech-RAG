<script setup>
defineProps({
  url: { type: String, required: true },
  alt: { type: String, default: '' },
  caption: { type: String, default: '' },
});
</script>

<template>
  <figure class="image-block">
    <img :src="url" :alt="alt" loading="lazy" />
    <figcaption v-if="caption">{{ caption }}</figcaption>
  </figure>
</template>

<style scoped>
.image-block {
  margin: 10px 0;
  max-width: 100%;
}
.image-block img {
  max-width: 100%;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  display: block;
}
figcaption {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
}
</style>
