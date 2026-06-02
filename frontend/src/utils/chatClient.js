import { parseSSE } from './sse.js';
import { buildApiUrl, fetchWithTimeout } from './api.js';

/**
 * Streaming chat client.  Consumers call `chat({...}, handlers)` where
 * `handlers` receives granular callbacks for every SSE event documented
 * in /API.md and the repo-root docs/API.md.
 *
 * Returns a `cancel()` function.
 */
export function chat({ settings, messages, conversationId, signal }, handlers) {
  const ctrl = new AbortController();
  const innerSignal = ctrl.signal;
  if (signal) signal.addEventListener('abort', () => ctrl.abort());

  const run = async () => {
    const url = buildApiUrl(settings.apiBaseUrl, '/chat/completions');
    const body = {
      conversation_id: conversationId,
      messages,
      model: settings.model || undefined,
      stream: true,
      options: {
        temperature: settings.temperature,
        top_k: settings.topK,
        enable_think: settings.enableThink,
        enable_tools: settings.enableTools,
      },
    };

    let res;
    try {
      res = await fetchWithTimeout(url, {
        method: 'POST',
        signal: innerSignal,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(settings.identityId ? { 'X-Identity-ID': settings.identityId } : {}),
        },
        body: JSON.stringify(body),
      }, 15000);
    } catch (err) {
      if (innerSignal.aborted) return;
      handlers.onError?.({
        code: 'network_error',
        message: err instanceof DOMException && err.name === 'AbortError'
          ? '连接后端超时，请确认后端已经完成启动'
          : err instanceof Error ? err.message : String(err),
      });
      return;
    }

    const contentType = res.headers.get('content-type') || '';
    if (!res.ok || !res.body || !contentType.includes('event-stream')) {
      // 尝试从响应体中提取有用信息
      let errPayload = {
        code: `http_${res.status}`,
        message: res.statusText || 'backend did not return event-stream',
        detail: `content-type: ${contentType || 'none'}`,
      };
      try {
        const clone = res.clone();
        const text = await clone.text();
        try {
          const json = JSON.parse(text);
          errPayload = { ...errPayload, ...json };
        } catch {
          errPayload.detail += ` | body: ${text.slice(0, 300)}`;
        }
      } catch {
        /* body not readable */
      }
      handlers.onError?.(errPayload);
      return;
    }

    try {
      for await (const evt of parseSSE(res.body)) {
        let payload = {};
        try { payload = evt.data ? JSON.parse(evt.data) : {}; } catch { console.warn('[ragwebui] malformed SSE data:', evt.data?.slice(0, 120)); }
        dispatch(evt.event, payload, handlers);
        if (evt.event === 'done' || evt.event === 'error') break;
      }
    } catch (err) {
      if (innerSignal.aborted) return;
      handlers.onError?.({ code: 'stream_error', message: String(err) });
    }
  };

  run().finally(() => handlers.onFinish?.());

  return () => ctrl.abort();
}

function dispatch(event, data, h) {
  switch (event) {
    case 'start':         return h.onStart?.(data);
    case 'retrieval.decision':
      return h.onRetrievalDecision?.(data);
    case 'retrieval.assessment':
      return h.onRetrievalAssessment?.(data);
    case 'support.decision':
      return h.onSupportDecision?.(data);
    case 'think.delta':   return h.onThinkDelta?.(data.text ?? '');
    case 'think.end':     return h.onThinkEnd?.();
    case 'content.delta': return h.onContentDelta?.(data.text ?? '');
    case 'tool.call':     return h.onToolCall?.(data);
    case 'tool.result':   return h.onToolResult?.(data);
    case 'image':         return h.onImage?.(data);
    case 'reference':     return h.onReference?.(data);
    case 'done':          return h.onDone?.(data);
    case 'error':         return h.onError?.(data);
  }
}
