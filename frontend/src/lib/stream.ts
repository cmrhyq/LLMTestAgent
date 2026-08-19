export interface ChatStreamRequest {
  instruction: string;
  api_doc_path?: string | null;
  conversation_id?: string | number | null;
  mode?: string;
  space_id?: string | number | null;
}

export interface StreamChatOptions {
  signal?: AbortSignal;
  /** 首次从响应头 X-Conversation-Id 读取到会话 ID 时触发（用于新建会话回写） */
  onConversationId?: (conversationId: string) => void;
}

/**
 * 以流式方式请求 /api/v1/chat/stream 接口。
 *
 * axios 不适合处理流式响应，因此这里使用原生 fetch + ReadableStream reader，
 * 逐块解码文本并通过 onChunk 回调实时返回给调用方。
 *
 * 后端会通过响应头 X-Conversation-Id 回传会话 ID：
 * - 携带 conversation_id 时复用该会话；
 * - 缺省时后端自动新建会话，并把新会话 ID 通过响应头返回。
 *
 * @param payload 请求体（用户 prompt、模式、可选会话/空间/文档信息）
 * @param onChunk 每接收到一段文本增量时触发
 * @param options 可选项：AbortSignal 与会话 ID 回调
 */
export async function streamChat(
  payload: ChatStreamRequest,
  onChunk: (chunk: string) => void,
  options?: StreamChatOptions
): Promise<void> {
  const response = await fetch("/api/v1/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: options?.signal,
  });

  if (!response.ok || !response.body) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `请求失败（${response.status}）`);
  }

  const conversationId = response.headers.get("X-Conversation-Id");
  if (conversationId && options?.onConversationId) {
    options.onConversationId(conversationId);
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
