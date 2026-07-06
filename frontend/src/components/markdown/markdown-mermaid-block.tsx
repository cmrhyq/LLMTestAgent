import { useEffect, useId, useState } from "react";

interface MarkdownMermaidBlockProps {
  code: string;
  isStreaming: boolean;
}

interface RenderedMermaid {
  code: string;
  svg: string;
}

let mermaidInitialized = false;

async function renderMermaid(id: string, code: string): Promise<string> {
  const mermaid = (await import("mermaid")).default;

  if (!mermaidInitialized) {
    mermaid.initialize({
      startOnLoad: false,
      theme: "neutral",
      securityLevel: "strict",
      fontFamily: "inherit",
    });
    mermaidInitialized = true;
  }

  const { svg } = await mermaid.render(id, code);
  return svg;
}

/**
 * Mermaid 流程图/时序图块：流式期间显示源码，结束后渲染 SVG。
 * 使用 neutral 浅色主题，确保在浅色模式下对比度足够。
 */
export function MarkdownMermaidBlock({ code, isStreaming }: MarkdownMermaidBlockProps) {
  const [rendered, setRendered] = useState<RenderedMermaid | null>(null);
  const rawId = useId().replace(/:/g, "");
  const renderId = `mermaid-${rawId}`;

  useEffect(() => {
    if (isStreaming) return;

    let cancelled = false;

    renderMermaid(renderId, code)
      .then((svg) => {
        if (!cancelled) {
          setRendered({ code, svg });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setRendered(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [code, isStreaming, renderId]);

  const svg = rendered?.code === code ? rendered.svg : null;

  if (isStreaming || !svg) {
    return (
      <pre className="markdown-code-block">
        <code className="language-mermaid">{code}</code>
      </pre>
    );
  }

  return <div className="markdown-mermaid-block" dangerouslySetInnerHTML={{ __html: svg }} />;
}
