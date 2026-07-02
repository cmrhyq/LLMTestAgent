import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
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
} from "lucide-react";

import { useRunTest, useUploadOpenAPI } from "@/hooks/use-workflows.ts";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const REDIRECT_DELAY_MS = 2000;
const MODES = [
  { value: "Ask", description: "询问模式：分析接口并解答问题，不实际执行测试" },
  { value: "Plan", description: "计划模式：生成测试计划，确认后执行测试" },
] as const;

export default function WorkflowRunPage() {
  const navigate = useNavigate();
  const [instruction, setInstruction] = useState("");
  const [mode, setMode] = useState("Ask");
  const [file, setFile] = useState<File | null>(null);
  const [uploadedPath, setUploadedPath] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { mutate, isPending, isSuccess, data } = useRunTest();
  const { mutate: uploadFile, isPending: isUploading } = useUploadOpenAPI();

  useEffect(() => {
    if (isSuccess && data?.run_id) {
      const timer = setTimeout(() => {
        navigate(`/runs/${data.run_id}`);
      }, REDIRECT_DELAY_MS);
      return () => clearTimeout(timer);
    }
  }, [isSuccess, data, navigate]);

  const handleSubmit = () => {
    if (!instruction.trim() || isPending || isUploading) return;
    mutate({
      instruction: instruction.trim(),
      api_doc_path: uploadedPath,
    });
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

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-1 items-center justify-center">
        {isSuccess && data ? (
          <div className="flex flex-col items-center gap-4">
            <CheckCircle2 className="h-16 w-16 text-primary" />
            <h2 className="text-xl font-semibold text-foreground">测试已启动</h2>
            <p className="text-muted-foreground">{data.message}</p>
            <p className="text-sm text-muted-foreground">
              运行 ID：{" "}
              <span className="font-mono font-semibold text-foreground">{String(data.run_id)}</span>
            </p>
            <p className="text-xs text-muted-foreground">正在跳转到运行详情…</p>
          </div>
        ) : isPending ? (
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-10 w-10 animate-spin text-accent" />
            <p className="text-muted-foreground">正在运行测试…</p>
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
              placeholder="例如：对“XXX”项目的所有接口运行单接口测试"
              rows={1}
              disabled={isPending}
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
                    disabled={isUploading || isPending}
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
                disabled={!instruction.trim() || isPending || isUploading}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/80 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
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
