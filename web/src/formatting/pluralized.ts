const IRREGULAR_PLURALS: Record<string, string> = { repository: "repositories" };

export function pluralized(count: number, noun: string): string {
  return `${count} ${count === 1 ? noun : (IRREGULAR_PLURALS[noun] ?? `${noun}s`)}`;
}
