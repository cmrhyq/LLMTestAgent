import { useState, useRef, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  Plus,
  Send,
  X,
  FileText,
  Loader2,
  CheckCircle2,
  ChevronDown,
  Check,
  HelpCircle,
  MessageSquare,
  ListTodo,
} from "lucide-react";
import { toast } from "sonner";

import { useUploadOpenAPI } from "@/hooks/use-workflows.ts";
import { useConversationMessages } from "@/hooks/use-conversations.ts";
import { useStreamingMarkdown } from "@/hooks/use-streaming-markdown.ts";
import { streamChat } from "@/lib/stream.ts";
import { queryKeys } from "@/lib/query-keys";
import { MarkdownRenderer } from "@/components/markdown";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const MODES = [
  {
    icon: <MessageSquare />,
    value: "Ask",
    description: "询问模式：分析接口并解答问题，不实际执行测试",
  },
  { icon: <ListTodo />, value: "Plan", description: "计划模式：生成测试计划，确认后执行测试" },
] as const;

interface UserBubbleProps {
  content: string;
}

function UserBubble({ content }: UserBubbleProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl bg-primary px-4 py-2 text-sm text-primary-foreground">
        {content}
      </div>
    </div>
  );
}

interface AssistantBubbleProps {
  content: string;
  isStreaming?: boolean;
}

function AssistantBubble({ content, isStreaming = false }: AssistantBubbleProps) {
  return (
    <div className="flex justify-start">
      <div className="w-full min-w-0">
        <MarkdownRenderer content={content} isStreaming={isStreaming} />
      </div>
    </div>
  );
}

function StreamingAssistantMessage({
  rawText,
  isStreaming,
}: {
  rawText: string;
  isStreaming: boolean;
}) {
  const { displayText } = useStreamingMarkdown({ rawText, isStreaming });
  if (isStreaming && rawText.length === 0) {
    return (
      <div className="flex items-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin text-accent" />
        <span>正在处理…</span>
      </div>
    );
  }
  return <AssistantBubble content={displayText} isStreaming={isStreaming} />;
}

export default function SecurityChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const conversationId = searchParams.get("conversation_id");
  const projectId = searchParams.get("project_id");
  const queryClient = useQueryClient();

  const [instruction, setInstruction] = useState("");
  const [mode, setMode] = useState("Ask");
  const [file, setFile] = useState<File | null>(null);
  const [uploadedPath, setUploadedPath] = useState<string | null>(null);

  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { mutate: uploadFile, isPending: isUploading } = useUploadOpenAPI();
  const { data: messagesData, isLoading: messagesLoading } =
    useConversationMessages(conversationId);
  const serverMessages = messagesData?.items ?? [];

  // 切换会话时清空进行中的本地 overlay（渲染期依据上一次会话 ID 重置，避免在 effect 中 setState）
  const [trackedConversationId, setTrackedConversationId] = useState(conversationId);
  if (conversationId !== trackedConversationId) {
    setTrackedConversationId(conversationId);
    setPendingUser(null);
    setAnswer("");
  }

  // 有新内容时滚动到底部
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [serverMessages.length, pendingUser, answer]);

  const handleSubmit = async () => {
    if (!instruction.trim() || isStreaming || isUploading) return;

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
          api_doc_path: uploadedPath,
          conversation_id: conversationId ?? undefined,
          mode,
          project_id: projectId ?? undefined,
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
        // 后端在连接关闭前已落库 user/assistant 消息，切换后重新拉取即可显示完整对话
        await queryClient.invalidateQueries({ queryKey: queryKeys.conversations.all });
        setSearchParams({ conversation_id: newConversationId }, { replace: true });
      } else if (conversationId) {
        // 存量会话：刷新消息与会话列表后清空 overlay
        await queryClient.invalidateQueries({
          queryKey: queryKeys.conversations.messages(conversationId),
        });
        queryClient.invalidateQueries({ queryKey: queryKeys.conversations.all });
        setPendingUser(null);
        setAnswer("");
      }
      // 其余情况（请求在建立会话前失败）：保留 overlay 展示错误信息
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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setUploadedPath(null);
      const formData = new FormData();
      formData.append("file", selected);
      uploadFile(formData, {
        onSuccess: (res) => {
          setUploadedPath(res.path);
        },
        onError: () => {
          setFile(null);
          setUploadedPath(null);
        },
      });
    }
    e.target.value = "";
  };

  const handleRemoveFile = () => {
    setFile(null);
    setUploadedPath(null);
  };

  const hasMessages = serverMessages.length > 0 || pendingUser !== null || isStreaming;
  const showWelcome = !hasMessages && !messagesLoading;

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
        <div className="mx-auto w-full max-w-3xl">
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.yaml,.yml"
            onChange={handleFileSelect}
            className="hidden"
          />

          <div className="rounded-xl border border-border bg-background px-3 py-2.5 shadow-card transition-shadow focus-within:border-accent/30 focus-within:shadow-elevated">
            {/* 输入框 */}
            <textarea
              value={instruction}
              onChange={handleInstructionChange}
              onKeyDown={handleKeyDown}
              placeholder="例如：帮我为登录接口设计一组测试用例"
              rows={1}
              disabled={isStreaming}
              className="max-h-40 w-full resize-none bg-transparent px-1 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-60"
            />

            {/* 工具栏 */}
            <div className="mt-1.5 flex items-center justify-between gap-2">
              <div className="flex min-w-0 items-center gap-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      className={cn(
                        "flex items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground shadow-xs transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                      )}
                    >
                      {mode}
                      <ChevronDown className="h-3.5 w-3.5" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="shadow-popover">
                    <TooltipProvider delayDuration={200}>
                      {MODES.map((m) => (
                        <DropdownMenuItem key={m.value} onClick={() => setMode(m.value)}>
                          {m.icon}
                          <span className="flex-1">{m.value}</span>
                          {mode === m.value && <Check className="h-3.5 w-3.5" />}
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span
                                onClick={(e) => e.stopPropagation()}
                                onPointerDown={(e) => e.stopPropagation()}
                                className="text-muted-foreground transition-colors hover:text-foreground"
                              >
                                <HelpCircle className="h-3.5 w-3.5" />
                              </span>
                            </TooltipTrigger>
                            <TooltipContent
                              side="right"
                              className="max-w-[220px] border-0 bg-popover text-popover-foreground shadow-popover"
                            >
                              {m.description}
                            </TooltipContent>
                          </Tooltip>
                        </DropdownMenuItem>
                      ))}
                    </TooltipProvider>
                  </DropdownMenuContent>
                </DropdownMenu>

                {file ? (
                  <span className="flex min-w-0 items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs text-foreground">
                    {isUploading ? (
                      <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />
                    ) : uploadedPath ? (
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-primary" />
                    ) : (
                      <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    )}
                    <span className="truncate max-w-[160px]">{file.name}</span>
                    <button
                      type="button"
                      onClick={handleRemoveFile}
                      disabled={isUploading}
                      className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:bg-border hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading || isStreaming}
                    className="flex items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground shadow-xs transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    解析文档
                    <Plus className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              <button
                type="button"
                onClick={handleSubmit}
                disabled={!instruction.trim() || isStreaming || isUploading}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/80 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
