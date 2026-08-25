import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { useConversationMessages } from "@/hooks/use-conversations.ts";
import { streamChat, streamRunEvents, type StreamRunEvent } from "@/lib/stream.ts";
import { queryKeys } from "@/lib/query-keys";

export interface UseSecurityChatParams {
  conversationId: string | null;
  spaceId: string | null;
  /** 新建会话后回调（容器负责把新会话 ID 写回 URL）。 */
  onConversationCreated(conversationId: string): void;
}

/** 把 run 模式 SSE 事件格式化为展示文本。 */
function formatRunEvent(event: StreamRunEvent): string {
  switch (event.type) {
    case "start":
      return "▶ 开始执行测试流程\n";
    case "node":
      return `▸ 节点 ${event.node ?? "?"} 完成\n`;
    case "final": {
      const state = event.state ?? {};
      if (state.user_intent === "ask" && state.answer_content) {
        return `${state.answer_content}\n`;
      }
      const s = (state.test_results_summary ?? {}) as Record<string, number>;
      const passRate = ((s.pass_rate ?? 0) * 100).toFixed(1);
      const lines = [
        `\n📊 测试完成：共 ${s.total ?? 0} 条，通过 ${s.passed ?? 0}，失败 ${s.failed ?? 0}，通过率 ${passRate}%`,
      ];
      if (state.report_path) lines.push(`📄 报告：${state.report_path}`);
      return lines.join("\n") + "\n";
    }
    case "error":
      return `✖ 执行失败：${event.message ?? "未知错误"}\n`;
    default:
      return "";
  }
}

export function useSecurityChat({ conversationId, spaceId, onConversationCreated }: UseSecurityChatParams) {
  const queryClient = useQueryClient();

  const [instruction, setInstruction] = useState("");
  const [mode, setMode] = useState("Run");

  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const { data: messagesData, isLoading: messagesLoading } =
    useConversationMessages(conversationId);
  const serverMessages = messagesData?.items ?? [];

  // 切换会话时清空进行中的本地 overlay。
  // 采用 React 官方支持的 render 期 setState（derive state from props）模式，
  // 避免在 effect 中 setState 导致旧会话 overlay 闪一帧。
  const [trackedConversationId, setTrackedConversationId] = useState(conversationId);
  if (conversationId !== trackedConversationId) {
    setTrackedConversationId(conversationId);
    setPendingUser(null);
    setAnswer("");
  }

  const handleSubmit = async () => {
    if (!instruction.trim() || isStreaming) return;

    const prompt = instruction.trim();
    setInstruction("");
    setPendingUser(prompt);
    setAnswer("");
    setIsStreaming(true);

    let newConversationId: string | null = null;

    try {
      const payload = {
        instruction: prompt,
        conversation_id: conversationId ?? undefined,
        mode,
        space_id: spaceId ?? undefined,
      };
      const streamOptions = {
        onConversationId: (id: string) => {
          newConversationId = id;
        },
      };

      if (mode === "Run") {
        // run 模式：SSE 事件流（节点进度 + 测试结果）
        await streamRunEvents(payload, (event) => {
          const text = formatRunEvent(event);
          if (text) setAnswer((prev) => prev + text);
        }, streamOptions);
      } else {
        // ask / plan：text/plain 文本流
        await streamChat(payload, (chunk) => setAnswer((prev) => prev + chunk), streamOptions);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "请求失败";
      toast.error(message);
      setAnswer((prev) => prev || `请求失败：${message}`);
    } finally {
      setIsStreaming(false);

      if (!conversationId && newConversationId) {
        // 新建会话：刷新会话列表并把新会话 ID 写回 URL
        await queryClient.invalidateQueries({ queryKey: queryKeys.conversations.all });
        onConversationCreated(newConversationId);
      } else if (conversationId) {
        // 存量会话：刷新消息与会话列表后清空 overlay
        await queryClient.invalidateQueries({
          queryKey: queryKeys.conversations.messages(conversationId),
        });
        queryClient.invalidateQueries({ queryKey: queryKeys.conversations.all });
        setPendingUser(null);
        setAnswer("");
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInstructionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInstruction(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const hasMessages = serverMessages.length > 0 || pendingUser !== null || isStreaming;
  const showWelcome = !hasMessages && !messagesLoading;

  return {
    instruction,
    setInstruction,
    mode,
    setMode,
    pendingUser,
    answer,
    isStreaming,
    serverMessages,
    messagesLoading,
    handleSubmit,
    handleKeyDown,
    handleInstructionChange,
    hasMessages,
    showWelcome,
  };
}
