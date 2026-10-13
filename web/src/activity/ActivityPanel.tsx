import { CheckCircle2Icon, LoaderCircleIcon, XCircleIcon, XIcon } from "lucide-react";
import { FailureMessage } from "@/components/FailureMessage";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useWriteActivity } from "./WriteActivityProvider";

export function ActivityPanel() {
  const { activity, dismissActivity } = useWriteActivity();
  if (activity === null) {
    return null;
  }
  const { repository, embedded } = activity;
  return (
    <section aria-label="Activity" aria-live="polite" className="mb-6 grid gap-3 rounded-lg border bg-muted/40 p-4">
      <header className="flex items-center gap-2">
        {activity.state === "running" && <LoaderCircleIcon className="size-4 animate-spin" aria-hidden />}
        {activity.state === "succeeded" && <CheckCircle2Icon className="size-4 text-primary" aria-hidden />}
        {activity.state === "failed" && <XCircleIcon className="size-4 text-destructive" aria-hidden />}
        <h2 className="flex-1 font-medium">{activity.title}</h2>
        {activity.state !== "running" && (
          <Button variant="ghost" size="icon" onClick={dismissActivity} aria-label="Dismiss">
            <XIcon />
          </Button>
        )}
      </header>
      {activity.state === "running" && (
        <div className="grid gap-2 text-sm">
          {activity.listing && <p className="text-muted-foreground">{activity.listing}…</p>}
          {repository && (
            <p className="truncate">
              <span className="text-muted-foreground">
                {repository.position} of {repository.count} ·{" "}
              </span>
              <span className="font-mono">{repository.key}</span>
            </p>
          )}
          {activity.stage && <p className="text-muted-foreground first-letter:uppercase">{activity.stage}</p>}
          {embedded && (
            <div className="grid gap-1">
              <Progress value={(100 * embedded.done) / Math.max(embedded.total, 1)} aria-label="Files embedded" />
              <p className="text-muted-foreground text-xs tabular-nums">
                {embedded.done} of {embedded.total} files embedded
              </p>
            </div>
          )}
        </div>
      )}
      {activity.outcomes.length > 0 && (
        <ul className="grid max-h-48 gap-1 overflow-y-auto text-sm">
          {activity.outcomes.map((outcome) => (
            <li key={outcome.key} className="flex gap-2">
              <span className={outcome.succeeded ? "text-primary" : "text-destructive"}>
                {outcome.succeeded ? "✓" : "✕"}
              </span>
              <span className="min-w-0 truncate font-mono">{outcome.key}</span>
              <span className="ml-auto shrink-0 text-muted-foreground">{outcome.detail}</span>
            </li>
          ))}
        </ul>
      )}
      {activity.summary && <p className="text-sm">{activity.summary}</p>}
      {activity.failure && <FailureMessage failure={activity.failure} />}
    </section>
  );
}
