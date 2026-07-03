export interface ChatStreamRequest {
  instruction: string;
  api_doc_path?: string | null;
}

/**
 * 以流式方式请求 /api/v1/chat/stream 接口。
 *
 * axios 不适合处理流式响应，因此这里使用原生 fetch + ReadableStream reader，
 * 逐块解码文本并通过 onChunk 回调实时返回给调用方。
 *
 * @param payload 请求体（用户 prompt 与可选的 OpenAPI 文档路径）
 * @param onChunk 每接收到一段文本增量时触发
 * @param signal 可选的 AbortSignal，用于中断请求
 */
export async function streamChat(
  payload: ChatStreamRequest,
  onChunk: (chunk: string) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch("/api/v1/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok || !response.body) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `请求失败（${response.status}）`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value, { stream: true });
      if (text) onChunk(text);
    }
    const tail = decoder.decode();
    if (tail) onChunk(tail);
  } finally {
    reader.releaseLock();
  }
}
