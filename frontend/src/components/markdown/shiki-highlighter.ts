import { createHighlighter, type Highlighter } from "shiki";

const SHIKI_THEME = "github-light";
const SHIKI_LANGS = [
  "json",
  "bash",
  "shell",
  "python",
  "typescript",
  "javascript",
  "yaml",
  "http",
  "markdown",
  "text",
] as const;

const HIGHLIGHT_LANGS = new Set<string>(SHIKI_LANGS);

/** 仅对编程语言启用 Shiki；text/ASCII 图等保持纯文本 pre，避免破坏对齐。 */
export function shouldHighlightLanguage(language: string): boolean {
  return HIGHLIGHT_LANGS.has(language) && language !== "text";
}

let highlighterPromise: Promise<Highlighter> | null = null;

/** Shiki 高亮器单例，避免每个代码块重复加载 wasm / 主题。 */
export function getShikiHighlighter(): Promise<Highlighter> {
  if (!highlighterPromise) {
    highlighterPromise = createHighlighter({
      themes: [SHIKI_THEME],
      langs: [...SHIKI_LANGS],
    });
  }
  return highlighterPromise;
}

export { SHIKI_THEME };
