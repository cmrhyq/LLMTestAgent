import { Briefcase, Check, ChevronDown, Loader2 } from "lucide-react";

import { useSpaces } from "@/hooks/use-spaces";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import type { Id, Space } from "@/lib/types";

interface SpaceSelectorProps {
  /** 当前选中的空间 id；为 null/undefined 时显示占位符。 */
  value: Id | null;
  /** 用户从下拉列表选中某项时回调，传入空间 id。 */
  onChange(spaceId: Id): void;
  /** 未选中时的占位文案，默认 "选择工作空间"。 */
  placeholder?: string;
  /** 是否禁用（由父组件控制）。 */
  disabled?: boolean;
}

/** 把不同类型 id 规范成字符串后再比较，避免 number/string 不一致。 */
function toIdString(id: Id | null | undefined): string | null {
  if (id === null || id === undefined) return null;
  return String(id);
}

function findCurrentSpace(spaces: Space[], value: Id | null): Space | undefined {
  const target = toIdString(value);
  if (target === null) return undefined;
  return spaces.find((s) => String(s.id) === target);
}

/**
 * 选择工作空间 pill 按钮。
 *
 * 视觉与 ChatInput 内 mode 选择器保持一致（同一段 className）：
 * - 公文包图标 + 空间名 / 占位符 + ChevronDown
 * - 加载中：图标位置变为 Loader2 旋转
 * - 错误 / 列表为空：按钮 disabled + 占位文案
 * - 下拉内容与 ChatInput dropdown 同款（shadow-popover），支持空态提示行
 */
export function SpaceSelector({
  value,
  onChange,
  placeholder = "选择工作空间",
  disabled,
}: SpaceSelectorProps) {
  const { data, isLoading, isError } = useSpaces({ page_size: 100, status: 1 });
  const spaces = data?.items ?? [];
  const current = findCurrentSpace(spaces, value);
  const isEmpty = !isLoading && !isError && spaces.length === 0;
  const isDisabled = disabled || isError || isEmpty;

  const label = isLoading ? "加载中…" : current?.name ?? placeholder;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          disabled={isDisabled}
          className={cn(
            "flex items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground shadow-xs transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
          )}
        >
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Briefcase className="h-3.5 w-3.5" />
          )}
          <span className="max-w-[160px] truncate">{label}</span>
          <ChevronDown className="h-3.5 w-3.5" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="min-w-[180px] shadow-popover" align="start">
        {spaces.length === 0 ? (
          <DropdownMenuItem disabled className="text-muted-foreground">
            暂无可用空间，请先在仪表盘创建
          </DropdownMenuItem>
        ) : (
          spaces.map((space) => {
            const isSelected = current?.id === space.id;
            return (
              <DropdownMenuItem
                key={String(space.id)}
                onClick={() => onChange(space.id)}
                className="flex items-center gap-2"
              >
                <Briefcase className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <span className="flex-1 truncate">{space.name}</span>
                {isSelected && <Check className="h-3.5 w-3.5 shrink-0 text-primary" />}
              </DropdownMenuItem>
            );
          })
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}