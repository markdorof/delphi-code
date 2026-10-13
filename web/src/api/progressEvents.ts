import type { components } from "./schema";

type Schemas = components["schemas"];

export type ProgressEvent =
  | { event: "owners_listing_started"; host: string; owner_noun: string }
  | { event: "repositories_listing_started"; host: string; owner: string }
  | { event: "listing_finished" }
  | { event: "repository_started"; key: string; position: number; count: number }
  | { event: "model_setup_started"; destination: string }
  | { event: "stage_started"; stage: string }
  | { event: "files_embedded"; done: number; total: number }
  | { event: "repository_finished"; result: Schemas["IndexingOutcomeResponse"] | Schemas["ProjectUpToDateResponse"] }
  | { event: "repository_failed"; error: { code: string; message: string } }
  | { event: "model_setup_finished"; reused: boolean }
  | { event: "agents_connection_started" };
