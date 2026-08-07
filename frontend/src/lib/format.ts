/**
 * Small display-formatting helpers shared by the scan pages.
 * All are pure and locale-aware so tests can assert on output.
 */

/** `0.9234` -> `92%` (whole percent, no decimals). */
export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

/** Milliseconds -> `32ms` or `1.2s` (keeps sub-second pipeline times readable). */
export function formatMs(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`;
  return `${Math.round(value)}ms`;
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

/** "2026-07-15" (date-only, no timezone) -> localized date without a time.
 * Parsed as local midnight so the day never shifts across timezones — the
 * calendar and marketplace dates are stored this way. */
export function formatDateOnly(dateStr: string, locale: string): string {
  const date = new Date(`${dateStr}T00:00:00`);
  if (Number.isNaN(date.getTime())) return dateStr;
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(date);
}
