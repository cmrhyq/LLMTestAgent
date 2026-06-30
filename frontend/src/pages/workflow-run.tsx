import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Send, X, FileText, Loader2, CheckCircle2 } from "lucide-react";

import { useRunTest, useUploadOpenAPI } from "@/hooks/use-workflows";

const REDIRECT_DELAY_MS = 2000;

export default function WorkflowRunPage() {
  const navigate = useNavigate();
  const [instruction, setInstruction] = useState("");
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
            <h2 className="text-xl font-semibold text-foreground">Test Started</h2>
            <p className="text-muted-foreground">{data.message}</p>
            <p className="text-sm text-muted-foreground">
              Run ID:{" "}
              <span className="font-mono font-semibold text-foreground">{String(data.run_id)}</span>
            </p>
            <p className="text-xs text-muted-foreground">Redirecting to run details...</p>
          </div>
        ) : isPending ? (
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-10 w-10 animate-spin text-accent" />
            <p className="text-muted-foreground">Running test...</p>
          </div>
        ) : (
          <div className="text-center">
            <h1 className="text-3xl font-medium text-foreground">What would you like to test?</h1>
            <p className="mt-2 text-muted-foreground">
              Enter a natural language instruction to start API testing
            </p>
          </div>
        )}
      </div>

      <div className="shrink-0 px-4 pb-6">
        {file && (
          <div className="mb-2 flex items-center gap-2 rounded-lg bg-secondary px-3 py-1.5 w-fit">
            {isUploading ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : uploadedPath ? (
              <CheckCircle2 className="h-4 w-4 text-primary" />
            ) : (
              <FileText className="h-4 w-4 text-muted-foreground" />
            )}
            <span className="text-sm text-foreground">{file.name}</span>
            {isUploading && <span className="text-xs text-muted-foreground">Uploading...</span>}
            <button
              type="button"
              onClick={handleRemoveFile}
              disabled={isUploading}
              className="ml-1 rounded p-0.5 text-muted-foreground hover:bg-border hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        <div className="flex items-center gap-2 rounded-3xl border border-border bg-card px-2 py-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || isPending}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-secondary text-muted-foreground transition-colors hover:bg-border hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isUploading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Plus className="h-5 w-5" />
            )}
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.yaml,.yml"
            onChange={handleFileSelect}
            className="hidden"
          />

          <input
            type="text"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g., Run single-endpoint tests on all endpoints"
            className="flex-1 bg-transparent px-2 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            disabled={isPending}
          />

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!instruction.trim() || isPending || isUploading}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/80 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>

        <p className="mt-2 text-center text-xs text-muted-foreground">
          Attach an OpenAPI document (.json/.yaml) with the + button, or just type your instruction
        </p>
      </div>
    </div>
  );
}
