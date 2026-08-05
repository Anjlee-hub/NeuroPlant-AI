import {
  AlertTriangle,
  Check,
  ChevronLeft,
  Copy,
  Download,
  History,
  ImageOff,
  Maximize2,
  ScanLine,
  Share2,
  Wand2,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
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

/** Label/value pair inside the details definition list. */
function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-right text-sm font-medium">{children}</dd>
    </div>
  );
}

function DetailSkeleton({ t }: { t: (key: string) => string }) {
  return (
    <div
      className="mt-4 grid gap-6 lg:grid-cols-2"
      role="status"
      aria-label={t("scanDetail.loading")}
    >
      <div className="flex flex-col gap-4">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
      <div className="flex flex-col gap-4">
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
    </div>
  );
}

/**
 * Uploaded scan image with a zoom lightbox. State (image failed / zoomed URL)
 * is owned here and reset by `key={scan.id}` at the call site, so navigating
 * between scans never leaks the previous scan's image state.
 */
function ScanImage({ url, alt }: { url: string | null; alt: string }) {
  const { t } = useTranslation();
  const [failed, setFailed] = useState(false);
  const [zoomUrl, setZoomUrl] = useState<string | null>(null);

  // Close the zoom lightbox with Escape (keyboard accessibility).
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
      <div className="flex aspect-[4/3] w-full flex-col items-center justify-center gap-2 rounded-md border bg-muted/40 text-center text-muted-foreground">
        <ImageOff className="size-8" />
        <span className="text-sm">{alt}</span>
      </div>
    );
  }

  return (
    <div className="relative">
      <img
        src={url}
        alt={alt}
        className="aspect-[4/3] w-full rounded-md border object-cover"
        onError={() => setFailed(true)}
      />
      <Button
        variant="outline"
        size="icon"
        className="absolute right-2 top-2 bg-background/85"
        aria-label={t("scanDetail.zoomImage")}
        onClick={() => setZoomUrl(url)}
      >
        <Maximize2 />
      </Button>

      {zoomUrl && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={t("scanDetail.zoomImage")}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4"
          onClick={() => setZoomUrl(null)}
        >
          <img src={zoomUrl} alt={alt} className="max-h-full max-w-full rounded-md" />
          <Button
            variant="outline"
            size="icon"
            className="absolute right-4 top-4 bg-background/85"
            aria-label={t("scanDetail.close")}
            onClick={() => setZoomUrl(null)}
          >
            <X />
          </Button>
        </div>
      )}
    </div>
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

  const invalidId = !Number.isInteger(id);
  const isError = invalidId || scanQuery.isError || explainQuery.isError;
  const explain = explainQuery.data;

  const cropName =
    scan?.crop_id != null
      ? (cropsQuery.data?.find((crop) => crop.id === scan.crop_id)?.name ?? String(scan.crop_id))
      : t("scanDetail.notSet");

  const copyPrediction = async () => {
    if (!scan) return;
    const text =
      `Disease: ${scan.disease_name}\n` +
      `Confidence: ${formatPercent(scan.confidence)}\n` +
      `AI provider: ${scan.provider} (${scan.model_version ?? t("scanDetail.notSet")})`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard unavailable (non-secure context) — nothing to recover.
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link
        to="/scans"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground print:hidden"
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
        <div className="mt-4">
          <header className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
                {scan.disease_name}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {formatDate(scan.created_at, i18n.language)}
              </p>
            </div>
            <ConfidenceBadge value={scan.confidence} hint={t("scanDetail.confidence")} />
          </header>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            {/* ── Images column ───────────────────────────────────────── */}
            <section className="flex flex-col gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{t("scanDetail.uploadedImage")}</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScanImage
                    key={scan.id}
                    url={scan.media_items[0]?.url ?? null}
                    alt={scan.disease_name}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{t("scanDetail.heatmapTitle")}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  {explain && explain.heatmap && explain.overlay_url ? (
                    <>
                      <img
                        src={explain.overlay_url}
                        alt={t("scanDetail.overlayTitle")}
                        className="w-full rounded-md border"
                        onError={(event) => {
                          event.currentTarget.style.display = "none";
                        }}
                      />
                      {explain.heatmap_url && (
                        <img
                          src={explain.heatmap_url}
                          alt={t("scanDetail.heatmapTitle")}
                          className="w-full rounded-md border"
                          onError={(event) => {
                            event.currentTarget.style.display = "none";
                          }}
                        />
                      )}
                      <p className="text-xs text-muted-foreground">
                        {t("scanDetail.heatmapCaption", {
                          provider: explain.heatmap.provider,
                          time: formatMs(explain.heatmap.time_ms),
                        })}
                      </p>
                      <a
                        href={explain.overlay_url}
                        download={`scan-${id}-heatmap.png`}
                        className="inline-flex items-center justify-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground print:hidden"
                      >
                        <Download />
                        {t("scanDetail.downloadHeatmap")}
                      </a>
                    </>
                  ) : (
                    <div className="flex flex-col items-center gap-2 rounded-md border bg-muted/40 p-6 text-center">
                      <Wand2 className="size-8 text-muted-foreground" />
                      <p className="text-sm font-medium text-foreground">
                        {t("scanDetail.noHeatmapTitle")}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {t("scanDetail.noHeatmapBody")}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </section>

            {/* ── Details column ──────────────────────────────────────── */}
            <section className="flex flex-col gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{t("scanDetail.detailsTitle")}</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="divide-y divide-border">
                    <DetailRow label={t("scanDetail.crop")}>{cropName}</DetailRow>
                    <DetailRow label={t("scanDetail.part")}>
                      {scan.part_type ? t(`scanHistory.partType.${scan.part_type}`) : t("scanDetail.notSet")}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.disease")}>{scan.disease_name}</DetailRow>
                    <DetailRow label={t("scanDetail.severity")}>
                      {scan.severity ? (
                        <SeverityBadge severity={scan.severity} />
                      ) : (
                        t("scanDetail.notSet")
                      )}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.confidence")}>
                      {formatPercent(scan.confidence)}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.confidenceLevel")}>
                      {explain ? (
                        <Badge variant={confidenceVariant(explain.confidence.top)}>
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
                      {explain ? formatMs(explain.timing.inference_time_ms) : t("scanDetail.notSet")}
                    </DetailRow>
                    <DetailRow label={t("scanDetail.provider")}>{scan.provider}</DetailRow>
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

                  <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4 print:hidden">
                    <Button variant="outline" onClick={() => void copyPrediction()}>
                      {copied ? <Check /> : <Copy />}
                      {copied ? t("scanDetail.copied") : t("scanDetail.copy")}
                    </Button>
                    <Button variant="outline" onClick={() => setShareNote(true)}>
                      <Share2 />
                      {t("scanDetail.share")}
                    </Button>
                  </div>
                  {shareNote && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      {t("scanDetail.shareComingSoon")}
                    </p>
                  )}
                </CardContent>
              </Card>

              {explain && (
                <>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">{t("scanDetail.adviceTitle")}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div
                        className={
                          explain.confidence.level === "low"
                            ? "flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
                            : "flex items-start gap-2 rounded-md bg-muted/60 p-3 text-sm"
                        }
                      >
                        {explain.confidence.level === "low" && (
                          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                        )}
                        <p>
                          {explain.confidence.level === "low" && (
                            <span className="mb-1 block font-semibold">
                              {t("scanDetail.lowConfidenceTitle")}
                            </span>
                          )}
                          {explain.confidence.advice}
                        </p>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">{t("scanDetail.topPredictions")}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {explain.top5.length > 0 ? (
                        <ol className="flex flex-col gap-2.5">
                          {explain.top5.slice(0, 5).map((ranking, index) => (
                            <li key={`${ranking.disease_name}-${index}`}>
                              <div className="flex items-center justify-between gap-3 text-sm">
                                <span className="flex min-w-0 items-center gap-2.5">
                                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
                                    {index + 1}
                                  </span>
                                  <span className="truncate font-medium">
                                    {ranking.disease_name}
                                  </span>
                                </span>
                                <span className="shrink-0 font-semibold">
                                  {formatPercent(ranking.confidence)}
                                </span>
                              </div>
                              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                                <div
                                  className="h-full rounded-full bg-brand-500"
                                  style={{ width: `${Math.round(ranking.confidence * 100)}%` }}
                                />
                              </div>
                            </li>
                          ))}
                        </ol>
                      ) : (
                        <p className="text-sm text-muted-foreground">{t("scanDetail.noTop5")}</p>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">{t("scanDetail.explanation")}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm leading-relaxed">{explain.explanation}</p>
                    </CardContent>
                  </Card>
                </>
              )}
            </section>
          </div>

          <div className="mt-8">
            <RecommendationsPanel scanId={id} />
          </div>
        </div>
      )}

    </div>
  );
}
