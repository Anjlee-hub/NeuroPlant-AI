
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  Copy,
  Download,
  History,
  ImageOff,
  Leaf,
  Maximize2,
  ScanLine,
  Share2,
  ShieldCheck,
  Stethoscope,
  Wand2,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "@/stores/auth";
import { api } from "@/lib/api";
import { formatDate, formatMs, formatPercent } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ConfidenceBadge,
  SeverityBadge,
  SyncBadge,
  confidenceVariant,
} from "@/components/ui/status-badges";
import { StateCard } from "@/components/ui/state-card";
import { RecommendationsPanel } from "@/components/treatment/recommendations";
import { SoilRecommendationsPanel } from "@/components/treatment/soil-recommendations";

function DetailRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border/60 py-3 last:border-0">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-right text-sm font-semibold">{children}</dd>
    </div>
  );
}

function DetailSkeleton({ t }: { t: (key: string) => string }) {
  return (
    <div
      className="mt-6 grid gap-6 lg:grid-cols-2"
      role="status"
      aria-label={t("scanDetail.loading")}
    >
      <div className="flex flex-col gap-4">
        <Skeleton className="aspect-[4/3] w-full rounded-2xl" />
        <Skeleton className="h-52 w-full rounded-2xl" />
      </div>
      <div className="flex flex-col gap-4">
        <Skeleton className="h-72 w-full rounded-2xl" />
        <Skeleton className="h-48 w-full rounded-2xl" />
      </div>
    </div>
  );
}

function ScanImage({ url, alt }: { url: string | null; alt: string }) {
  const { t } = useTranslation();
  const [failed, setFailed] = useState(false);
  const [zoomUrl, setZoomUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!zoomUrl) return;

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setZoomUrl(null);
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoomUrl]);

  if (!url || failed) {
    return (
      <div className="flex aspect-[4/3] w-full flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-muted/40 text-center text-muted-foreground">
        <ImageOff className="size-10" />
        <span className="text-sm">{alt}</span>
      </div>
    );
  }

  return (
    <>
      <div className="group relative overflow-hidden rounded-xl border bg-muted">
        <img
          src={url}
          alt={alt}
          className="aspect-[4/3] w-full object-cover transition-transform duration-500 group-hover:scale-[1.02]"
          onError={() => setFailed(true)}
        />
        <Button
          variant="outline"
          size="icon"
          className="absolute right-3 top-3 bg-background/90 shadow-sm"
          aria-label={t("scanDetail.zoomImage")}
          onClick={() => setZoomUrl(url)}
        >
          <Maximize2 className="size-4" />
        </Button>
      </div>

      {zoomUrl && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={t("scanDetail.zoomImage")}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
          onClick={() => setZoomUrl(null)}
        >
          <img
            src={zoomUrl}
            alt={alt}
            className="max-h-full max-w-full rounded-xl object-contain"
            onClick={(event) => event.stopPropagation()}
          />
          <Button
            variant="outline"
            size="icon"
            className="absolute right-4 top-4 bg-background/90"
            aria-label={t("scanDetail.close")}
            onClick={() => setZoomUrl(null)}
          >
            <X className="size-4" />
          </Button>
        </div>
      )}
    </>
  );
}

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <Card className="overflow-hidden rounded-2xl border-border/70 shadow-sm">
      <CardHeader className="border-b border-border/60 bg-muted/20 px-5 py-4">
        <CardTitle className="text-base font-bold">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-5">{children}</CardContent>
    </Card>
  );
}

export function ScanDetailPage() {
  const { t, i18n } = useTranslation();
  const { scanId } = useParams();
  const id = Number(scanId);
  const { user } = useAuth();

  const [copied, setCopied] = useState(false);
  const [shareNote, setShareNote] = useState(false);

  const scanQuery = useQuery({
    queryKey: ["scan", id],
    queryFn: () => api.getScan(id),
    enabled: !!user && Number.isInteger(id),
  });

  const explainQuery = useQuery({
    queryKey: ["scan-explain", id],
    queryFn: () => api.getScanExplain(id),
    enabled: !!user && Number.isInteger(id),
  });

  const cropsQuery = useQuery({
    queryKey: ["crops"],
    queryFn: () => api.listCrops(),
    enabled: !!user,
    staleTime: 5 * 60_000,
  });

  const scan = scanQuery.data;

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={History} title={t("scanDetail.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("scanDetail.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const invalidId = !Number.isInteger(id) || id <= 0;
  const isError = invalidId || scanQuery.isError || explainQuery.isError;
  const explain = explainQuery.data;

  const cropName =
    scan?.crop_id != null
      ? (cropsQuery.data?.find((crop) => crop.id === scan.crop_id)?.name ??
        String(scan.crop_id))
      : t("scanDetail.notSet");

  const copyPrediction = async () => {
    if (!scan) return;

    const text =
      `Disease: ${scan.disease_name}\n` +
      `Confidence: ${scan.confidence === null
        ? t("scanHistory.needsReview")
        : formatPercent(scan.confidence)}\n` +
      `AI provider: ${scan.provider} (${scan.model_version ?? t("scanDetail.notSet")})`;

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard unavailable in this browser context.
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50/60 via-background to-background dark:from-emerald-950/15">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-9">
        <Link
          to="/scans"
          className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-emerald-700 dark:hover:text-emerald-300 print:hidden"
        >
          <ChevronLeft className="size-4" />
          {t("scanDetail.back")}
        </Link>

        {scanQuery.isPending || explainQuery.isPending ? (
          <DetailSkeleton t={t} />
        ) : isError ? (
          <StateCard
            className="mt-4"
            icon={ScanLine}
            title={t("scanDetail.errorTitle")}
            body={t("scanDetail.errorBody")}
            tone="destructive"
          >
            <Button
              variant="outline"
              onClick={() => {
                void scanQuery.refetch();
                void explainQuery.refetch();
              }}
            >
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : !scan ? null : (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            {/* Diagnosis header */}
            <header className="mb-7 overflow-hidden rounded-3xl border border-emerald-100 bg-gradient-to-br from-white via-emerald-50/80 to-green-100/70 p-5 shadow-sm dark:border-emerald-900/50 dark:from-card dark:via-emerald-950/30 dark:to-green-950/30 sm:p-7">
              <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
                <div className="min-w-0">
                  <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/70 px-3 py-1 text-xs font-semibold text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-300">
                    <Leaf className="size-3.5" />
                    NeuroPlant AI · {t("scanDetail.detailsTitle")}
                  </div>

                  <h1 className="max-w-3xl text-2xl font-bold tracking-tight sm:text-3xl">
                    {scan.disease_name}
                  </h1>

                  <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
                    <span>{formatDate(scan.created_at, i18n.language)}</span>
                    <span>·</span>
                    <span>#{scan.id}</span>
                  </p>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {scan.severity && (
                      <SeverityBadge severity={scan.severity} />
                    )}
                    <SyncBadge status={scan.sync_status} />
                  </div>
                </div>

                <div className="flex shrink-0 flex-col items-start gap-2 rounded-2xl border border-emerald-100 bg-white/80 p-4 dark:border-emerald-900/60 dark:bg-background/50 sm:items-center">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {t("scanDetail.confidence")}
                  </span>
                  <ConfidenceBadge
                    value={scan.confidence}
                    hint={t("scanDetail.confidence")}
                  />
                </div>
              </div>
            </header>

            {/* Main content */}
            <div className="grid items-start gap-6 lg:grid-cols-[1.05fr_0.95fr]">
              <section className="flex min-w-0 flex-col gap-5">
                <SectionCard title={t("scanDetail.uploadedImage")}>
                  <ScanImage
                    key={scan.id}
                    url={scan.media_items[0]?.url ?? null}
                    alt={scan.disease_name}
                  />
                </SectionCard>

                <SectionCard title={t("scanDetail.heatmapTitle")}>
                  <div className="flex flex-col gap-4">
                    {explain?.heatmap && explain.overlay_url ? (
                      <>
                        <div>
                          <p className="mb-2 text-xs font-semibold text-muted-foreground">
                            {t("scanDetail.overlayTitle")}
                          </p>
                          <img
                            src={explain.overlay_url}
                            alt={t("scanDetail.overlayTitle")}
                            className="w-full rounded-xl border"
                            onError={(event) => {
                              event.currentTarget.style.display = "none";
                            }}
                          />
                        </div>

                        {explain.heatmap_url && (
                          <div>
                            <p className="mb-2 text-xs font-semibold text-muted-foreground">
                              {t("scanDetail.heatmapTitle")}
                            </p>
                            <img
                              src={explain.heatmap_url}
                              alt={t("scanDetail.heatmapTitle")}
                              className="w-full rounded-xl border"
                              onError={(event) => {
                                event.currentTarget.style.display = "none";
                              }}
                            />
                          </div>
                        )}

                        <p className="text-xs leading-relaxed text-muted-foreground">
                          {t("scanDetail.heatmapCaption", {
                            provider: explain.heatmap.provider,
                            time: formatMs(explain.heatmap.time_ms),
                          })}
                        </p>

                        <a
                          href={explain.overlay_url}
                          download={`scan-${id}-heatmap.png`}
                          className="inline-flex items-center justify-center gap-2 rounded-xl border border-input bg-background px-4 py-2.5 text-sm font-semibold transition-colors hover:bg-accent print:hidden"
                        >
                          <Download className="size-4" />
                          {t("scanDetail.downloadHeatmap")}
                        </a>
                      </>
                    ) : (
                      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed bg-muted/30 px-5 py-9 text-center">
                        <div className="flex size-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
                          <Wand2 className="size-6" />
                        </div>
                        <p className="font-semibold">
                          {t("scanDetail.noHeatmapTitle")}
                        </p>
                        <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
                          {t("scanDetail.noHeatmapBody")}
                        </p>
                      </div>
                    )}
                  </div>
                </SectionCard>
              </section>

              <section className="flex min-w-0 flex-col gap-5">
                <SectionCard title={t("scanDetail.detailsTitle")}>
                  <dl className="divide-y divide-border/60">
                    <DetailRow label={t("scanDetail.crop")}>
                      {cropName}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.part")}>
                      {scan.part_type
                        ? t(`scanHistory.partType.${scan.part_type}`)
                        : t("scanDetail.notSet")}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.disease")}>
                      {scan.disease_name}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.severity")}>
                      {scan.severity ? (
                        <SeverityBadge severity={scan.severity} />
                      ) : (
                        t("scanDetail.notSet")
                      )}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.confidence")}>
                      {scan.confidence === null
                        ? t("scanHistory.needsReview")
                        : formatPercent(scan.confidence)}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.confidenceLevel")}>
                      {explain ? (
                        <Badge
                          variant={confidenceVariant(explain.confidence.top)}
                        >
                          {t(`scanDetail.levels.${explain.confidence.level}`)}
                        </Badge>
                      ) : (
                        t("scanDetail.notSet")
                      )}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.timestamp")}>
                      {formatDate(scan.created_at, i18n.language)}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.processing")}>
                      {formatMs(scan.processing_time_ms)}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.inferenceMs")}>
                      {explain
                        ? formatMs(explain.timing.inference_time_ms)
                        : t("scanDetail.notSet")}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.provider")}>
                      {scan.provider}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.model")}>
                      {scan.model_version ?? t("scanDetail.notSet")}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.dataset")}>
                      {scan.dataset_version ?? t("scanDetail.notSet")}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.sync")}>
                      <SyncBadge status={scan.sync_status} />
                    </DetailRow>
                  </dl>

                  <div className="mt-5 flex flex-wrap gap-2 border-t pt-5 print:hidden">
                    <Button
                      asChild
                      className="flex-1 gap-2 bg-emerald-700 text-white hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-700"
                    >
                      <Link to={`/scans/${id}/doctor`}>
                        <Stethoscope className="size-4" />
                        {t("doctor.title")}
                      </Link>
                    </Button>

                    <Button
                      variant="outline"
                      className="gap-2"
                      onClick={() => void copyPrediction()}
                    >
                      {copied ? (
                        <Check className="size-4" />
                      ) : (
                        <Copy className="size-4" />
                      )}
                      {copied
                        ? t("scanDetail.copied")
                        : t("scanDetail.copy")}
                    </Button>

                    <Button
                      variant="outline"
                      className="gap-2"
                      onClick={() => setShareNote(true)}
                    >
                      <Share2 className="size-4" />
                      {t("scanDetail.share")}
                    </Button>
                  </div>

                  {shareNote && (
                    <p className="mt-3 rounded-lg bg-muted/60 p-3 text-xs text-muted-foreground">
                      {t("scanDetail.shareComingSoon")}
                    </p>
                  )}
                </SectionCard>

                {explain && (
                  <>
                    <SectionCard title={t("scanDetail.adviceTitle")}>
                      <div
                        className={
                          explain.confidence.level === "low" ||
                          explain.confidence.level === "unavailable"
                            ? "flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
                            : "flex items-start gap-3 rounded-xl bg-muted/50 p-4 text-sm"
                        }
                      >
                        {explain.confidence.level === "low" ||
                        explain.confidence.level === "unavailable" ? (
                          <AlertTriangle className="mt-0.5 size-5 shrink-0 text-amber-600 dark:text-amber-300" />
                        ) : (
                          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-emerald-600" />
                        )}
                        <div>
                          {(explain.confidence.level === "low" ||
                            explain.confidence.level === "unavailable") && (
                            <p className="mb-1 font-bold">
                              {t("scanDetail.lowConfidenceTitle")}
                            </p>
                          )}
                          <p className="leading-relaxed">
                            {explain.confidence.advice}
                          </p>
                        </div>
                      </div>
                    </SectionCard>

                    <SectionCard title={t("scanDetail.topPredictions")}>
                      {explain.top5.length > 0 ? (
                        <ol className="flex flex-col gap-4">
                          {explain.top5.slice(0, 5).map((ranking, index) => (
                            <li
                              key={`${ranking.disease_name}-${index}`}
                              className="space-y-2"
                            >
                              <div className="flex items-center justify-between gap-3 text-sm">
                                <span className="flex min-w-0 items-center gap-3">
                                  <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-xs font-bold text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
                                    {index + 1}
                                  </span>
                                  <span className="truncate font-semibold">
                                    {ranking.disease_name}
                                  </span>
                                </span>
                                <span className="shrink-0 font-bold tabular-nums">
                                  {ranking.confidence === null
                                    ? t("scanHistory.needsReview")
                                    : formatPercent(ranking.confidence)}
                                </span>
                              </div>

                              {ranking.confidence !== null && (
                                <div
                                  className="h-2 overflow-hidden rounded-full bg-muted"
                                  role="progressbar"
                                  aria-valuenow={Math.round(
                                    ranking.confidence * 100,
                                  )}
                                  aria-valuemin={0}
                                  aria-valuemax={100}
                                >
                                  <div
                                    className="h-full rounded-full bg-emerald-600 transition-all duration-700 dark:bg-emerald-400"
                                    style={{
                                      width: `${Math.max(0, Math.min(100, ranking.confidence * 100))}%`,
                                    }}
                                  />
                                </div>
                              )}
                            </li>
                          ))}
                        </ol>
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          {t("scanDetail.noTop5")}
                        </p>
                      )}
                    </SectionCard>

                    <SectionCard title={t("scanDetail.explanation")}>
                      <p className="text-sm leading-7 text-muted-foreground">
                        {explain.explanation}
                      </p>
                    </SectionCard>
                  </>
                )}
              </section>
            </div>

            {/* Treatment recommendations */}
            <div className="mt-7">
              <RecommendationsPanel scanId={id} />
            </div>

            {/* Soil recommendations */}
            <div className="mt-7">
              <SoilRecommendationsPanel scanId={id} />
            </div>

            <div className="mt-8 flex flex-wrap justify-between gap-3 border-t pt-5 print:hidden">
              <Button variant="outline" asChild>
                <Link to="/scans">
                  <History className="mr-2 size-4" />
                  {t("scanDetail.back")}
                </Link>
              </Button>

              <Button asChild>
                <Link to="/detect">
                  <ScanLine className="mr-2 size-4" />
                  {t("scanHistory.scanNow")}
                </Link>
              </Button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
