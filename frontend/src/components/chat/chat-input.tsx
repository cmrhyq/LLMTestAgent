import { useRef } from "react";
import {
  Check,
  CheckCircle2,
  ChevronDown,
  FileText,
  HelpCircle,
  Loader2,
  MessageSquare,
  ListTodo,
  Plus,
  Send,
  X,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu.tsx";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip.tsx";
import { cn } from "@/lib/utils";

const MODES = [
  {
    icon: <MessageSquare />,
    value: "Ask",
    description: "询问模式：分析接口并解答问题，不实际执行测试",
  },
  { icon: <ListTodo />, value: "Plan", description: "计划模式：生成测试计划，确认后执行测试" },
] as const;

export interface ChatInputProps {
  instruction: string;
  onInstructionChange(e: React.ChangeEvent<HTMLTextAreaElement>): void;
  onKeyDown(e: React.KeyboardEvent): void;
  mode: string;
  onModeChange(mode: string): void;
  file: File | null;
  isUploading: boolean;
  uploadedPath: string | null;
  isStreaming: boolean;
  onFileSelect(e: React.ChangeEvent<HTMLInputElement>): void;
  onRemoveFile(): void;
  onSubmit(): void;
}

export function ChatInput({
  instruction,
  onInstructionChange,
  onKeyDown,
  mode,
  onModeChange,
  file,
  isUploading,
  uploadedPath,
  isStreaming,
  onFileSelect,
  onRemoveFile,
  onSubmit,
}: ChatInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="mx-auto w-full max-w-3xl">
      <input
        ref={fileInputRef}
        type="file"
        accept=".json,.yaml,.yml"
        onChange={onFileSelect}
        className="hidden"
      />

      <div className="rounded-[4px] border border-border bg-card px-3 py-2.5 shadow-xs transition-all duration-200 ease-out-expo focus-within:border-primary/50 focus-within:shadow-input">
        {/* 输入框：mono 提示符 + 多行输入 */}
        <div className="flex items-start gap-2">
          <span
            className="select-none pt-2 font-mono text-sm font-semibold text-primary"
            aria-hidden="true"
          >
            ❯
          </span>
          <textarea
            value={instruction}
            onChange={onInstructionChange}
            onKeyDown={onKeyDown}
            placeholder="例如：帮我为登录接口设计一组测试用例"
            rows={1}
            disabled={isStreaming}
            className="max-h-40 w-full resize-none bg-transparent px-0 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-60"
          />
        </div>

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
                    <DropdownMenuItem key={m.value} onClick={() => onModeChange(m.value)}>
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
                  onClick={onRemoveFile}
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
            onClick={onSubmit}
            disabled={!instruction.trim() || isStreaming || isUploading}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors duration-200 ease-out-expo hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
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
  );
}
