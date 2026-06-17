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
  projectId: string | number;
  environment?: Environment | null;
}

interface EnvironmentFormContentProps {
  projectId: string | number;
  environment?: Environment | null;
  onClose: () => void;
}

function EnvironmentFormContent({ projectId, environment, onClose }: EnvironmentFormContentProps) {
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
      project_id: projectId,
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
          Name
        </label>
        <Input
          id="env-name"
          placeholder="Production"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="env-base-url" className="text-sm font-medium">
          Base URL
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
          Description
        </label>
        <Input
          id="env-description"
          placeholder="Optional description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="env-variables" className="text-sm font-medium">
          Variables (JSON)
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
          Set as default environment
        </label>
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

export function EnvironmentFormDialog({
  open,
  onOpenChange,
  projectId,
  environment,
}: EnvironmentFormDialogProps) {
  const isEdit = !!environment;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Environment" : "Add Environment"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update the environment configuration."
              : "Add a new environment for this project."}
          </DialogDescription>
        </DialogHeader>
        {open && (
          <EnvironmentFormContent
            key={environment?.id ?? "new"}
            projectId={projectId}
            environment={environment}
            onClose={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
