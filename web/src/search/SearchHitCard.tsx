import { CheckIcon, CopyIcon, ExternalLinkIcon } from "lucide-react";
import { useState } from "react";
import type { components } from "@/api/schema";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { HighlightedSnippet } from "./HighlightedSnippet";

type SearchHit = components["schemas"]["SearchHitResponse"];

const COPIED_CONFIRMATION_MILLISECONDS = 1500;

export function SearchHitCard({ hit, projectKey }: { hit: SearchHit; projectKey: string }) {
  const lines = hit.start_line === hit.end_line ? `${hit.start_line}` : `${hit.start_line}–${hit.end_line}`;
  return (
    <article className="min-w-0 rounded-lg border">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b px-3 py-2">
        <div className="min-w-0 basis-full sm:basis-0 sm:flex-1">
          <p className="truncate font-mono text-sm">
            {hit.path}
            <span className="text-muted-foreground">:{lines}</span>
          </p>
          <p className="truncate text-muted-foreground text-xs">{hit.key ?? projectKey}</p>
        </div>
        <Badge variant="secondary">{hit.language}</Badge>
        <span className="text-muted-foreground text-xs tabular-nums" title="Higher means a closer match">
          {hit.score.toFixed(2)}
        </span>
        {hit.url ? (
          <Button asChild variant="ghost" size="sm">
            <a href={hit.url} target="_blank" rel="noreferrer">
              <ExternalLinkIcon />
              Open
            </a>
          </Button>
        ) : (
          <CopyLocationButton location={`${hit.path}:${hit.start_line}`} />
        )}
      </header>
      <div className="p-2">
        <HighlightedSnippet text={hit.text} language={hit.language} firstLineNumber={hit.start_line} />
      </div>
    </article>
  );
}

function CopyLocationButton({ location }: { location: string }) {
  const [copied, setCopied] = useState(false);
  async function copyLocation() {
    await navigator.clipboard.writeText(location);
    setCopied(true);
    setTimeout(() => setCopied(false), COPIED_CONFIRMATION_MILLISECONDS);
  }
  return (
    <Button variant="ghost" size="sm" onClick={copyLocation} aria-label={`Copy ${location}`}>
      {copied ? <CheckIcon /> : <CopyIcon />}
      {copied ? "Copied" : "Copy path"}
    </Button>
  );
}
