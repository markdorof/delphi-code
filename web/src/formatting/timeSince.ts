const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 3600],
  ["month", 30 * 24 * 3600],
  ["week", 7 * 24 * 3600],
  ["day", 24 * 3600],
  ["hour", 3600],
  ["minute", 60],
];

const RELATIVE = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

export function timeSince(isoTime: string, now: Date = new Date()): string {
  const seconds = (new Date(isoTime).getTime() - now.getTime()) / 1000;
  for (const [unit, unitSeconds] of UNITS) {
    if (Math.abs(seconds) >= unitSeconds) {
      return RELATIVE.format(Math.round(seconds / unitSeconds), unit);
    }
  }
  return "just now";
}
