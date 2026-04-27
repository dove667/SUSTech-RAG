import { parseSSE } from './sse.js';
import { runDemoStream } from './demoStream.js';

/**
 * Streaming chat client.  Consumers call `chat({...}, handlers)` where
 * `handlers` receives granular callbacks for every SSE event documented
 * in docs/API.md.
 *
 * Returns a `cancel()` function.
 */
export function chat({ settings, messages, conversationId, signal }, handlers) {
  const ctrl = new AbortController();
  const innerSignal = ctrl.signal;
  if (signal) signal.addEventListener('abort', () => ctrl.abort());

  const run = async () => {
    if (settings.demoMode) {
      await runDemoStream(messages, handlers, innerSignal);
      return;
    }

    const url = joinUrl(settings.apiBaseUrl, '/chat/completions');
    const body = {
      conversation_id: conversationId,
      messages,
      model: settings.model || undefined,
      knowledge_base_ids: settings.knowledgeBaseIds?.length ? settings.knowledgeBaseIds : undefined,
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
      res = await fetch(url, {
        method: 'POST',
        signal: innerSignal,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(settings.apiKey ? { 'Authorization': `Bearer ${settings.apiKey}` } : {}),
        },
        body: JSON.stringify(body),
      });
    } catch (err) {
      // Network error → fall back to demo.
      handlers.onFallback?.(err);
      await runDemoStream(messages, handlers, innerSignal);
      return;
    }

    const contentType = res.headers.get('content-type') || '';
    if (!res.ok || !res.body || !contentType.includes('event-stream')) {
      let errPayload = { code: `http_${res.status}`, message: res.statusText || 'backend did not return event-stream' };
      try { errPayload = await res.clone().json(); } catch { /* ignore */ }
      handlers.onFallback?.(errPayload);
      await runDemoStream(messages, handlers, innerSignal);
      return;
    }

    try {
      for await (const evt of parseSSE(res.body)) {
        let payload = {};
        try { payload = evt.data ? JSON.parse(evt.data) : {}; } catch { /* leave empty */ }
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

function joinUrl(base, path) {
  if (!base) return path;
  return `${base.replace(/\/$/, '')}${path.startsWith('/') ? path : `/${path}`}`;
}
