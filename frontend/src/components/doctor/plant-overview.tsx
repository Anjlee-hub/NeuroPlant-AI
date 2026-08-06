import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ConfidenceBadge,
  RiskBadge,
  SeverityBadge,
} from "@/components/ui/status-badges";
import { formatDate } from "@/lib/format";
import type { RecoveryScan, RiskLevel } from "@/types/recovery";

/** Label/value pair inside the overview definition list. */
function OverviewRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-right text-sm font-medium">{children}</dd>
    </div>
  );
}

/**
 * Plant Overview — the dashboard's summary card: crop, plant part, disease,
 * confidence, severity, computed risk level, scan date and AI model provenance.
 * Data comes from the recovery tracker's compact scan summary (one call), so
 * the overview never needs a separate catalog request.
 */
export function PlantOverview({
  scan,
  risk,
}: {
  scan: RecoveryScan;
  risk: RiskLevel;
}) {
  const { t, i18n } = useTranslation();
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("doctor.overview")}</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="divide-y divide-border">
          <OverviewRow label={t("doctor.crop")}>
            {scan.crop_name ?? t("scanDetail.notSet")}
          </OverviewRow>
          <OverviewRow label={t("doctor.part")}>
            {scan.part_type ? t(`scanCrop.parts.${scan.part_type}`) : t("scanDetail.notSet")}
          </OverviewRow>
          <OverviewRow label={t("doctor.disease")}>{scan.disease_name}</OverviewRow>
          <OverviewRow label={t("doctor.confidence")}>
            <ConfidenceBadge value={scan.confidence} hint={t("doctor.confidence")} />
          </OverviewRow>
          <OverviewRow label={t("doctor.severity")}>
            {scan.severity ? <SeverityBadge severity={scan.severity} /> : t("scanDetail.notSet")}
          </OverviewRow>
          <OverviewRow label={t("doctor.risk")}>
            <RiskBadge risk={risk} />
          </OverviewRow>
          <OverviewRow label={t("doctor.scanDate")}>
            {formatDate(scan.created_at, i18n.language)}
          </OverviewRow>
          <OverviewRow label={t("doctor.model")}>
            {scan.model_version ?? t("scanDetail.notSet")}
          </OverviewRow>
          <OverviewRow label={t("doctor.provider")}>{scan.provider}</OverviewRow>
        </dl>
      </CardContent>
    </Card>
  );
}
