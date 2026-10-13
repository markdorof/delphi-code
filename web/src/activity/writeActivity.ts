import type { ApiFailure } from "@/api/apiFailure";
import type { ProgressEvent } from "@/api/progressEvents";
import { pluralized } from "@/formatting/pluralized";

export interface RepositoryOutcome {
  key: string;
  succeeded: boolean;
  detail: string;
}

export interface WriteActivity {
  title: string;
  state: "running" | "succeeded" | "failed";
  repository?: { key: string; position: number; count: number };
  stage?: string;
  embedded?: { done: number; total: number };
  listing?: string;
  outcomes: RepositoryOutcome[];
  summary?: string;
  failure?: ApiFailure;
}

export function startedActivity(title: string): WriteActivity {
  return { title, state: "running", outcomes: [] };
}

export function activityAfterProgress(activity: WriteActivity, event: ProgressEvent): WriteActivity {
  switch (event.event) {
    case "repository_started": {
      const { stage: _stage, embedded: _embedded, ...rest } = activity;
      return { ...rest, repository: { key: event.key, position: event.position, count: event.count } };
    }
    case "stage_started": {
      const { embedded: _embedded, ...rest } = activity;
      return { ...rest, stage: event.stage };
    }
    case "files_embedded":
      return { ...activity, embedded: { done: event.done, total: event.total } };
    case "repository_finished": {
      const result = event.result;
      const detail = "unchanged" in result && result.unchanged ? "Up to date" : indexedSize(result);
      return { ...activity, outcomes: [...activity.outcomes, { key: result.key, succeeded: true, detail }] };
    }
    case "repository_failed":
      return {
        ...activity,
        outcomes: [
          ...activity.outcomes,
          { key: activity.repository?.key ?? "", succeeded: false, detail: event.error.message },
        ],
      };
    case "owners_listing_started":
      return { ...activity, listing: `Listing ${event.owner_noun}s on ${event.host}` };
    case "repositories_listing_started":
      return { ...activity, listing: `Listing ${event.owner}'s repositories on ${event.host}` };
    case "listing_finished": {
      const { listing: _listing, ...rest } = activity;
      return rest;
    }
    case "model_setup_started":
      return { ...activity, stage: `Setting up the model in ${event.destination}` };
    case "model_setup_finished":
      return { ...activity, stage: event.reused ? "Reused the installed model" : "Model installed" };
    case "agents_connection_started":
      return { ...activity, stage: "Connecting agents" };
  }
}

export function succeededActivity(activity: WriteActivity, summary: string): WriteActivity {
  return { ...withoutCurrentStep(activity), state: "succeeded", summary };
}

export function failedActivity(activity: WriteActivity, failure: ApiFailure): WriteActivity {
  return { ...withoutCurrentStep(activity), state: "failed", failure };
}

function withoutCurrentStep(activity: WriteActivity): WriteActivity {
  const { stage: _stage, embedded: _embedded, listing: _listing, ...rest } = activity;
  return rest;
}

function indexedSize(result: object): string {
  if ("files" in result && "chunks" in result) {
    return `${pluralized(Number(result.files), "file")}, ${pluralized(Number(result.chunks), "chunk")}`;
  }
  return "Indexed";
}
