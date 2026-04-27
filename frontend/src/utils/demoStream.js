/**
 * Rich demo stream — runs when no backend is present.
 * Exercises every block type the renderer supports: think / tool / content
 * (with markdown, code, LaTeX in various delimiters) / image / reference.
 */

function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => { clearTimeout(t); reject(new DOMException('aborted', 'AbortError')); });
  });
}

async function stream(text, emit, signal, perChunk = 3, delay = 14) {
  for (let i = 0; i < text.length; i += perChunk) {
    if (signal.aborted) return;
    emit(text.slice(i, i + perChunk));
    await sleep(delay, signal);
  }
}

export async function runDemoStream(messages, h, signal) {
  const lastUser = [...messages].reverse().find(m => m.role === 'user')?.content ?? '你好';

  try {
    h.onStart?.({ conversation_id: 'demo', message_id: `demo_${Date.now()}` });
    await sleep(120, signal);

    // Think block
    await stream(
      `用户询问："${lastUser}"。\n我需要先检索知识库，然后结合检索结果生成一个结构化、可读的回答……`,
      t => h.onThinkDelta?.(t), signal, 4, 10,
    );
    h.onThinkEnd?.();
    await sleep(200, signal);

    // Tool call + result
    h.onToolCall?.({ id: 't_1', name: 'search_knowledge_base', arguments: { query: lastUser, top_k: 5 } });
    await sleep(400, signal);
    h.onToolResult?.({ id: 't_1', result: { hits: 3, top_score: 0.82 } });

    // Main content
    const md = `## 关于你的问题

**RAG**（Retrieval-Augmented Generation）结合了检索与生成，核心流程可以写成：

$$
P(y\\mid x) = \\sum_{z \\in \\mathcal{Z}} P_\\eta(z\\mid x)\\,P_\\theta(y\\mid x, z)
$$

其中行内公式形式例如 \\(P(z\\mid x)\\)、$E=mc^2$、以及 \\[ a^2 + b^2 = c^2 \\]。

### 伪代码示例

\`\`\`python
def rag_answer(query: str) -> str:
    docs = retriever.search(query, top_k=5)
    context = "\\n".join(d.text for d in docs)
    return llm.generate(prompt=f"{context}\\n\\nQ: {query}\\nA:")
\`\`\`

### 关键优势

1. **知识可更新** —— 更新向量库即可，无需微调。
2. **可溯源** —— 返回的引用清晰可见。
3. **成本低** —— 小模型 + 大知识库同样强大。

| 方法 | 可更新 | 可溯源 |
| :---- | :----: | :----: |
| Fine-tune | ❌ | ❌ |
| RAG | ✅ | ✅ |
`;
    await stream(md, t => h.onContentDelta?.(t), signal, 6, 8);

    // Image
    h.onImage?.({
      url: 'https://dummyimage.com/720x360/2563eb/ffffff&text=RAG+Architecture',
      alt: 'RAG 架构示意图',
      caption: '图 1：RAG 系统架构',
    });

    // References
    h.onReference?.({
      items: [
        { title: 'Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks',
          url: 'https://arxiv.org/abs/2005.11401', score: 0.91, snippet: 'We introduce RAG — models which combine pre-trained parametric and non-parametric memory...' },
        { title: '本地文档 · 《RAG 入门手册》第 3 章',
          url: '#', score: 0.78, snippet: '向量检索的核心是将文档切片并映射到稠密向量空间...' },
      ],
    });

    h.onDone?.({ finish_reason: 'stop', usage: { prompt_tokens: 128, completion_tokens: 456 } });
  } catch (err) {
    if (err?.name === 'AbortError') return;
    h.onError?.({ code: 'demo_error', message: String(err) });
  }
}
