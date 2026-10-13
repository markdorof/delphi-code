export function commaSeparatedValues(text: string | undefined): string[] {
  return (text ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}
