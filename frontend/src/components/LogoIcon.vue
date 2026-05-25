<script setup>
/**
 * SUSTech logo 图标组件。
 *
 * 用 Canvas 直接渲染带 --primary 颜色的图标：
 * - 暗部（橙色中心）→ 纯 --primary
 * - 亮部（白色边缘）→ 浅色 --primary
 * - 背景透明
 * 输出为 PNG data URL，以 <img> 显示，无需 CSS mask。
 */
import { ref, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  size: { type: Number, default: 28 },
  color: { type: String, default: 'var(--primary)' },
});

const imgSrc = ref('');

function parseHexColor(hex) {
  hex = hex.replace('#', '');
  if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
  return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)];
}

function rgbToHex(r, g, b) {
  return '#' + [r, g, b].map(c => Math.round(c).toString(16).padStart(2, '0')).join('');
}

function smoothCoverage(lum, th, edge) {
  if (edge <= 0) return lum < th ? 1 : 0;
  const t = (th - lum) / edge;
  const x = Math.max(0, Math.min(1, t));
  return x * x * (3 - 2 * x);
}

function getPrimaryRgb() {
  const val = getComputedStyle(document.documentElement).getPropertyValue('--primary').trim();
  if (val.startsWith('#')) return parseHexColor(val);
  if (val.startsWith('rgb')) {
    const m = val.match(/\d+/g);
    if (m) return [parseInt(m[0]), parseInt(m[1]), parseInt(m[2])];
  }
  return [234, 88, 12]; // fallback orange
}

async function renderIcon() {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      try {
        const w = img.naturalWidth || img.width;
        const h = img.naturalHeight || img.height;
        const scale = 4;
        const th = 188;
        const edge = 4;

        // Get primary color
        const [pr, pg, pb] = getPrimaryRgb();

        // Step 1: upscale 4×
        const srcCanvas = document.createElement('canvas');
        srcCanvas.width = w;
        srcCanvas.height = h;
        const srcCtx = srcCanvas.getContext('2d');
        srcCtx.drawImage(img, 0, 0);

        const upCanvas = document.createElement('canvas');
        upCanvas.width = w * scale;
        upCanvas.height = h * scale;
        const upCtx = upCanvas.getContext('2d');
        upCtx.imageSmoothingEnabled = true;
        upCtx.imageSmoothingQuality = 'high';
        upCtx.drawImage(srcCanvas, 0, 0, w, h, 0, 0, w * scale, h * scale);
        const upData = upCtx.getImageData(0, 0, w * scale, h * scale);

        // Step 2: render colored pixels with transparency
        const outData = new ImageData(w * scale, h * scale);
        const d = upData.data;
        const o = outData.data;
        for (let i = 0; i < d.length; i += 4) {
          const a = d[i + 3];
          // Background or light part: fully transparent
          if (a < 128) {
            o[i + 3] = 0;
            continue;
          }
          const lum = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
          const cov = smoothCoverage(lum, th, edge);
          if (cov < 0.01) {
            // Light (white) edge of gradient: transparent
            o[i + 3] = 0;
          } else {
            // Darker part: show --primary with coverage-based opacity
            o[i] = pr;
            o[i + 1] = pg;
            o[i + 2] = pb;
            o[i + 3] = Math.round(cov * 255);
          }
        }
        upCtx.putImageData(outData, 0, 0);

        // Step 3: downscale to original size (anti-aliasing)
        const dstCanvas = document.createElement('canvas');
        dstCanvas.width = w;
        dstCanvas.height = h;
        const dstCtx = dstCanvas.getContext('2d');
        dstCtx.imageSmoothingEnabled = true;
        dstCtx.imageSmoothingQuality = 'high';
        dstCtx.drawImage(upCanvas, 0, 0, w * scale, h * scale, 0, 0, w, h);

        resolve(dstCanvas.toDataURL('image/png'));
      } catch (err) {
        reject(err);
      }
    };
    img.onerror = () => reject(new Error('Failed to load /sustech.png'));
    img.src = '/sustech.png';
  });
}

let observer = null;

onMounted(async () => {
  // Initial render
  try {
    imgSrc.value = await renderIcon();
  } catch (err) {
    console.error('[LogoIcon] render failed:', err);
  }

  // Watch for theme changes (CSS variables on <html>)
  observer = new MutationObserver(async () => {
    try {
      imgSrc.value = await renderIcon();
    } catch (err) {
      console.error('[LogoIcon] re-render failed:', err);
    }
  });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['style'] });
});

onUnmounted(() => {
  if (observer) observer.disconnect();
});
</script>

<template>
  <img
    v-if="imgSrc"
    :src="imgSrc"
    class="logo-icon"
    :style="{ width: size + 'px', height: size + 'px' }"
    alt="SUSTech"
  />
  <span
    v-else
    class="logo-icon"
    :style="{ width: size + 'px', height: size + 'px' }"
  />
</template>

<style scoped>
.logo-icon {
  display: inline-block;
  flex-shrink: 0;
}
</style>
