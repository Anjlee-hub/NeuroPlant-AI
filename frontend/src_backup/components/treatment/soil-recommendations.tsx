import { useQuery } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import {
  AlertCircle,
  AlertTriangle,
  Check,
  ChevronDown,
  Droplets,
  FlaskConical,
  Gauge,
  HeartPulse,
  Layers,
  Leaf,
  ListCollapse,
  Mountain,
  Recycle,
  Sparkles,
  Waves,
  type LucideIcon,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { SpeakButton } from "@/components/assistant/speak-button";
import { describeSoil } from "@/components/assistant/describe";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { SoilRecommendation } from "@/types/soil";

/** All nine guidance sections start collapsed — the health summary comes first. */
const DEFAULT_OPEN_KEYS: string[] = [];

/** Structural status check — avoids importing ApiError (mocked in tests). */
function isNotFound(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    (error as { status?: unknown }).status === 404
  );
}

// Health label -> badge/track colors (full class strings so Tailwind keeps them).
const HEALTH_STYLES: Record<string, { badge: string; track: string }> = {
  excellent: {
    badge:
      "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    track: "bg-emerald-500",
  },
  good: {
    badge: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
    track: "bg-green-500",
  },
  fair: {
    badge: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    track: "bg-amber-500",
  },
  poor: {
    badge: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    track: "bg-red-500",
  },
};

// ── Panel: fetch + loading / empty / error states ─────────────────────────

/**
 * Owns the `GET /scans/{id}/soil-recommendations` query and renders its four
 * states (loading skeleton, empty state for 404, error with retry, or the full
 * soil plan). Used by both the live scan result and the scan detail page.
 */
export function SoilRecommendationsPanel({
  scanId,
  className,
}: {
  scanId: number;
  className?: string;
}) {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: ["scan-soil-recommendations", scanId],
    queryFn: () => api.getScanSoilRecommendations(scanId),
    retry: false, // a 404 (no plan) or transient error shouldn't auto-retry
  });

  if (query.isPending) {
    return (
      <div
        role="status"
        aria-label={t("soil.loading")}
        className={cn("flex flex-col gap-4", className)}
      >
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (query.isError) {
    if (isNotFound(query.error)) {
      return <SoilRecommendationsEmpty className={className} />;
    }
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center gap-3 p-6 text-center">
          <AlertCircle className="size-8 text-destructive" aria-hidden="true" />
          <p className="font-medium">{t("soil.errorTitle")}</p>
          <p className="text-sm text-muted-foreground">{t("soil.errorBody")}</p>
          <Button variant="outline" size="sm" onClick={() => void query.refetch()}>
            {t("soil.retry")}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!query.data) return null;
  return <SoilRecommendationsView recommendation={query.data} className={className} />;
}

function SoilRecommendationsEmpty({ className }: { className?: string }) {
  const { t } = useTranslation();
  return (
    <StateCard
      className={className}
      icon={Mountain}
      title={t("soil.emptyTitle")}
      body={t("soil.emptyBody")}
    />
  );
}

// ── Full soil plan ────────────────────────────────────────────────────────

interface Section {
  key: string;
  icon: LucideIcon;
  title: string;
  desc: string;
  content: ReactNode;
}

/**
 * The self-contained soil plan: a health header card (soil-health rating,
 * suitability, improvement suggestions, disease/severity/confidence context)
 * followed by one expandable card per guidance area.
 */
export function SoilRecommendationsView({
  recommendation: rec,
  className,
}: {
  recommendation: SoilRecommendation;
  className?: string;
}) {
  const { t } = useTranslation();
  const [openKeys, setOpenKeys] = useState<Set<string>>(
    () => new Set(DEFAULT_OPEN_KEYS),
  );

  const sections = buildSections(rec, t);
  const allKeys = sections.map((section) => section.key);
  const allOpen = allKeys.length > 0 && allKeys.every((key) => openKeys.has(key));

  const toggle = (key: string) =>
    setOpenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  const toggleAll = () =>
    setOpenKeys(allOpen ? new Set<string>() : new Set(allKeys));

  const cropLabel = rec.disease.crop_name ?? "";
  const subtitle = cropLabel
    ? t("soil.subtitle", { disease: rec.disease.name, crop: cropLabel })
    : t("soil.subtitleNoCrop", { disease: rec.disease.name });

  return (
    <section className={cn("flex flex-col gap-4", className)} aria-label={t("soil.title")}>
      <Card>
        <CardContent className="p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
                {t("soil.planLabel")}
              </p>
              <h2 className="mt-1 text-xl font-bold tracking-tight">{t("soil.title")}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
            </div>
            {sections.length > 0 && (
              <div className="flex shrink-0 flex-wrap items-center gap-2 print:hidden">
                <SpeakButton text={describeSoil(rec)} />
                <Button variant="outline" size="sm" onClick={toggleAll}>
                  <ListCollapse />
                  {allOpen ? t("soil.collapseAll") : t("soil.expandAll")}
                </Button>
              </div>
            )}
          </div>

          <SoilHealthCard rec={rec} t={t} />

          {rec.soil_suitability && (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t("soil.suitability")}
              </p>
              <p className="mt-1 text-sm leading-relaxed">{rec.soil_suitability}</p>
            </div>
          )}

          {rec.improvement_suggestions.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t("soil.improvements")}
              </p>
              <ul className="mt-2 flex flex-col gap-2">
                {rec.improvement_suggestions.map((suggestion, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    <Check
                      className="mt-0.5 size-4 shrink-0 text-brand-600 dark:text-brand-400"
                      aria-hidden="true"
                    />
                    <span>{suggestion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {rec.disease_soil_notes && (
            <div className="mt-4 rounded-md border bg-muted/40 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t("soil.diseaseNotes")}
              </p>
              <p className="mt-1 text-sm leading-relaxed">{rec.disease_soil_notes}</p>
            </div>
          )}

          {(rec.severity_notes.length > 0 || rec.confidence_note) && (
            <div className="mt-4 flex flex-col gap-2">
              {rec.severity_notes.map((note, index) => (
                <p
                  key={index}
                  className="flex items-start gap-2 rounded-md border border-amber-300/70 bg-amber-50/50 p-2.5 text-sm dark:border-amber-800/60 dark:bg-amber-950/30"
                >
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" aria-hidden="true" />
                  <span>{note}</span>
                </p>
              ))}
              {rec.confidence_note && (
                <p
                  role="status"
                  className="flex items-start gap-2 rounded-md border border-amber-300/70 bg-amber-50/50 p-2.5 text-sm dark:border-amber-800/60 dark:bg-amber-950/30"
                >
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" aria-hidden="true" />
                  <span>{rec.confidence_note}</span>
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {sections.map((section) => (
        <SectionCard
          key={section.key}
          section={section}
          open={openKeys.has(section.key)}
          onToggle={() => toggle(section.key)}
        />
      ))}
    </section>
  );
}

/** Soil-health rating: localized level badge + 0–5 score bar + reason. */
function SoilHealthCard({ rec, t }: { rec: SoilRecommendation; t: TFunction }) {
  const styles = HEALTH_STYLES[rec.soil_health.label] ?? HEALTH_STYLES.good;
  const labelKey = `soil.health.level.${rec.soil_health.label}`;
  const level = t(labelKey, { defaultValue: rec.soil_health.label });
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/40 p-3.5">
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
          <HeartPulse className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold">{t("soil.health.title")}</p>
          <p className="text-xs text-muted-foreground">{rec.soil_health.summary}</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className="text-2xl font-bold tabular-nums">{rec.soil_health.score.toFixed(1)}</span>
        <Badge className={cn("shrink-0 text-xs", styles.badge)}>{level}</Badge>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={5}
        aria-valuenow={rec.soil_health.score}
        aria-label={t("soil.health.score")}
      >
        <div
          className={cn("h-full rounded-full", styles.track)}
          style={{ width: `${Math.min(100, (rec.soil_health.score / 5) * 100)}%` }}
        />
      </div>
    </div>
  );
}

/** One expandable guidance card (accordion: icon + title + chevron). */
function SectionCard({
  section,
  open,
  onToggle,
}: {
  section: Section;
  open: boolean;
  onToggle: () => void;
}) {
  const headerId = `soil-${section.key}-header`;
  const contentId = `soil-${section.key}`;
  return (
    <Card className="overflow-hidden">
      <h3>
        <button
          id={headerId}
          type="button"
          aria-expanded={open}
          aria-controls={contentId}
          onClick={onToggle}
          className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left transition-colors hover:bg-muted/40"
        >
          <span className="flex min-w-0 items-center gap-3">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
              <section.icon className="size-4" aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold">{section.title}</span>
              <span className="block text-xs text-muted-foreground">{section.desc}</span>
            </span>
          </span>
          <ChevronDown
            className={cn(
              "size-4 shrink-0 text-muted-foreground transition-transform",
              open && "rotate-180",
            )}
            aria-hidden="true"
          />
        </button>
      </h3>
      <div
        id={contentId}
        role="region"
        aria-labelledby={headerId}
        className={cn("px-4 pb-4", open ? "block" : "hidden", "print:block")}
      >
        {section.content}
      </div>
    </Card>
  );
}

/** Build the nine guidance sections, skipping any area with no content. */
function buildSections(rec: SoilRecommendation, t: TFunction): Section[] {
  const sections: Section[] = [];

  const textSections: Array<[string, LucideIcon, string | null, string, string]> = [
    ["soilType", Mountain, rec.recommended_soil_type, t("soil.soilType.title"), t("soil.soilType.desc")],
    ["ph", Gauge, rec.ph_range, t("soil.ph.title"), t("soil.ph.desc")],
    ["moisture", Droplets, rec.moisture_level, t("soil.moisture.title"), t("soil.moisture.desc")],
    ["drainage", Waves, rec.drainage, t("soil.drainage.title"), t("soil.drainage.desc")],
    ["organicMatter", Leaf, rec.organic_matter, t("soil.organicMatter.title"), t("soil.organicMatter.desc")],
    ["npk", FlaskConical, rec.npk, t("soil.npk.title"), t("soil.npk.desc")],
    ["compost", Recycle, rec.compost, t("soil.compost.title"), t("soil.compost.desc")],
    ["mulching", Layers, rec.mulching, t("soil.mulching.title"), t("soil.mulching.desc")],
  ];
  for (const [key, icon, value, title, desc] of textSections) {
    if (value && value.trim()) {
      sections.push({ key, icon, title, desc, content: <p className="text-sm leading-relaxed">{value}</p> });
    }
  }

  if (rec.micronutrients.length > 0) {
    sections.push({
      key: "micronutrients",
      icon: Sparkles,
      title: t("soil.micronutrients.title"),
      desc: t("soil.micronutrients.desc"),
      content: (
        <ul className="flex flex-wrap gap-1.5">
          {rec.micronutrients.map((micronutrient, index) => (
            <li
              key={index}
              className="rounded-full border bg-background px-2.5 py-0.5 text-sm"
            >
              {micronutrient}
            </li>
          ))}
        </ul>
      ),
    });
  }

  return sections;
}
