import { useState } from "react";
import { useCreateSpace, useUpdateSpace } from "@/hooks/use-spaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Space } from "@/lib/types";

interface SpaceFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** 有值 = 编辑；null / undefined = 创建。 */
  space?: Space | null;
}

interface SpaceFormContentProps {
  space?: Space | null;
  onClose: () => void;
}

const STATUS_OPTIONS = [
  { value: 1, label: "已启用" },
  { value: 0, label: "未启用" },
] as const;

function SpaceFormContent({ space, onClose }: SpaceFormContentProps) {
  const isEdit = !!space;

  const [name, setName] = useState(space?.name ?? "");
  const [baseUrl, setBaseUrl] = useState(space?.base_url ?? "");
  const [description, setDescription] = useState(space?.description ?? "");
  const [status, setStatus] = useState<number>(space?.status ?? 1);

  const createSpace = useCreateSpace();
  const updateSpace = useUpdateSpace();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (isEdit && space) {
      updateSpace.mutate(
        { id: space.id, payload: { name, base_url: baseUrl, description, status } },
        { onSuccess: () => onClose() }
      );
    } else {
      // 创建时不带 status，保持后端默认
      createSpace.mutate({ name, base_url: baseUrl, description }, { onSuccess: () => onClose() });
    }
  }

  const isPending = createSpace.isPending || updateSpace.isPending;
  const errorMessage = createSpace.error?.message || updateSpace.error?.message;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="space-name" className="text-sm font-medium">
          名称
        </label>
        <Input
          id="space-name"
          placeholder="我的 API 空间"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="space-base-url" className="text-sm font-medium">
          基础 URL
        </label>
        <Input
          id="space-base-url"
          placeholder="https://api.example.com"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="space-description" className="text-sm font-medium">
          描述
        </label>
        <Input
          id="space-description"
          placeholder="可选描述"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      {isEdit && (
        <div className="space-y-2">
          <label htmlFor="space-status" className="text-sm font-medium">
            状态
          </label>
          <select
            id="space-status"
            value={status}
            onChange={(e) => setStatus(Number(e.target.value))}
            className="flex h-9 w-full rounded-md border-thin border-border/50 bg-input px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:shadow-card"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          取消
        </Button>
        <Button type="submit" disabled={isPending}>
          {isPending ? (isEdit ? "更新中…" : "创建中…") : isEdit ? "更新" : "创建"}
        </Button>
      </DialogFooter>
    </form>
  );
}

/** 空间表单弹窗：创建 / 编辑二合一。 */
export function SpaceFormDialog({ open, onOpenChange, space }: SpaceFormDialogProps) {
  const isEdit = !!space;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "编辑空间" : "创建空间"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "更新空间信息。" : "添加一个新的 API 空间以开始测试。"}
          </DialogDescription>
        </DialogHeader>
        {open && (
          <SpaceFormContent
            key={space?.id ?? "new"}
            space={space}
            onClose={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
