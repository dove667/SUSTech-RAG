import { defineStore } from 'pinia';
import { applyTheme, getPresetVars, PRESETS, THEME_VARS } from '@/styles/themes.js';
import { normalizeApiBaseUrl } from '@/utils/api.js';

const STORAGE_KEY = 'ragwebui:settings:v1';

/** Defaults live here so "reset" works. */
const DEFAULTS = () => ({
  preset: 'system',                // light | dark | system | blue | pink | green | custom
  overrides: {},                   // partial override of CSS vars — wins over preset

  apiBaseUrl: '/api',
  identityId: '',

  // UI prefs
  sendWithEnter: true,
  showReferences: true,
  autoCollapseThink: true,
  renderLatex: true,
});

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

export const useSettings = defineStore('settings', {
  state: () => {
    const state = { ...DEFAULTS(), ...loadFromStorage() };
    state.apiBaseUrl = normalizeApiBaseUrl(state.apiBaseUrl);
    return state;
  },

  getters: {
    /** The computed set of CSS variables after applying preset + overrides. */
    themeVars(state) {
      const base = state.preset === 'custom'
        ? getPresetVars('light')
        : getPresetVars(state.preset);
      return { ...base, ...state.overrides };
    },
    presetList() {
      return Object.entries(PRESETS).map(([id, p]) => ({ id, name: p.name }));
    },
    allThemeKeys() {
      return THEME_VARS;
    },
  },

  actions: {
    apply() {
      applyTheme(this.themeVars);
    },
    persist() {
      this.apiBaseUrl = normalizeApiBaseUrl(this.apiBaseUrl);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.$state));
    },
    setPreset(id) {
      this.preset = id;
      if (id !== 'custom') this.overrides = {};
      this.apply();
      this.persist();
    },
    setOverride(key, value) {
      this.overrides = { ...this.overrides, [key]: value };
      if (this.preset !== 'custom') this.preset = 'custom';
      this.apply();
      this.persist();
    },
    clearOverride(key) {
      const next = { ...this.overrides };
      delete next[key];
      this.overrides = next;
      this.apply();
      this.persist();
    },
    reset() {
      Object.assign(this, DEFAULTS());
      this.apply();
      this.persist();
    },
    update(patch) {
      if (Object.prototype.hasOwnProperty.call(patch, 'apiBaseUrl')) {
        patch = { ...patch, apiBaseUrl: normalizeApiBaseUrl(patch.apiBaseUrl) };
      }
      Object.assign(this, patch);
      this.persist();
    },
  },
});

/** Watch system theme changes so `preset: 'system'` updates live. */
export function bindSystemThemeWatcher(store) {
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  const handler = () => { if (store.preset === 'system') store.apply(); };
  mq.addEventListener?.('change', handler);
}
