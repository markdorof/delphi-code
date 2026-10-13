import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import { FailureMessage } from "@/components/FailureMessage";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { ListedProject } from "./listedProject";

export function ProjectDetailsSheet({ project, onClose }: { project: ListedProject | null; onClose: () => void }) {
  return (
    <Sheet open={project !== null} onOpenChange={(open) => open || onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        {project && <ProjectDetails project={project} />}
      </SheetContent>
    </Sheet>
  );
}

function ProjectDetails({ project }: { project: ListedProject }) {
  const { client } = useApiConnection();
  const state = useQuery({
    queryKey: ["projects", "status", project.key],
    queryFn: async () =>
      dataOrFailure(await client.GET("/api/projects/status", { params: { query: { project: project.key } } })),
  });
  return (
    <>
      <SheetHeader>
        <SheetTitle className="break-all font-mono text-base">{project.key}</SheetTitle>
        <SheetDescription>{project.source ?? project.project ?? "Stored index"}</SheetDescription>
      </SheetHeader>
      <div className="px-4 pb-4">
        {state.isPending && <p className="text-muted-foreground">Loading…</p>}
        {state.isError && <FailureMessage failure={state.error} />}
        {state.data && (
          <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
            <Detail label="Files">{state.data.files ?? "—"}</Detail>
            <Detail label="Chunks">{state.data.chunks ?? "—"}</Detail>
            <Detail label="Indexed at">{state.data.indexed_at ?? "Never"}</Detail>
            <Detail label="Paths">{state.data.paths?.join(", ") || "Everything"}</Detail>
            <Detail label="Languages">{state.data.languages?.join(", ") || "All"}</Detail>
            <Detail label="Ignored">{state.data.ignores?.join(", ") || "Nothing extra"}</Detail>
            <Detail label="Largest file">
              {state.data.max_bytes ? `${Math.round(state.data.max_bytes / 1024)} KiB` : "—"}
            </Detail>
            <Detail label="Model">{state.data.model ?? "—"}</Detail>
            <Detail label="Stored in">{state.data.index_directory}</Detail>
          </dl>
        )}
      </div>
    </>
  );
}

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="break-all">{children}</dd>
    </>
  );
}
