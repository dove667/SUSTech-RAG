<script setup>
import { computed, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useSettings } from '@/stores/settings.js';
import { PRESETS, getPresetVars } from '@/styles/themes.js';
import { showConfirm } from '@/utils/confirm.js';
import LogoIcon from '@/components/LogoIcon.vue';

const s = useSettings();

const presetGroups = [
  { id: 'system', name: '跟随系统' },
  { id: 'light',  name: PRESETS.light.name },
  { id: 'dark',   name: PRESETS.dark.name },
  { id: 'blue',   name: PRESETS.blue.name },
  { id: 'pink',   name: PRESETS.pink.name },
  { id: 'green',  name: PRESETS.green.name },
  { id: 'custom', name: '自定义' },
];

const activeTab = ref('general');

const embedOrigin = typeof window !== 'undefined' ? window.location.origin : '';
const embedSnippet = `<!-- 1) 整页嵌入 -->
<iframe
  src="${embedOrigin}/embed"
  style="width:100%;height:600px;border:0">
</iframe>

<!-- 2) 精灵球（悬浮） -->
<iframe
  src="${embedOrigin}/ball"
  style="position:fixed;inset:0;border:0;pointer-events:none;z-index:99999;background:transparent"
  allowtransparency="true">
</iframe>

// 父页面通过 postMessage 控制：
parent.postMessage({ type: 'ragwebui:send', text: '你好' }, '*');
parent.postMessage({ type: 'ragwebui:set-theme', preset: 'dark' }, '*');
parent.postMessage({ type: 'ragwebui:reset' }, '*');`;

function update(patch) { s.update(patch); }

function onPreset(id) { s.setPreset(id); }

async function resetAll() {
  const { confirmed } = await showConfirm({
    title: '恢复默认设置',
    message: '恢复全部默认设置？此操作不会清空会话。',
    confirmText: '恢复',
    danger: true,
    storageKey: 'skip_reset_settings',
  });
  if (confirmed) s.reset();
}

async function clearChats() {
  const { confirmed } = await showConfirm({
    title: '清空所有会话',
    message: '确定要清空所有会话吗？此操作不可恢复。',
    confirmText: '清空',
    danger: true,
    storageKey: 'skip_clear_chats',
  });
  if (confirmed) {
    const { useChat } = await import('@/stores/chat.js');
    useChat().clearAll();
  }
}

// Colour picker: KaTeX vars are colours, others are text
function isColorVar(k) {
  return !['radius','radius-sm','radius-lg','shadow','shadow-lg','font','font-mono','font-size','line-height'].includes(k);
}

// Split vars into groups for nicer UI
const varGroups = [
  { title: '背景', keys: ['bg','bg-elevated','bg-subtle','bg-bubble-user','bg-bubble-ai','bg-code','bg-think','bg-tool'] },
  { title: '文本', keys: ['text','text-muted','text-faint','text-on-primary','text-code'] },
  { title: '强调色', keys: ['primary','primary-hover','primary-soft','danger','success','warning'] },
  { title: '边框', keys: ['border','border-strong'] },
  { title: '圆角/阴影/字体', keys: ['radius','radius-sm','radius-lg','shadow','shadow-lg','font','font-mono','font-size','line-height'] },
];

const effectiveVars = computed(() => s.themeVars);

function valueOf(k) {
  return s.overrides[k] ?? effectiveVars.value[k] ?? '';
}
function hasOverride(k) { return Object.prototype.hasOwnProperty.call(s.overrides, k); }

function onVarInput(k, v) { s.setOverride(k, v); }
function onVarColor(k, v) { s.setOverride(k, v); }
function clearOverride(k) { s.clearOverride(k); }

function exportConfig() {
  const payload = JSON.stringify(s.$state, null, 2);
  const blob = new Blob([payload], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'ragwebui-settings.json';
  a.click();
  URL.revokeObjectURL(url);
}

async function importConfig(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  try {
    const text = await file.text();
    const obj = JSON.parse(text);
    s.$patch(obj);
    s.apply();
    s.persist();
    alert('已导入设置');
  } catch (err) {
    alert('导入失败：' + err);
  }
  e.target.value = '';
}
</script>

<template>
  <div class="settings">
    <aside class="side">
      <div class="brand">
        <RouterLink to="/" class="logo-link">
          <LogoIcon :size="34" />
          <span class="name">南科知识问答</span>
        </RouterLink>
      </div>
      <nav class="tabs">
        <button :class="{ on: activeTab === 'general' }" @click="activeTab = 'general'">基本</button>
        <button :class="{ on: activeTab === 'theme'   }" @click="activeTab = 'theme'">配色</button>
        <button :class="{ on: activeTab === 'api'     }" @click="activeTab = 'api'">接口</button>
        <button :class="{ on: activeTab === 'chat'    }" @click="activeTab = 'chat'">对话行为</button>
        <button :class="{ on: activeTab === 'data'    }" @click="activeTab = 'data'">数据</button>
        <button :class="{ on: activeTab === 'about'   }" @click="activeTab = 'about'">关于</button>
      </nav>
      <div class="nav-links">
        <RouterLink to="/">电脑版</RouterLink>
        <RouterLink to="/mobile">手机版</RouterLink>
        <RouterLink to="/ball">精灵球</RouterLink>
        <RouterLink to="/embed">嵌入版</RouterLink>
      </div>
    </aside>

    <main class="main">
      <!-- GENERAL -->
      <section v-if="activeTab === 'general'" class="panel">
        <h2>基本设置</h2>
        <div class="row">
          <label>Enter 直接发送（关闭则 Ctrl+Enter 发送）</label>
          <input type="checkbox" :checked="s.sendWithEnter" @change="e => update({ sendWithEnter: e.target.checked })" />
        </div>
        <div class="row">
          <label>显示引用来源</label>
          <input type="checkbox" :checked="s.showReferences" @change="e => update({ showReferences: e.target.checked })" />
        </div>
        <div class="row">
          <label>思考结束后自动折叠 think 块</label>
          <input type="checkbox" :checked="s.autoCollapseThink" @change="e => update({ autoCollapseThink: e.target.checked })" />
        </div>
        <div class="row">
          <label>渲染 LaTeX 公式</label>
          <input type="checkbox" :checked="s.renderLatex" @change="e => update({ renderLatex: e.target.checked })" />
        </div>
      </section>

      <!-- THEME -->
      <section v-else-if="activeTab === 'theme'" class="panel">
        <h2>配色与主题</h2>
        <p class="muted">选择预设，或把任意变量改成你喜欢的值。所有色值以 CSS 变量形式应用，即时生效。</p>

        <div class="presets">
          <button
            v-for="p in presetGroups"
            :key="p.id"
            class="preset"
            :class="{ on: s.preset === p.id }"
            @click="onPreset(p.id)"
            type="button"
          >
            <span class="swatches" v-if="p.id !== 'custom' && p.id !== 'system'">
              <span :style="{ background: getPresetVars(p.id)['bg'] }" />
              <span :style="{ background: getPresetVars(p.id)['primary'] }" />
              <span :style="{ background: getPresetVars(p.id)['bg-bubble-ai'] }" />
              <span :style="{ background: getPresetVars(p.id)['text'] }" />
            </span>
            <span v-else-if="p.id === 'system'" class="swatches sys">
              <span style="background: #fff" /><span style="background: #111" />
            </span>
            <span v-else class="swatches custom">
              <span style="background: conic-gradient(from 0deg,#f87171,#fbbf24,#34d399,#60a5fa,#a78bfa,#f472b6,#f87171)" />
            </span>
            <span class="label">{{ p.name }}</span>
          </button>
        </div>

        <div v-for="g in varGroups" :key="g.title" class="var-group">
          <h3>{{ g.title }}</h3>
          <div class="vars">
            <div v-for="k in g.keys" :key="k" class="var-row">
              <code class="key">--{{ k }}</code>
              <template v-if="isColorVar(k)">
                <input
                  class="color"
                  type="color"
                  :value="/^#[0-9a-fA-F]{6}$/.test(valueOf(k)) ? valueOf(k) : '#000000'"
                  @input="e => onVarColor(k, e.target.value)"
                  :title="valueOf(k)"
                />
              </template>
              <input
                class="val"
                type="text"
                :value="valueOf(k)"
                @change="e => onVarInput(k, e.target.value)"
              />
              <button class="icon-btn tiny" v-if="hasOverride(k)" @click="clearOverride(k)" title="恢复">↺</button>
            </div>
          </div>
        </div>
      </section>

      <!-- API -->
      <section v-else-if="activeTab === 'api'" class="panel">
        <h2>接口设置</h2>
        <p class="muted">
          详见
          <a href="/API.md" target="_blank">/API.md</a>
          接口规范。
        </p>
        <div class="row">
          <label>API Base URL</label>
          <input type="text" :value="s.apiBaseUrl" @change="e => update({ apiBaseUrl: e.target.value })" placeholder="/api" />
        </div>
        <p class="hint" style="margin-top:8px;line-height:1.6;">
          💡 <strong>中继模式</strong>：将 API Base URL 设为中继服务地址（如 <code>http://127.0.0.1:8080</code>）
          即可通过中继连接到远程 Worker。开发时也可通过环境变量启动：
          <br /><code>VITE_RELAY_URL=http://127.0.0.1:8080 npm run dev</code>
        </p>

      </section>

      <!-- CHAT BEHAVIOUR -->
      <section v-else-if="activeTab === 'chat'" class="panel">
        <h2>对话行为</h2>

      </section>

      <!-- DATA -->
      <section v-else-if="activeTab === 'data'" class="panel">
        <h2>数据</h2>
        <div class="row">
          <button class="btn" @click="exportConfig">导出设置</button>
          <label class="btn" style="cursor:pointer">
            导入设置
            <input type="file" accept="application/json" @change="importConfig" style="display:none" />
          </label>
        </div>
        <div class="row">
          <button class="btn danger" @click="clearChats">清空所有会话</button>
          <button class="btn" @click="resetAll">恢复默认设置</button>
        </div>
      </section>

      <!-- ABOUT -->
      <section v-else class="panel">
        <h2>关于</h2>
        <p>这是一个基于 Vue 3 + Vite 的 RAG 知识问答系统前端，支持：</p>
        <ul>
          <li>电脑版、手机版、精灵球、嵌入版四种形态</li>
          <li>完整的配色变量系统，所有颜色可调</li>
          <li>SSE 流式传输，支持 think / 内容 / 图片 / 代码 / 工具 等多种块</li>
          <li>自动识别多种 LaTeX 定界符 (<code>$...$</code>, <code>$$...$$</code>, <code>\(...\)</code>, <code>\[...\]</code>, <code>\begin...\end</code>)</li>
        </ul>
        <p class="muted">接口规范：<a href="/API.md" target="_blank">/API.md</a></p>
        <h3 style="margin-top: 20px;">嵌入示例</h3>
        <pre class="snippet">{{ embedSnippet }}</pre>
      </section>
    </main>
  </div>
</template>

<style scoped>
.settings {
  display: grid;
  grid-template-columns: 220px 1fr;
  height: 100vh;
  background: var(--bg);
}
@media (max-width: 720px) {
  .settings { grid-template-columns: 1fr; }
  .side { position: static !important; width: auto !important; height: auto !important; border-right: none !important; border-bottom: 1px solid var(--border); }
  .side .tabs { flex-direction: row !important; overflow-x: auto; }
}

.side {
  background: var(--bg-elevated);
  border-right: 1px solid var(--border);
  padding: 16px 12px;
  display: flex; flex-direction: column; gap: 10px;
}
.brand .logo-link {
  display: flex; align-items: center; gap: 10px;
  font-weight: 700; color: var(--text); text-decoration: none;
  padding: 4px 6px 8px;
}

.tabs { display: flex; flex-direction: column; gap: 2px; }
.tabs button {
  text-align: left; padding: 8px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 14px;
  white-space: nowrap;
}
.tabs button:hover { background: var(--bg-subtle); color: var(--text); }
.tabs button.on { background: var(--primary-soft); color: var(--primary); font-weight: 600; }

.nav-links {
  margin-top: auto;
  display: flex; flex-direction: column; gap: 4px;
  padding-top: 10px; border-top: 1px solid var(--border);
  font-size: 13px;
}
.nav-links a { color: var(--text-muted); padding: 4px 6px; border-radius: 4px; }
.nav-links a:hover { background: var(--bg-subtle); color: var(--text); text-decoration: none; }

.main { overflow-y: auto; padding: 24px 28px 80px; }
.panel { max-width: 720px; margin: 0 auto; }
.panel h2 { margin: 0 0 4px; font-size: 22px; }
.panel h3 { font-size: 14px; color: var(--text-muted); margin: 18px 0 8px; font-weight: 600; }
.muted { color: var(--text-muted); font-size: 13px; margin: 4px 0 16px; }

.row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--border);
}
.row label { flex: 1; font-size: 14px; }
.row input[type=text], .row input[type=password] {
  flex: 1; max-width: 320px;
  padding: 6px 10px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-family: var(--font-mono);
}
.row input[type=range] { flex: 1; max-width: 260px; accent-color: var(--primary); }

/* Presets */
.presets {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  margin: 10px 0 18px;
}
.preset {
  display: flex; flex-direction: column; align-items: center;
  padding: 10px; gap: 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 2px solid var(--border);
  cursor: pointer;
  font-size: 13px;
  transition: all 120ms ease;
}
.preset:hover { border-color: var(--primary); }
.preset.on { border-color: var(--primary); background: var(--primary-soft); }
.swatches {
  display: grid;
  grid-template-columns: 1fr 1fr;
  width: 64px; height: 40px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.swatches span { display: block; }
.swatches.sys { grid-template-columns: 1fr 1fr; }
.swatches.custom { grid-template-columns: 1fr; }

.var-group { margin-top: 16px; }
.vars { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; }
@media (max-width: 640px) { .vars { grid-template-columns: 1fr; } }
.var-row {
  display: grid;
  grid-template-columns: minmax(0, 160px) auto 1fr auto;
  gap: 6px;
  align-items: center;
}
.var-row .key {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-subtle);
  padding: 2px 6px; border-radius: 4px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.var-row .color {
  width: 28px; height: 24px; padding: 0; border: 1px solid var(--border);
  border-radius: 4px; background: none; cursor: pointer;
}
.var-row .val {
  min-width: 0;
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  background: var(--bg);
  color: var(--text);
}
.var-row .tiny { width: 24px; height: 24px; font-size: 12px; }

.snippet {
  background: var(--bg-code);
  color: var(--text-code);
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 12px;
  overflow-x: auto;
  white-space: pre;
}
</style>
