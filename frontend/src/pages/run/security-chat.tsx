import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";

import { useSecurityChat } from "@/hooks/use-security-chat.ts";
import {
  UserBubble,
  AssistantBubble,
  StreamingAssistantMessage,
} from "@/components/chat/message-bubbles";
import { ChatInput } from "@/components/chat/chat-input";
import { SpaceSelector } from "@/components/space/space-selector";

export default function SecurityChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const conversationId = searchParams.get("conversation_id");
  const spaceId = searchParams.get("space_id");

  const {
    instruction,
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
    showWelcome,
  } = useSecurityChat({
    conversationId,
    spaceId,
    onConversationCreated: (id) => {
      setSearchParams({ conversation_id: id }, { replace: true });
    },
  });

  const scrollRef = useRef<HTMLDivElement>(null);

  // 有新内容时滚动到底部
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [serverMessages.length, pendingUser, answer]);

  // 切换空间：清空 conversation_id（每个会话归属一个空间，避免历史消息与新空间错配）。
  // spaceId 仍由 URL 直接驱动，useSecurityChat 在 spaceId 变化时自动重载上下文。
  const handleSpaceChange = (nextSpaceId: string | number) => {
    const next = new URLSearchParams();
    next.set("space_id", String(nextSpaceId));
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex flex-1 flex-col overflow-y-auto">
        {showWelcome ? (
          <div className="flex flex-1 items-center justify-center">
            <div className="text-center">
              {/*<div className="font-mono text-sm font-semibold text-primary">&gt; _</div>*/}
              <h1 className="mt-4 font-display text-3xl font-semibold tracking-tight text-foreground">
                你想测试什么？
              </h1>
              <p className="mt-2 text-muted-foreground">输入自然语言指令，开始 API 测试</p>
            </div>
          </div>
        ) : (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6">
            {messagesLoading && (
              <div className="flex items-center gap-2 font-mono text-sm text-muted-foreground">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:300ms]" />
                <span>加载会话历史…</span>
              </div>
            )}

            {serverMessages.map((msg) =>
              msg.role === "user" ? (
                <UserBubble key={msg.id} content={msg.content} />
              ) : (
                <AssistantBubble key={msg.id} content={msg.content} />
              )
            )}

            {pendingUser !== null && <UserBubble content={pendingUser} />}

            {(isStreaming || (pendingUser !== null && answer.length > 0)) && (
              <StreamingAssistantMessage rawText={answer} isStreaming={isStreaming} />
            )}
          </div>
        )}
      </div>

      {/* Composer：固定在页面底部 */}
      <div className="shrink-0 px-4 pb-6">
        <div className="mx-auto w-full max-w-3xl">
          <ChatInput
            instruction={instruction}
            onInstructionChange={handleInstructionChange}
            onKeyDown={handleKeyDown}
            mode={mode}
            onModeChange={setMode}
            isStreaming={isStreaming}
            onSubmit={handleSubmit}
          />
          {/* 上下文条：左侧工作空间选择器，右侧 mono 提示 */}
          <div className="mt-2 flex items-center justify-between gap-2">
            <SpaceSelector value={spaceId} onChange={handleSpaceChange} />
            <span className="hidden font-mono text-[10px] uppercase tracking-widest text-muted-foreground/70 sm:block">
              Context · Space
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
