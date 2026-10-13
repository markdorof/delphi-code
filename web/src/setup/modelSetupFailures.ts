const CODES_THAT_SETUP_FIXES = new Set(["model_missing", "model_invalid", "embedding_invalid"]);

export function setupFixes(failureCode: string): boolean {
  return CODES_THAT_SETUP_FIXES.has(failureCode);
}
