/** 流式输出末尾光标，表示内容仍在生成中。 */
export function StreamingCursor() {
  return (
    <span className="markdown-streaming-cursor ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-pulse bg-foreground align-middle" />
  );
}
