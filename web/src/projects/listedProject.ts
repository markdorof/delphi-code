import type { components } from "@/api/schema";

export type ListedProject = components["schemas"]["ListedProjectResponse"];

export function isLocalProject(project: ListedProject): project is ListedProject & { project: string } {
  return project.project !== null;
}
