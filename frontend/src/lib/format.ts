/**
 * Small display-formatting helpers shared by the scan pages.
 * All are pure and locale-aware so tests can assert on output.
 */

/** `0.9234` -> `92%` (whole percent, no decimals). */
export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

/** ISO timestamp -> short localized date + time. */
export function formatDate(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
