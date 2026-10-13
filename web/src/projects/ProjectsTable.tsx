import { InfoIcon, RefreshCwIcon, Trash2Icon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { timeSince } from "@/formatting/timeSince";
import { isLocalProject, type ListedProject } from "./listedProject";

export function ProjectsTable({
  projects,
  writeRunning,
  onShowDetails,
  onReindex,
  onRemove,
}: {
  projects: ListedProject[];
  writeRunning: boolean;
  onShowDetails: (project: ListedProject) => void;
  onReindex: (project: ListedProject) => void;
  onRemove: (project: ListedProject) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Project</TableHead>
            <TableHead className="hidden sm:table-cell">Index</TableHead>
            <TableHead className="text-right">
              <span className="sr-only">Actions</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {projects.map((project) => (
            <TableRow key={project.key}>
              <TableCell className="w-full max-w-0 whitespace-normal">
                <p className="break-all font-mono text-sm sm:truncate">{project.key}</p>
                <p className="truncate text-muted-foreground text-xs">
                  {project.tracked ? "Tracked" : "Index only"}
                  {project.ref && ` · ${project.ref}`}
                  {project.commit && ` · ${project.commit.slice(0, 7)}`}
                  <span className="sm:hidden"> · {indexState(project)}</span>
                </p>
              </TableCell>
              <TableCell className="hidden whitespace-nowrap sm:table-cell">
                {project.ready ? (
                  <span className="text-sm" title={project.indexed_at ?? undefined}>
                    {project.indexed_at ? timeSince(project.indexed_at) : "Indexed"}
                  </span>
                ) : (
                  <Badge variant="outline">Not indexed</Badge>
                )}
              </TableCell>
              <TableCell className="whitespace-nowrap text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Details of ${project.key}`}
                  disabled={!project.index_directory}
                  onClick={() => onShowDetails(project)}
                >
                  <InfoIcon />
                </Button>
                {isLocalProject(project) && (
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Re-index ${project.key}`}
                    disabled={writeRunning}
                    onClick={() => onReindex(project)}
                  >
                    <RefreshCwIcon />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove ${project.key}`}
                  disabled={writeRunning}
                  onClick={() => onRemove(project)}
                >
                  <Trash2Icon />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function indexState(project: ListedProject): string {
  if (!project.ready) {
    return "Not indexed";
  }
  return project.indexed_at ? `indexed ${timeSince(project.indexed_at)}` : "Indexed";
}
