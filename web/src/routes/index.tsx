import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { dataOrFailure } from "@/api/apiClient";
import { useApiConnection } from "@/api/apiContext";
import { FailureMessage } from "@/components/FailureMessage";

export const Route = createFileRoute("/")({
  component: ProjectsOverview,
});

export function ProjectsOverview() {
  const { client } = useApiConnection();
  const projects = useQuery({
    queryKey: ["projects"],
    queryFn: async () => dataOrFailure(await client.GET("/api/projects")),
  });

  if (projects.isPending) {
    return <p className="text-muted-foreground">Loading projects…</p>;
  }
  if (projects.isError) {
    return <FailureMessage failure={projects.error} />;
  }
  if (projects.data.repos.length === 0) {
    return <p className="text-muted-foreground">No projects yet. Index or add one with the delphi-code command.</p>;
  }
  return (
    <ul className="divide-y rounded-lg border">
      {projects.data.repos.map((project) => (
        <li key={project.key} className="flex items-center justify-between gap-4 px-4 py-3">
          <span className="truncate font-mono text-sm">{project.key}</span>
          <span className="shrink-0 text-muted-foreground text-sm">{project.ready ? "Indexed" : "Not indexed"}</span>
        </li>
      ))}
    </ul>
  );
}
