/**
 * Minimal, dependency-free Server-Sent-Events parser operating on a
 * `ReadableStream<Uint8Array>` returned from `fetch`.
 *
 * Yields `{ event, data }` objects.  `data` is always a string — callers
 * decide whether to JSON.parse it.
 *
 * When multiple SSE frames arrive in a single TCP chunk (common when a
 * proxy or a fast model emits tokens faster than the network flushes),
 * we yield one event and then await a micro-task tick so Vue has a
 * chance to re-render before the next event.  This prevents the UI from
 * "jumping" from empty to full text without any intermediate frames.
 */
export async function* parseSSE(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  // Yield to the microtask queue so Vue has a chance to re-render before
  // the next SSE frame is processed.  queueMicrotask is ordered correctly
  // relative to Vue's nextTick (which also uses Promise.resolve /
  // queueMicrotask), and it fires much earlier than setTimeout(0) — the
  // macrotask delay was adding ~4 ms per token, killing streaming feel.
  function schedule() {
    return new Promise((resolve) => queueMicrotask(resolve));
  }

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buffer.search(/\r?\n\r?\n/)) !== -1) {
        const chunk = buffer.slice(0, idx);
        buffer = buffer.slice(idx).replace(/^\r?\n\r?\n/, '');

        const evt = { event: 'message', data: '' };
        for (const rawLine of chunk.split(/\r?\n/)) {
          if (!rawLine || rawLine.startsWith(':')) continue;
          const colon = rawLine.indexOf(':');
          const field = colon === -1 ? rawLine : rawLine.slice(0, colon);
          const val = colon === -1 ? '' : rawLine.slice(colon + 1).replace(/^ /, '');
          if (field === 'event') evt.event = val;
          else if (field === 'data') evt.data += (evt.data ? '\n' : '') + val;
        }
        if (evt.data !== '' || evt.event !== 'message') {
          yield evt;
          // If more complete frames are already buffered, give Vue a
          // scheduling slot before yielding the next one.
          if (buffer.search(/\r?\n\r?\n/) !== -1) {
            await schedule();
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
