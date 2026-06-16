import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { FileUp, CheckCircle2, Loader2, AlertCircle } from "lucide-react";

import { useParseOpenAPI } from "@/hooks/use-workflows";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const ACCEPTED_TYPES = [".json", ".yaml", ".yml"];

export default function WorkflowParsePage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const { mutate, isPending, isSuccess, isError, error, data } = useParseOpenAPI();

  const handleFileSelect = useCallback((file: File) => {
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (ACCEPTED_TYPES.includes(ext)) {
      setSelectedFile(file);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelect(file);
    },
    [handleFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFileSelect(file);
    },
    [handleFileSelect]
  );

  const handleParse = useCallback(() => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append("file", selectedFile);
    mutate(formData);
  }, [selectedFile, mutate]);

  if (isSuccess && data) {
    return (
      <div className="mx-auto max-w-lg space-y-6 pt-12">
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <CheckCircle2 className="h-16 w-16 text-emerald-500" />
            <h2 className="text-xl font-semibold">Parsing Complete</h2>
            <p className="text-muted-foreground">
              Successfully parsed{" "}
              <span className="font-semibold text-foreground">{data.endpoints_count}</span>{" "}
              endpoints.
            </p>
            <Button onClick={() => navigate("/dashboard")} className="mt-4">
              Go to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight text-foreground">Parse OpenAPI Document</h1>

      <Card>
        <CardHeader>
          <CardTitle>Upload API Document</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            role="button"
            tabIndex={0}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                fileInputRef.current?.click();
              }
            }}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-16 transition-colors ${
              isDragOver
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25 hover:border-primary/50"
            }`}
          >
            <FileUp className="mb-4 h-12 w-12 text-muted-foreground" />
            <p className="text-sm font-medium text-muted-foreground">
              Drag &amp; drop or click to upload
            </p>
            <p className="mt-1 text-xs text-muted-foreground/70">Accepts .json, .yaml, .yml</p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.yaml,.yml"
            onChange={handleInputChange}
            className="hidden"
          />

          {selectedFile && (
            <div className="mt-4 flex items-center justify-between rounded-md border bg-muted/50 px-4 py-3">
              <span className="truncate text-sm font-medium">{selectedFile.name}</span>
              <Button onClick={handleParse} disabled={isPending} size="sm">
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Parse
              </Button>
            </div>
          )}

          {isError && (
            <div className="mt-4 flex items-center gap-2 rounded-md border border-destructive/50 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error?.message ?? "Failed to parse document"}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
