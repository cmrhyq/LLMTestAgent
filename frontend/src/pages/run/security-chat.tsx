import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { useSecurityChat } from "@/hooks/use-security-chat.ts";
import { UserBubble, AssistantBubble, StreamingAssistantMessage } from "@/components/chat/message-bubbles";
import { ChatInput } from "@/components/chat/chat-input";

export default function SecurityChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const conversationId = searchParams.get("conversation_id");
  const projectId = searchParams.get("project_id");

  const {
    instruction,

    mode,
    setMode,
    file,
    uploadedPath,
    isUploading,
    pendingUser,
    answer,
    isStreaming,
    serverMessages,
    messagesLoading,
    handleSubmit,
    handleKeyDown,
    handleInstructionChange,
    handleFileSelect,
    handleRemoveFile,

    showWelcome,
  } = useSecurityChat({
    conversationId,
    projectId,
    onConversationCreated: (id) => {
      setSearchParams({ conversation_id: id }, { replace: true });
    },
  });

  const scrollRef = useRef<HTMLDivElement>(null);

  // 有新内容时滚动到底部
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [serverMessages.length, pendingUser, answer]);

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex flex-1 flex-col overflow-y-auto">
        {showWelcome ? (
          <div className="flex flex-1 items-center justify-center">
            <div className="text-center">
              <h1 className="text-3xl font-medium text-foreground">你想测试什么？</h1>
              <p className="mt-2 text-muted-foreground">输入自然语言指令，开始 API 测试</p>
            </div>
          </div>
        ) : (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6">
            {messagesLoading && (
              <div className="flex items-center gap-3 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin text-accent" />
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

      <div className="shrink-0 px-4 pb-6">
        <ChatInput
          instruction={instruction}
          onInstructionChange={handleInstructionChange}
          onKeyDown={handleKeyDown}
          mode={mode}
          onModeChange={setMode}
          file={file}
          isUploading={isUploading}
          uploadedPath={uploadedPath}
          isStreaming={isStreaming}
          onFileSelect={handleFileSelect}
          onRemoveFile={handleRemoveFile}
          onSubmit={handleSubmit}
        />
      </div>
    </div>
  );
}
