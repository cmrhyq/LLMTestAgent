import { Loader2 } from "lucide-react";

import { useStreamingMarkdown } from "@/hooks/use-streaming-markdown.ts";
import { MarkdownRenderer } from "@/components/markdown";

export function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl bg-primary px-4 py-2 text-sm text-primary-foreground">
        {content}
      </div>
    </div>
  );
}

export function AssistantBubble({ content, isStreaming = false }: { content: string; isStreaming?: boolean }) {
  return (
    <div className="flex justify-start">
      <div className="w-full min-w-0">
        <MarkdownRenderer content={content} isStreaming={isStreaming} />
      </div>
    </div>
  );
}

export function StreamingAssistantMessage({ rawText, isStreaming }: { rawText: string; isStreaming: boolean }) {
  const { displayText } = useStreamingMarkdown({ rawText, isStreaming });
  if (isStreaming && rawText.length === 0) {
    return (
      <div className="flex items-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin text-accent" />
        <span>正在处理…</span>
      </div>
    );
  }
  return <AssistantBubble content={displayText} isStreaming={isStreaming} />;
}
