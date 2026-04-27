/**
 * Theme system.
 *
 * Every visual variable is defined here and applied via CSS custom properties
 * on <html>. Settings page lets the user freely override any of them.
 */

export const THEME_VARS = [
  // ——— surfaces ———
  'bg',            // app background
  'bg-elevated',   // cards, sidebar
  'bg-subtle',     // input fields, hovered rows
  'bg-bubble-user',
  'bg-bubble-ai',
  'bg-code',
  'bg-think',
  'bg-tool',

  // ——— text ———
  'text',
  'text-muted',
  'text-faint',
  'text-on-primary',
  'text-code',

  // ——— accent ———
  'primary',
  'primary-hover',
  'primary-soft',
  'danger',
  'success',
  'warning',

  // ——— borders ———
  'border',
  'border-strong',

  // ——— layout ———
  'radius',
  'radius-sm',
  'radius-lg',
  'shadow',
  'shadow-lg',

  // ——— typography ———
  'font',
  'font-mono',
  'font-size',
  'line-height',
];

const base = {
  'radius':     '12px',
  'radius-sm':  '8px',
  'radius-lg':  '20px',
  'shadow':     '0 2px 8px rgba(0,0,0,0.06)',
  'shadow-lg':  '0 12px 32px rgba(0,0,0,0.14)',
  'font':       "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
  'font-mono':  "'JetBrains Mono', 'Fira Code', 'SFMono-Regular', Consolas, monospace",
  'font-size':  '15px',
  'line-height':'1.65',
};

export const PRESETS = {
  light: {
    name: '浅色',
    vars: {
      ...base,
      'bg':            '#ffffff',
      'bg-elevated':   '#f7f8fa',
      'bg-subtle':     '#f1f3f5',
      'bg-bubble-user':'#e8f1ff',
      'bg-bubble-ai':  '#f7f8fa',
      'bg-code':       '#0f172a',
      'bg-think':      '#fff8e1',
      'bg-tool':       '#ecfeff',

      'text':          '#1f2328',
      'text-muted':    '#59636e',
      'text-faint':    '#8c959f',
      'text-on-primary':'#ffffff',
      'text-code':     '#e2e8f0',

      'primary':       '#2563eb',
      'primary-hover': '#1d4ed8',
      'primary-soft':  '#dbeafe',
      'danger':        '#dc2626',
      'success':       '#16a34a',
      'warning':       '#d97706',

      'border':        '#e5e7eb',
      'border-strong': '#cbd5e1',
    },
  },

  dark: {
    name: '深色',
    vars: {
      ...base,
      'bg':            '#0d1117',
      'bg-elevated':   '#161b22',
      'bg-subtle':     '#1f252d',
      'bg-bubble-user':'#1e3a8a',
      'bg-bubble-ai':  '#161b22',
      'bg-code':       '#010409',
      'bg-think':      '#2a2416',
      'bg-tool':       '#082f3a',

      'text':          '#e6edf3',
      'text-muted':    '#9198a1',
      'text-faint':    '#656d76',
      'text-on-primary':'#ffffff',
      'text-code':     '#e6edf3',

      'primary':       '#3b82f6',
      'primary-hover': '#60a5fa',
      'primary-soft':  '#1e3a8a',
      'danger':        '#f87171',
      'success':       '#4ade80',
      'warning':       '#fbbf24',

      'border':        '#30363d',
      'border-strong': '#484f58',

      'shadow':        '0 2px 8px rgba(0,0,0,0.4)',
      'shadow-lg':     '0 12px 32px rgba(0,0,0,0.6)',
    },
  },

  blue: {
    name: '海蓝',
    vars: {
      ...base,
      'bg':            '#f0f6ff',
      'bg-elevated':   '#ffffff',
      'bg-subtle':     '#e0edff',
      'bg-bubble-user':'#bfdbfe',
      'bg-bubble-ai':  '#ffffff',
      'bg-code':       '#0c2748',
      'bg-think':      '#e0f2fe',
      'bg-tool':       '#cffafe',

      'text':          '#0f2c5b',
      'text-muted':    '#475a7d',
      'text-faint':    '#7b8cac',
      'text-on-primary':'#ffffff',
      'text-code':     '#e2e8f0',

      'primary':       '#0ea5e9',
      'primary-hover': '#0284c7',
      'primary-soft':  '#bae6fd',
      'danger':        '#e11d48',
      'success':       '#059669',
      'warning':       '#d97706',

      'border':        '#c7dcff',
      'border-strong': '#94b8ed',
    },
  },

  pink: {
    name: '樱花粉',
    vars: {
      ...base,
      'bg':            '#fff5f9',
      'bg-elevated':   '#ffffff',
      'bg-subtle':     '#ffe4ee',
      'bg-bubble-user':'#fbcfe8',
      'bg-bubble-ai':  '#ffffff',
      'bg-code':       '#3b0a24',
      'bg-think':      '#fef3c7',
      'bg-tool':       '#fae8ff',

      'text':          '#4a0f2f',
      'text-muted':    '#7a4a62',
      'text-faint':    '#a07b8c',
      'text-on-primary':'#ffffff',
      'text-code':     '#fce7f3',

      'primary':       '#ec4899',
      'primary-hover': '#db2777',
      'primary-soft':  '#fce7f3',
      'danger':        '#e11d48',
      'success':       '#10b981',
      'warning':       '#f59e0b',

      'border':        '#fbcfe8',
      'border-strong': '#f9a8d4',
    },
  },

  green: {
    name: '森林绿',
    vars: {
      ...base,
      'bg':            '#f2f8f3',
      'bg-elevated':   '#ffffff',
      'bg-subtle':     '#e2efe4',
      'bg-bubble-user':'#bbf7d0',
      'bg-bubble-ai':  '#ffffff',
      'bg-code':       '#0a2818',
      'bg-think':      '#fef3c7',
      'bg-tool':       '#ccfbf1',

      'text':          '#14321f',
      'text-muted':    '#3e6651',
      'text-faint':    '#7a9687',
      'text-on-primary':'#ffffff',
      'text-code':     '#d1fae5',

      'primary':       '#16a34a',
      'primary-hover': '#15803d',
      'primary-soft':  '#bbf7d0',
      'danger':        '#dc2626',
      'success':       '#059669',
      'warning':       '#d97706',

      'border':        '#cce7d4',
      'border-strong': '#9ec9ab',
    },
  },
};

/** Apply a theme object's vars to the <html> element. */
export function applyTheme(vars) {
  const root = document.documentElement;
  Object.entries(vars).forEach(([k, v]) => {
    root.style.setProperty(`--${k}`, v);
  });
}

/** Get the effective preset id, resolving 'system'. */
export function resolvePresetId(id) {
  if (id !== 'system') return id;
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  return prefersDark ? 'dark' : 'light';
}

export function getPresetVars(id) {
  const real = resolvePresetId(id);
  return PRESETS[real]?.vars ?? PRESETS.light.vars;
}
