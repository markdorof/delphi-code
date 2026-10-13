import { useQuery } from "@tanstack/react-query";
import type { CSSProperties } from "react";
import { canHighlight, highlightedLines } from "./snippetHighlighter";

interface SnippetToken {
  content: string;
  offset: number;
  htmlStyle?: Record<string, string>;
}

export function HighlightedSnippet({
  text,
  language,
  firstLineNumber,
}: {
  text: string;
  language: string;
  firstLineNumber: number;
}) {
  const code = text.replace(/\n+$/, "");
  const highlighted = useQuery({
    queryKey: ["highlighted-snippet", language, code],
    queryFn: () => highlightedLines(code, language),
    enabled: canHighlight(language),
    staleTime: Number.POSITIVE_INFINITY,
  });
  const lines: SnippetToken[][] = highlighted.data ?? unhighlightedLines(code);

  return (
    <pre className="highlighted-snippet overflow-x-auto rounded-md bg-muted px-3 py-2 font-mono text-[13px] leading-relaxed">
      <code className="table">
        {lines.map((tokens, index) => {
          const lineNumber = firstLineNumber + index;
          return (
            <span key={lineNumber} className="table-row">
              <span className="table-cell select-none pr-4 text-right text-muted-foreground">{lineNumber}</span>
              <span className="table-cell whitespace-pre">
                {tokens.map((token) => (
                  <span key={token.offset} style={token.htmlStyle as CSSProperties | undefined}>
                    {token.content}
                  </span>
                ))}
              </span>
            </span>
          );
        })}
      </code>
    </pre>
  );
}

function unhighlightedLines(code: string): SnippetToken[][] {
  let offset = 0;
  return code.split("\n").map((line) => {
    const token = { content: line, offset };
    offset += line.length + 1;
    return [token];
  });
}
