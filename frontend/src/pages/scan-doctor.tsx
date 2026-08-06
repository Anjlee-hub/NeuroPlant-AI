import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, Printer, ScanLine, Stethoscope } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { AiDiagnosis } from "@/components/doctor/ai-diagnosis";
import { PlantOverview } from "@/components/doctor/plant-overview";
import { RecoveryTrackerPanel } from "@/components/doctor/recovery-tracker";
import { SoilRecommendationsPanel } from "@/components/treatment/soil-recommendations";
import { RecommendationsPanel } from "@/components/treatment/recommendations";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { useAuth } from "@/stores/auth";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { RecoveryScan } from "@/types/recovery";

/** Page heading used both on screen and (print-only) at the top of the PDF. */
function SectionHeading({ children }: { children: string }) {
  return (
    <h2 className="mb-4 text-lg font-bold tracking-tight sm:text-xl">{children}</h2>
  );
}

function DoctorSkeleton() {
  const { t } = useTranslation();
  return (
    <div role="status" aria-label={t("doctor.title")} className="mt-6 flex flex-col gap-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-72 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

/** Print-only report header (title + generated date) — hidden on screen. */
function PrintReportHeader({ scan }: { scan: RecoveryScan }) {
  const { t, i18n } = useTranslation();
  return (
    <header className="mb-6 hidden border-b pb-4 print:block">
      <h1 className="text-2xl font-bold tracking-tight">
        {t("doctor.title")} — {scan.disease_name}
      </h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {t("doctor.generatedAt", {
          date: formatDate(new Date().toISOString(), i18n.language),
        })}
      </p>
    </header>
  );
}

/**
 * Crop Doctor Dashboard (M3, Task 4) — one page that turns a persisted scan
 * into an actionable care plan: Plant Overview, AI Diagnosis (explanation +
 * Grad-CAM + top-5), Treatment, Soil, and the Crop Recovery Tracker. It reuses
 * the existing recommendation/soil panels verbatim (no duplicated engine
 * logic) and composes the new recovery section around the tracker payload.
 * Printing this page (or "Save as PDF") produces the downloadable report.
 */
export function ScanDoctorPage() {
  const { t } = useTranslation();
  const { scanId } = useParams();
  const id = Number(scanId);
  const { user } = useAuth();

  const trackerQuery = useQuery({
    queryKey: ["scan-recovery", id],
    queryFn: () => api.getScanRecoveryTracker(id),
    enabled: !!user && Number.isInteger(id),
  });
  const explainQuery = useQuery({
    queryKey: ["scan-explain", id],
    queryFn: () => api.getScanExplain(id),
    enabled: !!user && Number.isInteger(id),
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={Stethoscope} title={t("scanDetail.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("scanDetail.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const invalidId = !Number.isInteger(id);
  const isError = invalidId || trackerQuery.isError || explainQuery.isError;
  const isLoading = !invalidId && (trackerQuery.isPending || explainQuery.isPending);
  const tracker = trackerQuery.data;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link
        to={`/scans/${id}`}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground print:hidden"
      >
        <ChevronLeft className="size-4" />
        {t("doctor.backToScan")}
      </Link>

      <header className="mt-4 flex flex-wrap items-start justify-between gap-3 print:hidden">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
            <Stethoscope className="size-7 text-brand-600 dark:text-brand-400" />
            {t("doctor.title")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("doctor.subtitle")}</p>
        </div>
        <Button onClick={() => window.print()}>
          <Printer />
          {t("doctor.printReport")}
        </Button>
      </header>

      {isLoading ? (
        <DoctorSkeleton />
      ) : isError ? (
        <StateCard
          className="mt-6"
          icon={ScanLine}
          title={t("scanDetail.errorTitle")}
          body={t("scanDetail.errorBody")}
          tone="destructive"
        >
          <Button
            variant="outline"
            onClick={() => {
              void trackerQuery.refetch();
              void explainQuery.refetch();
            }}
          >
            {t("common.retry")}
          </Button>
        </StateCard>
      ) : tracker ? (
        <div className="mt-6">
          <PrintReportHeader scan={tracker.scan} />

          <section aria-label={t("doctor.overview")}>
            <SectionHeading>{t("doctor.overview")}</SectionHeading>
            <PlantOverview scan={tracker.scan} risk={tracker.risk} />
          </section>

          <section className="mt-8" aria-label={t("doctor.diagnosis")}>
            <SectionHeading>{t("doctor.diagnosis")}</SectionHeading>
            <AiDiagnosis explain={explainQuery.data ?? null} />
          </section>

          <section className="mt-8 print:break-before-page" aria-label={t("doctor.treatment")}>
            <SectionHeading>{t("doctor.treatment")}</SectionHeading>
            <RecommendationsPanel scanId={id} />
          </section>

          <section className="mt-8" aria-label={t("doctor.soil")}>
            <SectionHeading>{t("doctor.soil")}</SectionHeading>
            <SoilRecommendationsPanel scanId={id} />
          </section>

          <section className="mt-8" aria-label={t("doctor.recovery")}>
            <SectionHeading>{t("doctor.recovery")}</SectionHeading>
            <RecoveryTrackerPanel scanId={id} />
          </section>
        </div>
      ) : null}
    </div>
  );
}
