import {
  AlertCircle,
  Camera,
  CheckCircle2,
  History,
  ImagePlus,
  ScanLine,
  Trash2,
  Wand2,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useAuth } from "@/stores/auth";
import { api, errorMessage } from "@/lib/api";
import { formatPercent } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  ConfidenceBadge,
  SeverityBadge,
  confidenceVariant,
} from "@/components/ui/status-badges";
import { StateCard } from "@/components/ui/state-card";
import type { Scan, ScanExplain, ScanPartType } from "@/types/scan";

const PART_TYPES: ScanPartType[] = ["leaf", "fruit", "stem", "plant", "whole"];

type Phase = "form" | "submitting" | "result" | "error";

/** Label/value pair in the result summary. */
function ResultRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-right text-sm font-medium">{children}</dd>
    </div>
  );
}

/**
 * Post-upload diagnosis: disease, confidence/severity badges, crop/part,
 * Grad-CAM heatmap, top-5 rankings, AI explanation and advice. The scan is
 * already persisted by the backend — this renders the "live" result.
 */
function ResultView({
  scan,
  explain,
  cropName,
  onNewScan,
}: {
  scan: Scan;
  explain: ScanExplain | null;
  cropName: string | null;
  onNewScan: () => void;
}) {
  const { t } = useTranslation();

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 text-sm font-medium text-brand-600 dark:text-brand-400">
        <CheckCircle2 className="size-4" />
        {t("scanCrop.savedNote")}
      </div>

      <Card className="mt-3">
        <CardContent className="p-6">
          <header className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm text-muted-foreground">{t("scanCrop.resultTitle")}</p>
              <h2 className="mt-1 text-2xl font-bold tracking-tight">{scan.disease_name}</h2>
            </div>
            <ConfidenceBadge value={scan.confidence} hint={t("scanCrop.confidence")} />
          </header>

          <dl className="mt-5 divide-y divide-border">
            <ResultRow label={t("scanCrop.crop")}>
              {cropName ?? t("scanCrop.notSet")}
            </ResultRow>
            <ResultRow label={t("scanCrop.part")}>
              {scan.part_type ? t(`scanCrop.parts.${scan.part_type}`) : t("scanCrop.notSet")}
            </ResultRow>
            <ResultRow label={t("scanCrop.severity")}>
              {scan.severity ? <SeverityBadge severity={scan.severity} /> : t("scanCrop.notSet")}
            </ResultRow>
            <ResultRow label={t("scanCrop.stage")}>
              {scan.stage ?? t("scanCrop.notSet")}
            </ResultRow>
            {explain && (
              <ResultRow label={t("scanCrop.confidence")}>
                <Badge variant={confidenceVariant(explain.confidence.top)}>
                  {explain.confidence.level}
                </Badge>
              </ResultRow>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* ── AI explanation + advice ──────────────────────────────────── */}
      {explain && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{t("scanDetail.explanation")}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed">{explain.explanation}</p>
            </CardContent>
          </Card>

          <div className="flex flex-col gap-4">
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
                  <p>{explain.confidence.advice}</p>
                </div>
              </CardContent>
            </Card>

            {explain.overlay_url && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{t("scanDetail.heatmapTitle")}</CardTitle>
                </CardHeader>
                <CardContent>
                  <img
                    src={explain.overlay_url}
                    alt={t("scanDetail.overlayTitle")}
                    className="w-full rounded-md border"
                    onError={(event) => {
                      event.currentTarget.style.display = "none";
                    }}
                  />
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* ── Top predictions ──────────────────────────────────────────── */}
      {explain && explain.top5.length > 0 && (
        <Card className="mt-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("scanDetail.topPredictions")}</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="flex flex-col gap-2.5">
              {explain.top5.slice(0, 5).map((ranking, index) => (
                <li key={`${ranking.disease_name}-${index}`}>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="flex min-w-0 items-center gap-2.5">
                      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
                        {index + 1}
                      </span>
                      <span className="truncate font-medium">{ranking.disease_name}</span>
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
          </CardContent>
        </Card>
      )}

      {/* ── Actions ──────────────────────────────────────────────────── */}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Button asChild>
          <Link to={`/scans/${scan.id}`}>{t("scanCrop.viewDetails")}</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/scans">
            <History />
            {t("scanCrop.viewHistory")}
          </Link>
        </Button>
        <Button variant="outline" onClick={onNewScan}>
          <ScanLine />
          {t("scanCrop.scanAnother")}
        </Button>
      </div>
    </div>
  );
}

export function ScanCropPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const uploadInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [cropId, setCropId] = useState<string>("");
  const [partType, setPartType] = useState<string>("");
  const [phase, setPhase] = useState<Phase>("form");
  const [result, setResult] = useState<Scan | null>(null);
  const [explain, setExplain] = useState<ScanExplain | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const cropsQuery = useQuery({
    queryKey: ["crops"],
    queryFn: () => api.listCrops(),
    enabled: !!user,
    staleTime: 5 * 60_000,
  });

  // Revoke object URLs when the preview is replaced or the page unmounts.
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const pickFile = (picked: File | null) => {
    if (!picked) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(picked);
    setPreviewUrl(URL.createObjectURL(picked));
    setPhase("form");
  };

  const reset = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setCropId("");
    setPartType("");
    setPhase("form");
    setResult(null);
    setExplain(null);
    setErrorMsg("");
  };

  const submit = async () => {
    if (!file) return;
    setPhase("submitting");
    try {
      const scan = await api.uploadScan({
        files: [file],
        clientScanId: crypto.randomUUID(),
        cropId: cropId ? Number(cropId) : null,
        partType: partType ? (partType as ScanPartType) : null,
      });
      // The scan is persisted server-side — drop stale history caches so it
      // shows up in Scan History immediately.
      void queryClient.invalidateQueries({ queryKey: ["scans"] });
      setResult(scan);
      setPhase("result");
      try {
        setExplain(await api.getScanExplain(scan.id));
      } catch {
        setExplain(null); // prediction still shown; explain is best-effort
      }
    } catch (err) {
      setErrorMsg(errorMessage(err));
      setPhase("error");
    }
  };

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={ScanLine} title={t("scanCrop.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("scanCrop.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{t("scanCrop.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("scanCrop.subtitle")}</p>
      </header>

      {phase === "result" && result ? (
        <ResultView
          scan={result}
          explain={explain}
          cropName={
            cropId
              ? (cropsQuery.data?.find((crop) => crop.id === Number(cropId))?.name ?? null)
              : result.crop_id != null
                ? (cropsQuery.data?.find((crop) => crop.id === result.crop_id)?.name ?? null)
                : null
          }
          onNewScan={reset}
        />
      ) : phase === "submitting" ? (
        <Card className="mt-6">
          <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
            <div
              className="size-10 animate-spin rounded-full border-4 border-muted border-t-brand-500"
              role="status"
              aria-label={t("scanCrop.submitting")}
            />
            <p className="text-sm font-medium">{t("scanCrop.submitting")}</p>
            {previewUrl && (
              <img
                src={previewUrl}
                alt={t("scanCrop.previewAlt")}
                className="aspect-video w-full max-w-sm rounded-md border object-cover"
              />
            )}
          </CardContent>
        </Card>
      ) : phase === "error" ? (
        <StateCard
          className="mt-6"
          icon={AlertCircle}
          title={t("scanCrop.errorTitle")}
          body={errorMsg || t("scanCrop.errorBody")}
          tone="destructive"
        >
          <Button variant="outline" onClick={() => setPhase("form")}>
            <Wand2 />
            {t("scanCrop.retry")}
          </Button>
        </StateCard>
      ) : (
        <Card className="mt-6">
          <CardContent className="p-6 sm:p-8">
            {/* ── Photo picker ──────────────────────────────────────── */}
            <div>
              <h2 className="text-base font-semibold">{t("scanCrop.photoTitle")}</h2>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <Button
                  variant="outline"
                  onClick={() => uploadInputRef.current?.click()}
                >
                  <ImagePlus />
                  {file ? t("scanCrop.replacePhoto") : t("scanCrop.uploadPhoto")}
                </Button>
                <Button variant="outline" onClick={() => cameraInputRef.current?.click()}>
                  <Camera />
                  {t("scanCrop.cameraPhoto")}
                </Button>
                {file && (
                  <Button variant="ghost" onClick={reset}>
                    <Trash2 />
                    {t("scanCrop.removePhoto")}
                  </Button>
                )}
              </div>
              <p className="mt-2 text-xs text-muted-foreground">{t("scanCrop.photoHint")}</p>

              {/* Hidden inputs — the camera variant uses `capture` so
                  mobile browsers open the camera directly. */}
              <input
                ref={uploadInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                data-testid="scan-upload-input"
                onChange={(event) => pickFile(event.target.files?.[0] ?? null)}
              />
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                data-testid="scan-camera-input"
                onChange={(event) => pickFile(event.target.files?.[0] ?? null)}
              />
            </div>

            {/* ── Preview ───────────────────────────────────────────── */}
            {previewUrl ? (
              <img
                src={previewUrl}
                alt={t("scanCrop.previewAlt")}
                className="mt-4 aspect-video w-full max-w-lg rounded-md border object-cover"
              />
            ) : (
              <div className="mt-4 flex aspect-video w-full max-w-lg flex-col items-center justify-center gap-2 rounded-md border border-dashed bg-muted/40 text-center text-muted-foreground">
                <ImagePlus className="size-8" />
                <p className="text-sm">{t("scanCrop.noPhoto")}</p>
              </div>
            )}

            {/* ── Crop + part ───────────────────────────────────────── */}
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="scan-crop" className="text-sm font-medium text-muted-foreground">
                  {t("scanCrop.cropLabel")}
                </Label>
                <Select
                  id="scan-crop"
                  value={cropId}
                  onChange={(event) => setCropId(event.target.value)}
                >
                  <option value="">{t("scanCrop.cropPlaceholder")}</option>
                  {(cropsQuery.data ?? []).map((crop) => (
                    <option key={crop.id} value={crop.id}>
                      {crop.name}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="scan-part" className="text-sm font-medium text-muted-foreground">
                  {t("scanCrop.partLabel")}
                </Label>
                <Select
                  id="scan-part"
                  value={partType}
                  onChange={(event) => setPartType(event.target.value)}
                >
                  <option value="">{t("scanCrop.partPlaceholder")}</option>
                  {PART_TYPES.map((part) => (
                    <option key={part} value={part}>
                      {t(`scanCrop.parts.${part}`)}
                    </option>
                  ))}
                </Select>
              </div>
            </div>

            <Button className="mt-6" size="lg" disabled={!file} onClick={() => void submit()}>
              <ScanLine />
              {t("scanCrop.submit")}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
