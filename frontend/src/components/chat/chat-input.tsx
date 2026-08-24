import {
  Check,
  ChevronDown,
  HelpCircle,
  Loader2,
  MessageSquare,
  ListTodo,
  Send,
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
  isStreaming: boolean;
  onSubmit(): void;
}

export function ChatInput({
  instruction,
  onInstructionChange,
  onKeyDown,
  mode,
  onModeChange,
  isStreaming,
  onSubmit,
}: ChatInputProps) {
  return (
    <div className="mx-auto w-full max-w-3xl">
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
            placeholder="今天帮你做些什么？例如：帮我为登录接口设计一组测试用例"
            rows={1}
            disabled={isStreaming}
            className="max-h-40 w-full resize-none bg-transparent px-0 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-60"
          />
        </div>

        {/* 工具栏 */}
        <div className="mt-1.5 flex items-center justify-between gap-2">
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
            </DropdownMenuContent>
          </DropdownMenu>

          <button
            type="button"
            onClick={onSubmit}
            disabled={!instruction.trim() || isStreaming}
            aria-label="发送"
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
