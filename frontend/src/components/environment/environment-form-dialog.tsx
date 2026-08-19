import { useState } from "react";
import { useCreateEnvironment, useUpdateEnvironment } from "@/hooks/use-environments";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Environment } from "@/lib/types";

interface EnvironmentFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  spaceId: string | number;
  environment?: Environment | null;
}

interface EnvironmentFormContentProps {
  spaceId: string | number;
  environment?: Environment | null;
  onClose: () => void;
}

function EnvironmentFormContent({ spaceId, environment, onClose }: EnvironmentFormContentProps) {
  const isEdit = !!environment;

  const [name, setName] = useState(environment?.name ?? "");
  const [baseUrl, setBaseUrl] = useState(environment?.base_url ?? "");
  const [description, setDescription] = useState(environment?.description ?? "");
  const [variables, setVariables] = useState(environment?.variables ?? "");
  const [isDefault, setIsDefault] = useState(environment?.is_default === 1);

  const createEnvironment = useCreateEnvironment();
  const updateEnvironment = useUpdateEnvironment();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: Partial<Environment> = {
      space_id: spaceId,
      name,
      base_url: baseUrl,
      description,
      variables,
      is_default: isDefault ? 1 : 0,
    };

    if (isEdit && environment) {
      updateEnvironment.mutate({ id: environment.id, payload }, { onSuccess: () => onClose() });
    } else {
      createEnvironment.mutate(payload, {
        onSuccess: () => onClose(),
      });
    }
  }

  const isPending = createEnvironment.isPending || updateEnvironment.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="env-name" className="text-sm font-medium">
          名称
        </label>
        <Input
          id="env-name"
          placeholder="生产环境"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="env-base-url" className="text-sm font-medium">
          基础 URL
        </label>
        <Input
          id="env-base-url"
          placeholder="https://api.example.com"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="env-description" className="text-sm font-medium">
          描述
        </label>
        <Input
          id="env-description"
          placeholder="可选描述"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="env-variables" className="text-sm font-medium">
          变量（JSON）
        </label>
        <Textarea
          id="env-variables"
          placeholder='{"enable": "xxx", "TIMEOUT": "30"}'
          value={variables}
          onChange={(e) => setVariables(e.target.value)}
          rows={3}
          className="font-mono text-xs"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          id="env-default"
          type="checkbox"
          checked={isDefault}
          onChange={(e) => setIsDefault(e.target.checked)}
          className="h-4 w-4 rounded border-border"
        />
        <label htmlFor="env-default" className="text-sm font-medium">
          设为默认环境
        </label>
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          取消
        </Button>
        <Button type="submit" disabled={isPending}>
          {isPending ? "保存中…" : isEdit ? "更新" : "创建"}
        </Button>
      </DialogFooter>
    </form>
  );
}

export function EnvironmentFormDialog({
  open,
  onOpenChange,
  spaceId,
  environment,
}: EnvironmentFormDialogProps) {
  const isEdit = !!environment;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "编辑环境" : "添加环境"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "更新环境配置。" : "为该空间添加一个新环境。"}
          </DialogDescription>
        </DialogHeader>
        {open && (
          <EnvironmentFormContent
            key={environment?.id ?? "new"}
            spaceId={spaceId}
            environment={environment}
            onClose={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
