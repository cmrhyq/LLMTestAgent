import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { useConversationMessages } from "@/hooks/use-conversations.ts";
import { streamChat } from "@/lib/stream.ts";
import { queryKeys } from "@/lib/query-keys";

export interface UseSecurityChatParams {
  conversationId: string | null;
  spaceId: string | null;
  /** 新建会话后回调（容器负责把新会话 ID 写回 URL）。 */
  onConversationCreated(conversationId: string): void;
}

export function useSecurityChat({ conversationId, spaceId, onConversationCreated }: UseSecurityChatParams) {
  const queryClient = useQueryClient();

  const [instruction, setInstruction] = useState("");
  const [mode, setMode] = useState("Ask");

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
      await streamChat(
        {
          instruction: prompt,
          conversation_id: conversationId ?? undefined,
          mode,
          space_id: spaceId ?? undefined,
        },
        (chunk) => setAnswer((prev) => prev + chunk),
        {
          onConversationId: (id) => {
            newConversationId = id;
          },
        }
      );
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
