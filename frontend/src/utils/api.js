const DEFAULT_API_BASE_URL = '/api';

export function normalizeApiBaseUrl(rawValue) {
  const value = typeof rawValue === 'string' ? rawValue.trim() : '';
  if (!value || value === '/') return DEFAULT_API_BASE_URL;

  const trimmed = value.replace(/\/+$/, '');
  if (trimmed === '') return DEFAULT_API_BASE_URL;

  try {
    if (/^https?:\/\//i.test(trimmed)) {
      const url = new URL(trimmed);
      if (url.pathname === '' || url.pathname === '/') {
        url.pathname = DEFAULT_API_BASE_URL;
      }
      return `${url.origin}${url.pathname.replace(/\/+$/, '')}`;
    }
  } catch {
    // Keep the user's input; the request layer will surface a clearer error.
  }

  return trimmed;
}

export function buildApiUrl(baseUrl, path) {
  const base = normalizeApiBaseUrl(baseUrl);
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

export async function fetchWithTimeout(input, init = {}, timeoutMs = 10000) {
  const ctrl = new AbortController();
  const upstreamSignal = init.signal;
  if (upstreamSignal) {
    if (upstreamSignal.aborted) {
      ctrl.abort(upstreamSignal.reason);
    } else {
      upstreamSignal.addEventListener('abort', () => ctrl.abort(upstreamSignal.reason), { once: true });
    }
  }

  const timer = window.setTimeout(() => ctrl.abort(new DOMException('Request timeout', 'AbortError')), timeoutMs);

  try {
    return await fetch(input, {
      ...init,
      signal: ctrl.signal,
    });
  } finally {
    window.clearTimeout(timer);
  }
}
