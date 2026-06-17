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
          Name
        </label>
        <Input
          id="ep-name"
          placeholder="Get Users"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div className="grid grid-cols-[120px_1fr] gap-3">
        <div className="space-y-2">
          <label htmlFor="ep-method" className="text-sm font-medium">
            Method
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
            Path
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
          Summary
        </label>
        <Input
          id="ep-summary"
          placeholder="Brief description of this endpoint"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="ep-content-type" className="text-sm font-medium">
          Content Type
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
          Parameters (JSON)
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
          Headers (JSON)
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
          Request Body (JSON)
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
          Cancel
        </Button>
        <Button type="submit" disabled={isPending}>
          {isPending ? "Saving..." : isEdit ? "Update" : "Create"}
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
          <DialogTitle>{isEdit ? "Edit Endpoint" : "Add Endpoint"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "Update the endpoint details." : "Add a new API endpoint to this project."}
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
