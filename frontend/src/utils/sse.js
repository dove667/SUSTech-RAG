/**
 * Minimal, dependency-free Server-Sent-Events parser operating on a
 * `ReadableStream<Uint8Array>` returned from `fetch`.
 *
 * Yields `{ event, data }` objects.  `data` is always a string — callers
 * decide whether to JSON.parse it.
 */
export async function* parseSSE(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

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
        if (evt.data !== '' || evt.event !== 'message') yield evt;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
