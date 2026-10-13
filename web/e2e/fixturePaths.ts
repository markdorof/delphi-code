import { tmpdir } from "node:os";
import { join } from "node:path";

export const ADDABLE_PROJECT = join(tmpdir(), "delphi-code-e2e-addable-project");
