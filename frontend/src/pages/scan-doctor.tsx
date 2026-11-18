
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  Download,
  Leaf,
  Printer,
  ScanLine,
  ShieldCheck,
  Sprout,
  Stethoscope,
} from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { AiDiagnosis } from "@/components/doctor/ai-diagnosis";
import { PlantOverview } from "@/components/doctor/plant-overview";
import { RecoveryTrackerPanel } from "@/components/doctor/recovery-tracker";
import { RecommendationsPanel } from "@/components/treatment/recommendations";
import { SoilRecommendationsPanel } from "@/components/treatment/soil-recommendations";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import type { RecoveryScan } from "@/types/recovery";

function SectionHeading({
  children,
  number,
}: {
  children: string;
  number: string;
}) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-sm font-bold text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
        {number}
      </span>

      <h2 className="text-lg font-bold tracking-tight sm:text-xl">
        {children}
      </h2>
    </div>
  );
}

function DoctorSkeleton() {
  const { t } = useTranslation();

  return (
    <div
      role="status"
      aria-label={t("doctor.title")}
      className="mt-6 flex flex-col gap-6"
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-72 w-full rounded-2xl" />
        <Skeleton className="h-96 w-full rounded-2xl" />
      </div>

      <Skeleton className="h-48 w-full rounded-2xl" />
      <Skeleton className="h-48 w-full rounded-2xl" />
      <Skeleton className="h-64 w-full rounded-2xl" />
    </div>
  );
}

function PrintReportHeader({ scan }: { scan: RecoveryScan }) {
  const { t, i18n } = useTranslation();

  return (
    <header className="mb-7 hidden border-b pb-5 print:block">
      <div className="flex items-center gap-2 text-sm font-semibold text-emerald-700">
        <Leaf className="size-5" />
        NeuroPlant AI
      </div>

      <h1 className="mt-3 text-2xl font-bold tracking-tight">
        {t("doctor.title")} — {scan.disease_name}
      </h1>

      <p className="mt-2 text-sm text-muted-foreground">
        {t("doctor.generatedAt", {
          date: formatDate(new Date().toISOString(), i18n.language),
        })}
      </p>
    </header>
  );
}

function ReportSection({
  children,
  label,
  number,
  className = "",
}: {
  children: ReactNode;
  label: string;
  number: string;
  className?: string;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      aria-label={label}
      className={`mt-8 ${className}`}
    >
      <SectionHeading number={number}>
        {label}
      </SectionHeading>

      {children}
    </motion.section>
  );
}

export function ScanDoctorPage() {
  const { t, i18n } = useTranslation();
  const { scanId } = useParams();
  const id = Number(scanId);
  const { user } = useAuth();

  const trackerQuery = useQuery({
    queryKey: ["scan-recovery", id],
    queryFn: () => api.getScanRecoveryTracker(id),
    enabled: !!user && Number.isInteger(id) && id > 0,
  });

  const explainQuery = useQuery({
    queryKey: ["scan-explain", id],
    queryFn: () => api.getScanExplain(id),
    enabled: !!user && Number.isInteger(id) && id > 0,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard
          icon={Stethoscope}
          title={t("scanDetail.authRequired")}
        >
          <Button asChild>
            <Link to="/login">
              {t("scanDetail.signIn")}
            </Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const invalidId = !Number.isInteger(id) || id <= 0;

  const isError =
    invalidId ||
    trackerQuery.isError ||
    explainQuery.isError;

  const isLoading =
    !invalidId &&
    (trackerQuery.isPending || explainQuery.isPending);

  const tracker = trackerQuery.data;

  const retry = () => {
    void trackerQuery.refetch();
    void explainQuery.refetch();
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50/60 via-background to-background dark:from-emerald-950/15">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-9">

        {/* Navigation */}
        <Link
          to={`/scans/${id}`}
          className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-emerald-700 dark:hover:text-emerald-300 print:hidden"
        >
          <ArrowLeft className="size-4" />
          {t("doctor.backToScan")}
        </Link>

        {/* Page heading */}
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-7 flex flex-col justify-between gap-5 rounded-3xl border border-emerald-100 bg-gradient-to-br from-white via-emerald-50/80 to-green-100/70 p-5 shadow-sm dark:border-emerald-900/50 dark:from-card dark:via-emerald-950/30 dark:to-green-950/30 sm:flex-row sm:items-center sm:p-7 print:hidden"
        >
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/70 px-3 py-1 text-xs font-semibold text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-300">
              <ShieldCheck className="size-3.5" />
              NeuroPlant AI · Crop Health Report
            </div>

            <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
              <Stethoscope className="size-7 shrink-0 text-emerald-700 dark:text-emerald-300" />
              {t("doctor.title")}
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              {t("doctor.subtitle")}
            </p>
          </div>

          <Button
            onClick={() => window.print()}
            className="h-11 shrink-0 gap-2 rounded-xl bg-emerald-700 text-white hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-700"
          >
            <Printer className="size-4" />
            {t("doctor.printReport")}
          </Button>
        </motion.header>

        {/* Loading and error states */}
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
            <Button variant="outline" onClick={retry}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : tracker ? (
          <>
            <PrintReportHeader scan={tracker.scan} />

            {/* Report overview */}
            <div className="mb-7 grid gap-3 sm:grid-cols-2">
              <Card className="overflow-hidden rounded-2xl border-emerald-100 dark:border-emerald-900/50">
                <CardContent className="flex items-center gap-4 p-4 sm:p-5">
                  <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
                    <Sprout className="size-5" />
                  </div>

                  <div className="min-w-0">
                    <p className="text-xs font-medium text-muted-foreground">
                      {t("doctor.overview")}
                    </p>

                    <p className="mt-1 truncate text-sm font-bold">
                      {tracker.scan.disease_name}
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="overflow-hidden rounded-2xl border-sky-100 dark:border-sky-900/50">
                <CardContent className="flex items-center gap-4 p-4 sm:p-5">
                  <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-300">
                    <CalendarDays className="size-5" />
                  </div>

                  <div className="min-w-0">
                    <p className="text-xs font-medium text-muted-foreground">
                      {t("doctor.generatedAt", {
                        date: formatDate(
                          tracker.scan.created_at,
                          i18n.language,
                        ),
                      })}
                    </p>

                    <p className="mt-1 text-sm font-bold">
                      #{tracker.scan.id}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Plant overview */}
            <ReportSection
              label={t("doctor.overview")}
              number="01"
            >
              <PlantOverview
                scan={tracker.scan}
                risk={tracker.risk}
              />
            </ReportSection>

            {/* AI diagnosis */}
            <ReportSection
              label={t("doctor.diagnosis")}
              number="02"
            >
              <AiDiagnosis
                explain={explainQuery.data ?? null}
              />
            </ReportSection>

            {/* Treatment recommendations */}
            <ReportSection
              label={t("doctor.treatment")}
              number="03"
              className="print:break-before-page"
            >
              <RecommendationsPanel scanId={id} />
            </ReportSection>

            {/* Soil recommendations */}
            <ReportSection
              label={t("doctor.soil")}
              number="04"
            >
              <SoilRecommendationsPanel scanId={id} />
            </ReportSection>

            {/* Recovery tracker */}
            <ReportSection
              label={t("doctor.recovery")}
              number="05"
            >
              <RecoveryTrackerPanel scanId={id} />
            </ReportSection>

            {/* Report footer */}
            <div className="mt-9 flex flex-col justify-between gap-4 border-t pt-6 sm:flex-row sm:items-center print:mt-8">
              <div className="flex items-start gap-3">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
                  <CheckCircle2 className="size-5" />
                </div>

                <div>
                  <p className="text-sm font-semibold">
                    NeuroPlant AI
                  </p>

                  <p className="mt-1 text-xs text-muted-foreground">
                    {t("doctor.subtitle")}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 print:hidden">
                <Button variant="outline" asChild>
                  <Link to={`/scans/${id}`}>
                    <ArrowLeft className="mr-2 size-4" />
                    {t("doctor.backToScan")}
                  </Link>
                </Button>

                <Button
                  onClick={() => window.print()}
                  className="gap-2"
                >
                  <Download className="size-4" />
                  {t("doctor.printReport")}
                </Button>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
