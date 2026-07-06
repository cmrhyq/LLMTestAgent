import { useState, useRef } from "react";
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
import { useStreamingMarkdown } from "@/hooks/use-streaming-markdown.ts";
import { streamChat } from "@/lib/stream.ts";
import { MarkdownRenderer } from "@/components/markdown";
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

export default function SecurityChatPage() {
  const [instruction, setInstruction] = useState("");
  const [mode, setMode] = useState("Ask");
  const [file, setFile] = useState<File | null>(null);
  const [uploadedPath, setUploadedPath] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { mutate: uploadFile, isPending: isUploading } = useUploadOpenAPI();
  const { displayText } = useStreamingMarkdown({ rawText: answer, isStreaming });

  const handleSubmit = async () => {
    if (!instruction.trim() || isStreaming || isUploading) return;

    const prompt = instruction.trim();
    setInstruction("");
    setAnswer("");
    setHasStarted(true);
    setIsStreaming(true);

    try {
      await streamChat({ instruction: prompt, api_doc_path: uploadedPath }, (chunk) => {
        setAnswer((prev) => prev + chunk);
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "请求失败";
      toast.error(message);
      setAnswer((prev) => prev || `请求失败：${message}`);
    } finally {
      setIsStreaming(false);
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

  const showWaiting = isStreaming && answer.length === 0;

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-1 items-center justify-center overflow-y-auto">
        {hasStarted ? (
          <div className="mx-auto flex w-full max-w-3xl flex-col self-start px-4 py-6">
            {showWaiting ? (
              <div className="flex items-center gap-3 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin text-accent" />
                <span>正在处理…</span>
              </div>
            ) : (
              <MarkdownRenderer content={displayText} isStreaming={isStreaming} />
            )}
          </div>
        ) : (
          <div className="text-center">
            <h1 className="text-3xl font-medium text-foreground">你想测试什么？</h1>
            <p className="mt-2 text-muted-foreground">输入自然语言指令，开始 API 测试</p>
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

          <div className="rounded-2xl border border-border bg-card px-3 py-2.5 shadow-sm transition-colors focus-within:border-[#8b949e]">
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
                      className="flex items-center gap-1.5 rounded-md border border-border bg-transparent px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {mode}
                      <ChevronDown className="h-3.5 w-3.5" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="border-border shadow-border">
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
                              className="max-w-[220px] border border-border bg-popover text-popover-foreground shadow-md"
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
                  <span className="flex min-w-0 items-center gap-1.5 rounded-md border border-border bg-secondary px-2 py-1 text-xs text-foreground">
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
                    className="flex items-center gap-1.5 rounded-md border border-border bg-transparent px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
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

          <p className="mt-2 text-center text-xs text-muted-foreground">
            通过「解析文档」添加 OpenAPI 文档（.json/.yaml），或直接输入你的指令
          </p>
        </div>
      </div>
    </div>
  );
}
