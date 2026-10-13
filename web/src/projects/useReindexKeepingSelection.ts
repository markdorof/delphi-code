import { useWriteActivity } from "@/activity/WriteActivityProvider";
import { useApiConnection } from "@/api/apiContext";
import type { ListedProject } from "./listedProject";
import { indexSummary } from "./writeSummaries";

export function useReindexKeepingSelection() {
  const { client } = useApiConnection();
  const { startWrite } = useWriteActivity();
  return async (project: ListedProject) => {
    const stored = (await client.GET("/api/projects/status", { params: { query: { project: project.key } } })).data;
    await startWrite({
      title: `Re-indexing ${project.key}`,
      path: "/api/projects/index",
      body: {
        project: project.key,
        path: stored?.paths ?? [],
        language: stored?.languages ?? [],
        ignore: stored?.ignores ?? [],
        ...(stored?.max_bytes ? { max_bytes: stored.max_bytes } : {}),
      },
      summary: indexSummary,
    });
  };
}
