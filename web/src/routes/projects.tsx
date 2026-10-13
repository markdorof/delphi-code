import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { CloudDownloadIcon, PlusIcon, RefreshCwIcon } from "lucide-react";
import { useState } from "react";
import { useWriteActivity } from "@/activity/WriteActivityProvider";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import { FailureMessage } from "@/components/FailureMessage";
import { Button } from "@/components/ui/button";
import { AddProjectsDialog } from "@/projects/AddProjectsDialog";
import type { ListedProject } from "@/projects/listedProject";
import { ProjectDetailsSheet } from "@/projects/ProjectDetailsSheet";
import { ProjectsTable } from "@/projects/ProjectsTable";
import { type ProjectRemoval, RemoveProjectDialog } from "@/projects/RemoveProjectDialog";
import { useReindexKeepingSelection } from "@/projects/useReindexKeepingSelection";
import { syncSummary } from "@/projects/writeSummaries";

export const Route = createFileRoute("/projects")({
  component: ProjectsPage,
});

export function ProjectsPage() {
  const { client } = useApiConnection();
  const { startWrite, writeRunning } = useWriteActivity();
  const reindex = useReindexKeepingSelection();
  const [adding, setAdding] = useState(false);
  const [detailed, setDetailed] = useState<ListedProject | null>(null);
  const [removing, setRemoving] = useState<ListedProject | null>(null);
  const [lastRemoval, setLastRemoval] = useState<ProjectRemoval | null>(null);
  const projects = useQuery({
    queryKey: ["projects"],
    queryFn: async () => dataOrFailure(await client.GET("/api/projects")),
  });

  function syncAll() {
    void startWrite({
      title: "Syncing tracked projects",
      path: "/api/projects/sync",
      body: undefined,
      summary: syncSummary,
    });
  }

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-4">
      <header className="flex flex-wrap items-center gap-2">
        <h1 className="flex-1 font-semibold text-lg">Projects</h1>
        <Button variant="outline" onClick={syncAll} disabled={writeRunning}>
          <RefreshCwIcon />
          Sync all
        </Button>
        <Button asChild variant="outline">
          <Link to="/projects/from-account">
            <CloudDownloadIcon />
            From your account
          </Link>
        </Button>
        <Button onClick={() => setAdding(true)} disabled={writeRunning}>
          <PlusIcon />
          Add projects
        </Button>
      </header>
      {lastRemoval && (
        <p role="status" className="text-muted-foreground text-sm">
          Removed {lastRemoval.key}
          {lastRemoval.deleted_index ? " and deleted its index." : "; its index was kept."}
        </p>
      )}
      {projects.isPending && <p className="text-muted-foreground">Loading projects…</p>}
      {projects.isError && <FailureMessage failure={projects.error} />}
      {projects.data?.repos.length === 0 && (
        <p className="text-muted-foreground">No projects yet. Add a folder or repository to search it.</p>
      )}
      {projects.data && projects.data.repos.length > 0 && (
        <ProjectsTable
          projects={projects.data.repos}
          writeRunning={writeRunning}
          onShowDetails={setDetailed}
          onReindex={(project) => void reindex(project)}
          onRemove={(project) => {
            setLastRemoval(null);
            setRemoving(project);
          }}
        />
      )}
      <AddProjectsDialog open={adding} onOpenChange={setAdding} />
      <ProjectDetailsSheet project={detailed} onClose={() => setDetailed(null)} />
      <RemoveProjectDialog
        project={removing}
        onClose={() => setRemoving(null)}
        onRemoved={(removal) => {
          setRemoving(null);
          setLastRemoval(removal);
        }}
      />
    </div>
  );
}
