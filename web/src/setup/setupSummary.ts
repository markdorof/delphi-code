import type { StreamedWriteResult } from "@/api/streamedWrite";

export function setupSummary(setup: StreamedWriteResult<"/api/setup">): string {
  return setup.reused
    ? `The model at ${setup.model} was already installed and passed its checks.`
    : `Installed the model at ${setup.model} and checked it.`;
}
