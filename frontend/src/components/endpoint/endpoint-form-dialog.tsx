import { useState } from "react";
import { useCreateEndpoint, useUpdateEndpoint } from "@/hooks/use-endpoints";
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
import type { Endpoint } from "@/lib/types";

const HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"] as const;

interface EndpointFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string | number;
  endpoint?: Endpoint | null;
}

interface EndpointFormContentProps {
  projectId: string | number;
  endpoint?: Endpoint | null;
  onClose: () => void;
}

function EndpointFormContent({ projectId, endpoint, onClose }: EndpointFormContentProps) {
  const isEdit = !!endpoint;

  const [name, setName] = useState(endpoint?.name ?? "");
  const [path, setPath] = useState(endpoint?.path ?? "");
  const [method, setMethod] = useState(endpoint?.method ?? "GET");
  const [summary, setSummary] = useState(endpoint?.summary ?? "");
  const [contentType, setContentType] = useState(endpoint?.content_type ?? "application/json");
  const [params, setParams] = useState(endpoint?.params ?? "");
  const [headers, setHeaders] = useState(endpoint?.headers ?? "");
  const [body, setBody] = useState(endpoint?.body ?? "");

  const createEndpoint = useCreateEndpoint();
  const updateEndpoint = useUpdateEndpoint();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: Partial<Endpoint> = {
      project_id: projectId,
      name,
      path,
      method,
      summary,
      content_type: contentType,
      params,
      headers,
      body,
      operation_id: name.toLowerCase().replace(/\s+/g, "_"),
    };

    if (isEdit && endpoint) {
      updateEndpoint.mutate({ id: endpoint.id, payload }, { onSuccess: () => onClose() });
    } else {
      createEndpoint.mutate(payload, {
        onSuccess: () => onClose(),
      });
    }
  }

  const isPending = createEndpoint.isPending || updateEndpoint.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="ep-name" className="text-sm font-medium">
          名称
        </label>
        <Input
          id="ep-name"
          placeholder="获取用户列表"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div className="grid grid-cols-[120px_1fr] gap-3">
        <div className="space-y-2">
          <label htmlFor="ep-method" className="text-sm font-medium">
            方法
          </label>
          <select
            id="ep-method"
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="flex h-9 w-full rounded-md border border-border bg-input px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {HTTP_METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <label htmlFor="ep-path" className="text-sm font-medium">
            路径
          </label>
          <Input
            id="ep-path"
            placeholder="/api/users"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            required
          />
        </div>
      </div>

      <div className="space-y-2">
        <label htmlFor="ep-summary" className="text-sm font-medium">
          摘要
        </label>
        <Input
          id="ep-summary"
          placeholder="该接口的简要描述"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="ep-content-type" className="text-sm font-medium">
          内容类型
        </label>
        <Input
          id="ep-content-type"
          placeholder="application/json"
          value={contentType}
          onChange={(e) => setContentType(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="ep-params" className="text-sm font-medium">
          参数（JSON）
        </label>
        <Textarea
          id="ep-params"
          placeholder='[{"name": "id", "in": "path", "required": true}]'
          value={params}
          onChange={(e) => setParams(e.target.value)}
          rows={3}
          className="font-mono text-xs"
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="ep-headers" className="text-sm font-medium">
          请求头（JSON）
        </label>
        <Textarea
          id="ep-headers"
          placeholder='{"Authorization": "Bearer token"}'
          value={headers}
          onChange={(e) => setHeaders(e.target.value)}
          rows={2}
          className="font-mono text-xs"
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="ep-body" className="text-sm font-medium">
          请求体（JSON）
        </label>
        <Textarea
          id="ep-body"
          placeholder='{"type": "object", "properties": {...}}'
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={3}
          className="font-mono text-xs"
        />
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

export function EndpointFormDialog({
  open,
  onOpenChange,
  projectId,
  endpoint,
}: EndpointFormDialogProps) {
  const isEdit = !!endpoint;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "编辑接口" : "添加接口"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "更新接口详情。" : "为该项目添加一个新的 API 接口。"}
          </DialogDescription>
        </DialogHeader>
        {open && (
          <EndpointFormContent
            key={endpoint?.id ?? "new"}
            projectId={projectId}
            endpoint={endpoint}
            onClose={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
