
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  ChevronRight,
  CloudUpload,
  History,
  ImagePlus,
  Leaf,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Trash2,
  WandSparkles,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode, type DragEvent } from "react";
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
import { RecommendationsPanel } from "@/components/treatment/recommendations";
import { SoilRecommendationsPanel } from "@/components/treatment/soil-recommendations";
import type { Scan, ScanExplain, ScanPartType } from "@/types/scan";

const PART_TYPES: ScanPartType[] = ["leaf", "fruit", "stem", "plant", "whole"];

type Phase = "form" | "submitting" | "result" | "error";

function ResultRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/70 py-3 last:border-0">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-right text-sm font-semibold">{children}</dd>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="mb-5">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">
        {eyebrow}
      </p>
      <h2 className="mt-1 text-xl font-bold tracking-tight sm:text-2xl">
        {title}
      </h2>
      {description && (
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      )}
    </div>
  );
}

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
    <div className="mt-8 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-green-200 bg-green-50 p-4 text-green-900 dark:border-green-900 dark:bg-green-950/30 dark:text-green-200">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
            <CheckCircle2 className="size-5" />
          </span>
          <div>
            <p className="font-semibold">{t("scanCrop.savedNote")}</p>
            <p className="text-xs opacity-80">Your scan has been processed.</p>
          </div>
        </div>
        <Badge variant="outline" className="border-green-300 text-green-800 dark:text-green-200">
          <ShieldCheck className="mr-1 size-3" />
          Diagnosis saved
        </Badge>
      </div>

      <Card className="overflow-hidden rounded-2xl border-border/70 shadow-sm">
        <div className="h-1.5 bg-gradient-to-r from-green-700 via-green-500 to-lime-400" />
        <CardContent className="p-5 sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                {t("scanCrop.resultTitle")}
              </p>
              <h2 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
                {scan.disease_name}
              </h2>
            </div>
            <ConfidenceBadge value={scan.confidence} hint={t("scanCrop.confidence")} />
          </div>

          <dl className="mt-6 rounded-xl bg-muted/30 px-4">
            <ResultRow label={t("scanCrop.crop")}>
              {cropName ?? t("scanCrop.notSet")}
            </ResultRow>
            <ResultRow label={t("scanCrop.part")}>
              {scan.part_type
                ? t(`scanCrop.parts.${scan.part_type}`)
                : t("scanCrop.notSet")}
            </ResultRow>
            <ResultRow label={t("scanCrop.severity")}>
              {scan.severity ? (
                <SeverityBadge severity={scan.severity} />
              ) : (
                t("scanCrop.notSet")
              )}
            </ResultRow>
            <ResultRow label={t("scanCrop.stage")}>
              {scan.stage ?? t("scanCrop.notSet")}
            </ResultRow>
            {explain && (
              <ResultRow label={t("scanCrop.confidence")}>
                <Badge variant={confidenceVariant(explain.confidence.top)}>
                  {t(`scanDetail.levels.${explain.confidence.level}`)}
                </Badge>
              </ResultRow>
            )}
          </dl>
        </CardContent>
      </Card>

      {explain && (
        <div className="grid gap-5 lg:grid-cols-2">
          <Card className="rounded-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Sparkles className="size-5 text-primary" />
                {t("scanDetail.explanation")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-7 text-muted-foreground">
                {explain.explanation}
              </p>
            </CardContent>
          </Card>

          <Card className="rounded-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldCheck className="size-5 text-primary" />
                {t("scanDetail.adviceTitle")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={
                  explain.confidence.level === "low" ||
                  explain.confidence.level === "unavailable"
                    ? "rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm leading-6 text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200"
                    : "rounded-xl bg-muted/50 p-4 text-sm leading-6"
                }
              >
                {explain.confidence.advice}
              </div>
            </CardContent>
          </Card>

          {explain.overlay_url && (
            <Card className="rounded-2xl lg:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ScanLine className="size-5 text-primary" />
                  {t("scanDetail.heatmapTitle")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <img
                  src={explain.overlay_url}
                  alt={t("scanDetail.overlayTitle")}
                  className="mx-auto max-h-[480px] w-full rounded-xl border border-border object-contain"
                  onError={(event) => {
                    event.currentTarget.style.display = "none";
                  }}
                />
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {explain && explain.top5.length > 0 && (
        <Card className="rounded-2xl">
          <CardHeader>
            <CardTitle className="text-base">
              {t("scanDetail.topPredictions")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-4">
              {explain.top5.slice(0, 5).map((ranking, index) => (
                <li key={`${ranking.disease_name}-${index}`}>
                  <div className="mb-2 flex items-center justify-between gap-3 text-sm">
                    <span className="flex min-w-0 items-center gap-3">
                      <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-bold text-primary">
                        {index + 1}
                      </span>
                      <span className="truncate font-medium">
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
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-green-700 to-lime-500"
                        style={{
                          width: `${Math.max(
                            0,
                            Math.min(100, ranking.confidence * 100),
                          )}%`,
                        }}
                      />
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      <section>
        <SectionHeading
          eyebrow="Next steps"
          title="Recommended treatment"
          description="Review the recommendations associated with this diagnosis."
        />
        <RecommendationsPanel scanId={scan.id} />
      </section>

      <section>
        <SectionHeading
          eyebrow="Field guidance"
          title="Soil recommendations"
          description="Explore the soil guidance available for this scan."
        />
        <SoilRecommendationsPanel scanId={scan.id} />
      </section>

      <div className="flex flex-wrap gap-3 border-t border-border pt-5 print:hidden">
        <Button asChild>
          <Link to={`/scans/${scan.id}/doctor`}>
            <Stethoscope className="mr-2 size-4" />
            {t("doctor.title")}
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link to={`/scans/${scan.id}`}>
            {t("scanCrop.viewDetails")}
            <ChevronRight className="ml-1 size-4" />
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/scans">
            <History className="mr-2 size-4" />
            {t("scanCrop.viewHistory")}
          </Link>
        </Button>
        <Button variant="outline" onClick={onNewScan}>
          <ScanLine className="mr-2 size-4" />
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
  const [cropId, setCropId] = useState("");
  const [partType, setPartType] = useState("");
  const [phase, setPhase] = useState<Phase>("form");
  const [result, setResult] = useState<Scan | null>(null);
  const [explain, setExplain] = useState<ScanExplain | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const cropsQuery = useQuery({
    queryKey: ["crops"],
    queryFn: () => api.listCrops(),
    enabled: !!user,
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const pickFile = (picked: File | null) => {
    if (!picked) return;

    if (!picked.type.startsWith("image/")) {
      setErrorMsg("Please select a valid image file.");
      setPhase("error");
      return;
    }

    setFile(picked);
    setPreviewUrl(URL.createObjectURL(picked));
    setPhase("form");
    setErrorMsg("");
    setResult(null);
    setExplain(null);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
    pickFile(event.dataTransfer.files?.[0] ?? null);
  };

  const reset = () => {
    setFile(null);
    setPreviewUrl(null);
    setCropId("");
    setPartType("");
    setPhase("form");
    setResult(null);
    setExplain(null);
    setErrorMsg("");

    if (uploadInputRef.current) uploadInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  };

  const submit = async () => {
    if (!file || phase === "submitting") return;

    setPhase("submitting");
    setErrorMsg("");

    try {
      const scan = await api.uploadScan({
        files: [file],
        clientScanId: crypto.randomUUID(),
        cropId: cropId ? Number(cropId) : null,
        partType: partType ? (partType as ScanPartType) : null,
      });

      void queryClient.invalidateQueries({ queryKey: ["scans"] });

      setResult(scan);
      setPhase("result");

      try {
        setExplain(await api.getScanExplain(scan.id));
      } catch {
        setExplain(null);
      }
    } catch (err) {
      setErrorMsg(errorMessage(err));
      setPhase("error");
    }
  };

  if (!user) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <StateCard icon={ScanLine} title={t("scanCrop.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("scanCrop.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const selectedCrop = cropId
    ? cropsQuery.data?.find((crop) => crop.id === Number(cropId))?.name
    : undefined;

  return (
    <div className="min-h-full bg-background">
      <div className="mx-auto max-w-6xl px-4 py-7 sm:px-6 sm:py-10">
        {/* Page heading */}
        <header className="mb-8">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5 text-xs font-semibold text-primary">
            <Sparkles className="size-3.5" />
            AI CROP INTELLIGENCE
          </div>

          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                {t("scanCrop.title")}
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
                {t("scanCrop.subtitle")}
              </p>
            </div>

            <Button asChild variant="outline" className="rounded-xl">
              <Link to="/scans">
                <History className="mr-2 size-4" />
                {t("scanCrop.viewHistory")}
              </Link>
            </Button>
          </div>
        </header>

        {phase === "result" && result ? (
          <ResultView
            scan={result}
            explain={explain}
            cropName={
              selectedCrop ??
              (result.crop_id != null
                ? cropsQuery.data?.find(
                    (crop) => crop.id === result.crop_id,
                  )?.name ?? null
                : null)
            }
            onNewScan={reset}
          />
        ) : phase === "submitting" ? (
          <Card className="overflow-hidden rounded-3xl">
            <CardContent className="flex flex-col items-center gap-5 p-8 text-center sm:p-14">
              <div className="relative flex size-20 items-center justify-center rounded-full bg-primary/10">
                <Leaf className="size-9 animate-pulse text-primary" />
                <span className="absolute inset-0 animate-ping rounded-full border border-primary/30" />
              </div>
              <div>
                <h2 className="text-xl font-bold">
                  {t("scanCrop.submitting")}
                </h2>
                <p className="mt-2 max-w-md text-sm text-muted-foreground">
                  Your image is being processed. Please keep this page open.
                </p>
              </div>
              {previewUrl && (
                <img
                  src={previewUrl}
                  alt={t("scanCrop.previewAlt")}
                  className="max-h-72 w-full max-w-sm rounded-2xl border object-cover"
                />
              )}
              <div className="h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-muted">
                <div className="h-full w-2/3 animate-pulse rounded-full bg-primary" />
              </div>
            </CardContent>
          </Card>
        ) : phase === "error" ? (
          <div className="space-y-4">
            <StateCard
              icon={AlertCircle}
              title={t("scanCrop.errorTitle")}
              body={errorMsg || t("scanCrop.errorBody")}
              tone="destructive"
            >
              <div className="flex flex-wrap justify-center gap-2">
                <Button variant="outline" onClick={() => setPhase("form")}>
                  <WandSparkles className="mr-2 size-4" />
                  {t("scanCrop.retry")}
                </Button>
                <Button variant="ghost" onClick={reset}>
                  {t("scanCrop.removePhoto")}
                </Button>
              </div>
            </StateCard>
          </div>
        ) : (
          <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
            {/* Main scan form */}
            <div className="space-y-6">
              <Card className="overflow-hidden rounded-3xl border-border/70 shadow-sm">
                <div className="border-b border-border bg-muted/20 px-5 py-5 sm:px-7">
                  <div className="flex items-center gap-3">
                    <span className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <ImagePlus className="size-5" />
                    </span>
                    <div>
                      <h2 className="font-bold">{t("scanCrop.photoTitle")}</h2>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        Upload a plant image or capture one using your camera.
                      </p>
                    </div>
                  </div>
                </div>

                <CardContent className="p-5 sm:p-7">
                  <div
                    onDragOver={(event) => {
                      event.preventDefault();
                      setDragActive(true);
                    }}
                    onDragLeave={(event) => {
                      event.preventDefault();
                      setDragActive(false);
                    }}
                    onDrop={handleDrop}
                    className={`relative overflow-hidden rounded-2xl border-2 border-dashed transition-all ${
                      dragActive
                        ? "border-primary bg-primary/10"
                        : previewUrl
                          ? "border-primary/30 bg-primary/[0.02]"
                          : "border-border bg-muted/20 hover:border-primary/50"
                    }`}
                  >
                    {previewUrl ? (
                      <div className="p-3 sm:p-5">
                        <div className="relative overflow-hidden rounded-xl bg-black/5">
                          <img
                            src={previewUrl}
                            alt={t("scanCrop.previewAlt")}
                            className="mx-auto max-h-[420px] w-full object-contain"
                          />
                          <div className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-black/65 px-3 py-1.5 text-xs font-medium text-white backdrop-blur">
                            <CheckCircle2 className="size-3.5" />
                            Image selected
                          </div>
                        </div>

                        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold">
                              {file?.name}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {file
                                ? `${(file.size / (1024 * 1024)).toFixed(2)} MB`
                                : ""}
                            </p>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={reset}
                          >
                            <Trash2 className="mr-2 size-4" />
                            {t("scanCrop.removePhoto")}
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex min-h-[270px] flex-col items-center justify-center px-5 py-10 text-center sm:min-h-[320px]">
                        <span className="mb-5 flex size-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                          <CloudUpload className="size-8" />
                        </span>
                        <h3 className="text-lg font-bold">
                          {t("scanCrop.noPhoto")}
                        </h3>
                        <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
                          Drag and drop your plant image here, or choose one
                          of the options below.
                        </p>
                        <div className="mt-6 flex flex-wrap justify-center gap-3">
                          <Button
                            onClick={() => uploadInputRef.current?.click()}
                          >
                            <ImagePlus className="mr-2 size-4" />
                            {t("scanCrop.uploadPhoto")}
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => cameraInputRef.current?.click()}
                          >
                            <Camera className="mr-2 size-4" />
                            {t("scanCrop.cameraPhoto")}
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>

                  <input
                    ref={uploadInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    data-testid="scan-upload-input"
                    onChange={(event) => {
                      pickFile(event.target.files?.[0] ?? null);
                      event.target.value = "";
                    }}
                  />

                  <input
                    ref={cameraInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    data-testid="scan-camera-input"
                    onChange={(event) => {
                      pickFile(event.target.files?.[0] ?? null);
                      event.target.value = "";
                    }}
                  />

                  {file && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => uploadInputRef.current?.click()}
                      >
                        <ImagePlus className="mr-2 size-4" />
                        {t("scanCrop.replacePhoto")}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => cameraInputRef.current?.click()}
                      >
                        <Camera className="mr-2 size-4" />
                        {t("scanCrop.cameraPhoto")}
                      </Button>
                    </div>
                  )}

                  <p className="mt-4 text-xs leading-5 text-muted-foreground">
                    {t("scanCrop.photoHint")}
                  </p>
                </CardContent>
              </Card>

              {/* Crop details */}
              <Card className="rounded-3xl border-border/70 shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Leaf className="size-5 text-primary" />
                    Crop information
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Provide additional details to help contextualize the scan.
                  </p>
                </CardHeader>

                <CardContent className="grid gap-5 p-5 pt-0 sm:grid-cols-2 sm:p-6 sm:pt-0">
                  <div className="flex flex-col gap-2">
                    <Label
                      htmlFor="scan-crop"
                      className="text-sm font-semibold"
                    >
                      {t("scanCrop.cropLabel")}
                    </Label>
                    <Select
                      id="scan-crop"
                      value={cropId}
                      onChange={(event) => setCropId(event.target.value)}
                    >
                      <option value="">
                        {t("scanCrop.cropPlaceholder")}
                      </option>
                      {(cropsQuery.data ?? []).map((crop) => (
                        <option key={crop.id} value={crop.id}>
                          {crop.name}
                        </option>
                      ))}
                    </Select>
                    {cropsQuery.isLoading && (
                      <p className="text-xs text-muted-foreground">
                        Loading crops...
                      </p>
                    )}
                    {cropsQuery.isError && (
                      <p className="text-xs text-destructive">
                        Unable to load crop options.
                      </p>
                    )}
                  </div>

                  <div className="flex flex-col gap-2">
                    <Label
                      htmlFor="scan-part"
                      className="text-sm font-semibold"
                    >
                      {t("scanCrop.partLabel")}
                    </Label>
                    <Select
                      id="scan-part"
                      value={partType}
                      onChange={(event) => setPartType(event.target.value)}
                    >
                      <option value="">
                        {t("scanCrop.partPlaceholder")}
                      </option>
                      {PART_TYPES.map((part) => (
                        <option key={part} value={part}>
                          {t(`scanCrop.parts.${part}`)}
                        </option>
                      ))}
                    </Select>
                  </div>
                </CardContent>
              </Card>

              {/* Submit */}
              <div className="flex flex-col gap-3 rounded-2xl border border-primary/20 bg-primary/[0.04] p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
                <div>
                  <p className="font-semibold">Ready to analyze your crop?</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {file
                      ? "Your image is ready for AI diagnosis."
                      : "Choose a plant image to enable diagnosis."}
                  </p>
                </div>
                <Button
                  size="lg"
                  className="rounded-xl"
                  disabled={!file}
                  onClick={() => void submit()}
                >
                  <ScanLine className="mr-2 size-4" />
                  {t("scanCrop.submit")}
                </Button>
              </div>
            </div>

            {/* Guidance sidebar */}
            <aside className="space-y-5">
              <Card className="overflow-hidden rounded-3xl border-border/70">
                <div className="bg-gradient-to-br from-green-900 via-green-800 to-emerald-700 p-5 text-white">
                  <span className="flex size-11 items-center justify-center rounded-xl bg-white/15">
                    <Sparkles className="size-6" />
                  </span>
                  <h3 className="mt-4 text-lg font-bold">
                    AI-powered crop diagnosis
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-green-50/85">
                    Analyze plant images and review the diagnosis and guidance
                    returned by NeuroPlant AI.
                  </p>
                </div>
                <CardContent className="space-y-4 p-5">
                  <div className="flex items-start gap-3">
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <ScanLine className="size-4" />
                    </span>
                    <div>
                      <p className="text-sm font-semibold">Image analysis</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        Submit a clear image of the affected plant.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <ShieldCheck className="size-4" />
                    </span>
                    <div>
                      <p className="text-sm font-semibold">Confidence insights</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        Review prediction confidence and available explanations.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Leaf className="size-4" />
                    </span>
                    <div>
                      <p className="text-sm font-semibold">Treatment guidance</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        Explore treatment and soil recommendations.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-3xl border-border/70">
                <CardHeader>
                  <CardTitle className="text-base">
                    Tips for a better scan
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 text-sm text-muted-foreground">
                    {[
                      "Capture the affected plant part clearly.",
                      "Use natural lighting when possible.",
                      "Avoid blurry or distant images.",
                      "Keep the affected area visible.",
                    ].map((tip) => (
                      <li key={tip} className="flex items-start gap-2.5">
                        <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" />
                        <span>{tip}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <Card className="rounded-3xl border-border/70 bg-muted/20">
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <History className="size-4 text-primary" />
                    Previous scans
                  </div>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    Access your previous crop diagnoses and scan records.
                  </p>
                  <Button
                    asChild
                    variant="outline"
                    size="sm"
                    className="mt-4 w-full"
                  >
                    <Link to="/scans">
                      View scan history
                      <ChevronRight className="ml-1 size-4" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
