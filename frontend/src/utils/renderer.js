import { marked } from 'marked';
import katex from 'katex';
import hljs from 'highlight.js/lib/common';
import DOMPurify from 'dompurify';

/**
 * Rich-text renderer: Markdown + multi-delimiter LaTeX + code highlighting.
 *
 * LaTeX delimiters recognised (both inline and display):
 *   $$ ... $$       (display)
 *   $ ... $         (inline)
 *   \[ ... \]       (display)
 *   \( ... \)       (inline)
 *   \begin{env} ... \end{env}   (display, supports equation/align/gather/cases/aligned/bmatrix/etc.)
 *
 * We replace math nodes with HTML placeholders *before* handing the text to
 * marked so that `$` or `_` inside formulas cannot be misinterpreted as
 * Markdown syntax.  After marked renders, we substitute the placeholders
 * with the KaTeX-rendered HTML and sanitise the whole thing via DOMPurify.
 */

marked.setOptions({
  gfm: true,
  breaks: true,
});

const PLACEHOLDER = (i) => `\u0000MATH${i}\u0000`;
const PLACEHOLDER_RE = /\u0000MATH(\d+)\u0000/g;

/** All math patterns, ordered so that display forms are matched before inline. */
const MATH_PATTERNS = [
  // $$...$$
  { re: /\$\$([\s\S]+?)\$\$/g, display: true },
  // \[...\]
  { re: /\\\[([\s\S]+?)\\\]/g, display: true },
  // \begin{env}...\end{env}
  { re: /\\begin\{([a-zA-Z*]+)\}([\s\S]+?)\\end\{\1\}/g, display: true, isEnv: true },
  // \(...\)
  { re: /\\\(([\s\S]+?)\\\)/g, display: false },
  // $...$  (avoid currency: preceding char must not be a digit/word; and content must not start/end with whitespace; and must not contain unescaped $)
  { re: /(^|[^\\$])\$([^\n$]+?)\$(?!\d)/g, display: false, hasPrefix: true },
];

function renderKatex(tex, display) {
  try {
    return katex.renderToString(tex, {
      displayMode: display,
      throwOnError: false,
      strict: 'ignore',
      output: 'html',
      trust: false,
    });
  } catch (e) {
    const escaped = tex
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return `<code class="katex-error" title="${String(e)}">${escaped}</code>`;
  }
}

function extractMath(source) {
  const parts = [];
  let text = source;

  for (const pat of MATH_PATTERNS) {
    text = text.replace(pat.re, (match, ...groups) => {
      let body, prefix = '';
      if (pat.isEnv) {
        // groups: [env, body]
        const env = groups[0];
        body = `\\begin{${env}}${groups[1]}\\end{${env}}`;
      } else if (pat.hasPrefix) {
        prefix = groups[0] ?? '';
        body = groups[1];
      } else {
        body = groups[0];
      }
      // Tighten edges for inline: whitespace immediately inside $...$ is usually not math.
      if (!pat.display && pat.hasPrefix) {
        if (/^\s|\s$/.test(body)) return match; // leave untouched
      }
      const idx = parts.length;
      parts.push({ tex: body, display: pat.display });
      return `${prefix}${PLACEHOLDER(idx)}`;
    });
  }

  return { text, parts };
}

function highlightCode(html) {
  return html.replace(
    /<pre><code(?: class="language-([^"]+)")?>([\s\S]*?)<\/code><\/pre>/g,
    (_, lang, code) => {
      const decoded = code
        .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"').replace(/&#39;/g, "'");
      let out;
      if (lang && hljs.getLanguage(lang)) {
        try { out = hljs.highlight(decoded, { language: lang, ignoreIllegals: true }).value; }
        catch { out = escapeHtml(decoded); }
      } else {
        try { out = hljs.highlightAuto(decoded).value; }
        catch { out = escapeHtml(decoded); }
      }
      const langLabel = lang || 'text';
      return `<div class="code-block"><div class="code-head"><span class="lang">${escapeHtml(langLabel)}</span><button class="copy-btn" data-copy>复制</button></div><pre><code class="hljs language-${escapeHtml(langLabel)}">${out}</code></pre></div>`;
    },
  );
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/** Render markdown (+latex + highlighting) to sanitised HTML string. */
export function renderMarkdown(source, { renderLatex = true } = {}) {
  if (!source) return '';
  let text = source;
  let parts = [];
  if (renderLatex) {
    const extracted = extractMath(source);
    text = extracted.text;
    parts = extracted.parts;
  }

  let html = marked.parse(text);
  html = highlightCode(html);

  if (renderLatex) {
    html = html.replace(PLACEHOLDER_RE, (_, i) => {
      const part = parts[Number(i)];
      if (!part) return '';
      return renderKatex(part.tex, part.display);
    });
  }

  return DOMPurify.sanitize(html, {
    ADD_ATTR: ['target', 'data-copy'],
    ADD_TAGS: ['math', 'semantics', 'mrow', 'mi', 'mn', 'mo', 'ms', 'mtext', 'annotation'],
  });
}
