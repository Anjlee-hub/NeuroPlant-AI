import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { formatPercent } from "@/lib/format";
import type { RiskLevel } from "@/types/recovery";
import type { ScanSeverity, ScanSyncStatus } from "@/types/scan";

/**
 * Single source of truth for scan status colors. Previously each scan page
 * re-declared the same variant functions, so the bands could drift between
 * the history grid, the detail page and future consumers.
 */

const CONFIDENCE_HIGH = 0.85;
const CONFIDENCE_MEDIUM = 0.6;

/** Confidence band -> badge color (mirrors the backend bands). */
export function confidenceVariant(
  confidence: number,
): "success" | "secondary" | "destructive" {
  if (confidence >= CONFIDENCE_HIGH) return "success";
  if (confidence >= CONFIDENCE_MEDIUM) return "secondary";
  return "destructive";
}

/** Severity level -> badge color. */
export function severityVariant(
  severity: ScanSeverity,
): "success" | "secondary" | "destructive" {
  if (severity === "low") return "success";
  if (severity === "moderate") return "secondary";
  return "destructive";
}

/** Scan sync status -> badge color. */
export function syncVariant(
  status: ScanSyncStatus,
): "success" | "outline" | "destructive" {
  if (status === "synced") return "success";
  if (status === "pending") return "outline";
  return "destructive";
}

/** Risk level (Crop Doctor overview) -> badge color. */
export function riskVariant(risk: RiskLevel): "success" | "secondary" | "destructive" {
  if (risk === "low") return "success";
  if (risk === "medium") return "secondary";
  return "destructive";
}

/** Percent badge colored by its confidence band. */
export function ConfidenceBadge({
  value,
  hint,
  className,
}: {
  value: number;
  /** Tooltip text describing what the badge measures. */
  hint?: string;
  className?: string;
}) {
  return (
    <Badge variant={confidenceVariant(value)} title={hint} className={className}>
      {formatPercent(value)}
    </Badge>
  );
}

/** Localized severity badge (low / moderate / severe). */
export function SeverityBadge({
  severity,
  className,
}: {
  severity: ScanSeverity;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <Badge variant={severityVariant(severity)} className={className}>
      {t(`scanHistory.severity.${severity}`)}
    </Badge>
  );
}

/** Localized sync status badge (synced / pending / failed). */
export function SyncBadge({
  status,
  className,
}: {
  status: ScanSyncStatus;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <Badge variant={syncVariant(status)} className={className}>
      {t(`scanHistory.sync.${status}`)}
    </Badge>
  );
}

/** Localized risk badge (low / medium / high) for the Crop Doctor overview. */
export function RiskBadge({
  risk,
  className,
}: {
  risk: RiskLevel;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <Badge variant={riskVariant(risk)} className={className}>
      {t(`doctor.riskLevel.${risk}`)}
    </Badge>
  );
}
