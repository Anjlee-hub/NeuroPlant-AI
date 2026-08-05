import { useQuery } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import {
  AlertCircle,
  AlertTriangle,
  Ban,
  CalendarDays,
  Check,
  ChevronDown,
  CloudRain,
  Droplets,
  Eye,
  FlaskConical,
  Flower2,
  Home,
  ListCollapse,
  Printer,
  ShieldCheck,
  Sprout,
  Sun,
  ThermometerSun,
  type LucideIcon,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  ChemicalRecommendation,
  DiseaseRecommendation,
  HomemadeRemedy,
  OrganicRemedy,
} from "@/types/recommendation";

/** The three treatment lists start expanded; the guidance sections fold away. */
const DEFAULT_OPEN_KEYS = ["homemade", "organic", "chemical"];

/** Structural status check — avoids importing ApiError (mocked in tests). */
function isNotFound(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    (error as { status?: unknown }).status === 404
  );
}

// ── Panel: fetch + loading / empty / error states ─────────────────────────

/**
 * Owns the `GET /scans/{id}/recommendations` query and renders its four
 * states (loading skeleton, empty state for 404, error with retry, or the
 * full plan). Used by both the live scan result and the scan detail page.
 */
export function RecommendationsPanel({
  scanId,
  className,
}: {
  scanId: number;
  className?: string;
}) {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: ["scan-recommendations", scanId],
    queryFn: () => api.getScanRecommendations(scanId),
    retry: false, // a 404 (no plan) or transient error shouldn't auto-retry
  });

  if (query.isPending) {
    return (
      <div
        role="status"
        aria-label={t("treatment.loading")}
        className={cn("flex flex-col gap-4", className)}
      >
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
    );
  }

  if (query.isError) {
    if (isNotFound(query.error)) {
      return <RecommendationsEmpty className={className} />;
    }
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center gap-3 p-6 text-center">
          <AlertCircle className="size-8 text-destructive" aria-hidden="true" />
          <p className="font-medium">{t("treatment.errorTitle")}</p>
          <p className="text-sm text-muted-foreground">{t("treatment.errorBody")}</p>
          <Button variant="outline" size="sm" onClick={() => void query.refetch()}>
            {t("treatment.retry")}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!query.data) return null;
  return <RecommendationsView recommendation={query.data} className={className} />;
}

function RecommendationsEmpty({ className }: { className?: string }) {
  const { t } = useTranslation();
  return (
    <StateCard
      className={className}
      icon={Sprout}
      title={t("treatment.emptyTitle")}
      body={t("treatment.emptyBody")}
    />
  );
}

// ── Full care plan ────────────────────────────────────────────────────────

interface Section {
  key: string;
  icon: LucideIcon;
  title: string;
  desc: string;
  content: ReactNode;
}

/**
 * The self-contained treatment plan: a header card (disease context, print +
 * expand-all controls, overview/cause/symptoms/spread) followed by one
 * expandable card per guidance category. Every section is forced open under
 * `print` so a printed report always shows the full plan.
 */
export function RecommendationsView({
  recommendation: rec,
  className,
}: {
  recommendation: DiseaseRecommendation;
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
    ? t("treatment.subtitle", { disease: rec.disease.name, crop: cropLabel })
    : t("treatment.subtitleNoCrop", { disease: rec.disease.name });

  return (
    <section className={cn("flex flex-col gap-4", className)} aria-label={t("treatment.title")}>
      <Card>
        <CardContent className="p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
                {t("treatment.planLabel")}
              </p>
              <h2 className="mt-1 text-xl font-bold tracking-tight">{t("treatment.title")}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2 print:hidden">
              <Button variant="outline" size="sm" onClick={toggleAll}>
                <ListCollapse />
                {allOpen ? t("treatment.collapseAll") : t("treatment.expandAll")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => window.print()}>
                <Printer />
                {t("treatment.print")}
              </Button>
            </div>
          </div>

          {rec.overview && (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t("treatment.overview")}
              </p>
              <p className="mt-1 text-sm leading-relaxed">{rec.overview}</p>
            </div>
          )}

          {(rec.cause || rec.spread_mechanism) && (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {rec.cause && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {t("treatment.cause")}
                  </p>
                  <p className="mt-1 text-sm leading-relaxed">{rec.cause}</p>
                </div>
              )}
              {rec.spread_mechanism && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {t("treatment.spread")}
                  </p>
                  <p className="mt-1 text-sm leading-relaxed">{rec.spread_mechanism}</p>
                </div>
              )}
            </div>
          )}

          {rec.symptoms.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t("treatment.symptoms")}
              </p>
              <ul className="mt-2 grid gap-1.5 sm:grid-cols-2">
                {rec.symptoms.map((symptom, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    <span
                      className="mt-1.5 size-1.5 shrink-0 rounded-full bg-brand-500"
                      aria-hidden="true"
                    />
                    <span>{symptom}</span>
                  </li>
                ))}
              </ul>
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

/** One expandable category card (accordion: icon + title + chevron). */
function SectionCard({
  section,
  open,
  onToggle,
}: {
  section: Section;
  open: boolean;
  onToggle: () => void;
}) {
  const headerId = `treatment-${section.key}-header`;
  const contentId = `treatment-${section.key}`;
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

/** Build the 12 guidance sections, skipping any category with no content. */
function buildSections(rec: DiseaseRecommendation, t: TFunction): Section[] {
  const sections: Section[] = [];

  if (rec.homemade_remedies.length > 0) {
    sections.push({
      key: "homemade",
      icon: Home,
      title: t("treatment.homemade.title"),
      desc: t("treatment.homemade.desc"),
      content: (
        <div className="flex flex-col gap-3">
          {rec.homemade_remedies.map((remedy, index) => (
            <HomemadeRemedyItem key={index} remedy={remedy} t={t} />
          ))}
        </div>
      ),
    });
  }

  if (rec.organic_remedies.length > 0) {
    sections.push({
      key: "organic",
      icon: Sprout,
      title: t("treatment.organic.title"),
      desc: t("treatment.organic.desc"),
      content: (
        <div className="flex flex-col gap-3">
          {rec.organic_remedies.map((remedy, index) => (
            <OrganicRemedyItem key={index} remedy={remedy} t={t} />
          ))}
        </div>
      ),
    });
  }

  if (rec.chemical_recommendations.length > 0) {
    sections.push({
      key: "chemical",
      icon: FlaskConical,
      title: t("treatment.chemical.title"),
      desc: t("treatment.chemical.desc"),
      content: (
        <div className="flex flex-col gap-3">
          {rec.chemical_recommendations.map((item, index) => (
            <ChemicalItem key={index} item={item} t={t} />
          ))}
        </div>
      ),
    });
  }

  const textSections: Array<[string, LucideIcon, string | null, string, string]> = [
    ["fertilizer", Flower2, rec.fertilizer, t("treatment.fertilizer.title"), t("treatment.fertilizer.desc")],
    ["watering", Droplets, rec.watering, t("treatment.watering.title"), t("treatment.watering.desc")],
    ["sunlight", Sun, rec.sunlight, t("treatment.sunlight.title"), t("treatment.sunlight.desc")],
    ["temperature", ThermometerSun, rec.temperature, t("treatment.temperature.title"), t("treatment.temperature.desc")],
    ["humidity", CloudRain, rec.humidity, t("treatment.humidity.title"), t("treatment.humidity.desc")],
  ];
  for (const [key, icon, value, title, desc] of textSections) {
    if (value && value.trim()) {
      sections.push({ key, icon, title, desc, content: <p className="text-sm leading-relaxed">{value}</p> });
    }
  }

  if (rec.prevention_tips.length > 0) {
    sections.push({
      key: "prevention",
      icon: ShieldCheck,
      title: t("treatment.prevention.title"),
      desc: t("treatment.prevention.desc"),
      content: <BulletList items={rec.prevention_tips} />,
    });
  }

  if (rec.recovery_timeline && rec.recovery_timeline.trim()) {
    sections.push({
      key: "recovery",
      icon: CalendarDays,
      title: t("treatment.recovery.title"),
      desc: t("treatment.recovery.desc"),
      content: <p className="text-sm leading-relaxed">{rec.recovery_timeline}</p>,
    });
  }

  if (rec.isolation && rec.isolation.trim()) {
    sections.push({
      key: "isolation",
      icon: Ban,
      title: t("treatment.isolation.title"),
      desc: t("treatment.isolation.desc"),
      content: <p className="text-sm leading-relaxed">{rec.isolation}</p>,
    });
  }

  if (rec.monitoring_advice.length > 0) {
    sections.push({
      key: "monitoring",
      icon: Eye,
      title: t("treatment.monitoring.title"),
      desc: t("treatment.monitoring.desc"),
      content: <BulletList items={rec.monitoring_advice} />,
    });
  }

  return sections;
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item, index) => (
        <li key={index} className="flex items-start gap-2 text-sm">
          <Check className="mt-0.5 size-4 shrink-0 text-brand-600 dark:text-brand-400" aria-hidden="true" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

// ── Individual remedy cards ───────────────────────────────────────────────

function HomemadeRemedyItem({ remedy, t }: { remedy: HomemadeRemedy; t: TFunction }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-3.5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-sm font-semibold">{remedy.title}</p>
        {remedy.category && (
          <Badge variant="secondary" className="shrink-0 text-xs">
            {t(`treatment.homemade.categories.${remedy.category}`, {
              defaultValue: remedy.category,
            })}
          </Badge>
        )}
      </div>

      {remedy.ingredients.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t("treatment.homemade.ingredients")}
          </p>
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {remedy.ingredients.map((ingredient, index) => (
              <li
                key={index}
                className="rounded-full border bg-background px-2.5 py-0.5 text-xs"
              >
                {ingredient}
              </li>
            ))}
          </ul>
        </div>
      )}

      {remedy.instructions && (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t("treatment.homemade.preparation")}
          </p>
          <p className="mt-1 text-sm leading-relaxed">{remedy.instructions}</p>
        </div>
      )}

      {remedy.frequency && (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t("treatment.homemade.frequency")}
          </p>
          <p className="mt-1 text-sm">{remedy.frequency}</p>
        </div>
      )}
    </div>
  );
}

function OrganicRemedyItem({ remedy, t }: { remedy: OrganicRemedy; t: TFunction }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-3.5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-sm font-semibold">{remedy.title}</p>
        {remedy.category && (
          <Badge variant="secondary" className="shrink-0 text-xs">
            {t(`treatment.organic.categories.${remedy.category}`, {
              defaultValue: remedy.category,
            })}
          </Badge>
        )}
      </div>

      {remedy.application && (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t("treatment.organic.application")}
          </p>
          <p className="mt-1 text-sm leading-relaxed">{remedy.application}</p>
        </div>
      )}

      {remedy.frequency && (
        <div className="mt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t("treatment.organic.frequency")}
          </p>
          <p className="mt-1 text-sm">{remedy.frequency}</p>
        </div>
      )}
    </div>
  );
}

function ChemicalItem({ item, t }: { item: ChemicalRecommendation; t: TFunction }) {
  return (
    <div className="rounded-lg border border-amber-300/70 bg-amber-50/50 p-3.5 dark:border-amber-800/60 dark:bg-amber-950/30">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-sm font-semibold">{item.product}</p>
        {item.category && (
          <Badge variant="outline" className="shrink-0 text-xs">
            {t(`treatment.chemical.categories.${item.category}`, {
              defaultValue: item.category,
            })}
          </Badge>
        )}
      </div>

      <dl className="mt-2 flex flex-col gap-1 text-sm">
        <div className="flex items-start justify-between gap-3">
          <dt className="text-muted-foreground">{t("treatment.chemical.dosage")}</dt>
          <dd className="text-right font-medium">{item.dosage}</dd>
        </div>
        <div className="flex items-start justify-between gap-3">
          <dt className="text-muted-foreground">{t("treatment.chemical.interval")}</dt>
          <dd className="text-right font-medium">{item.application_interval}</dd>
        </div>
      </dl>

      {item.safety_precautions.length > 0 && (
        <div className="mt-3 rounded-md border border-amber-300 bg-background/80 p-3 dark:border-amber-800">
          <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-amber-700 dark:text-amber-300">
            <AlertTriangle className="size-3.5 shrink-0" aria-hidden="true" />
            {t("treatment.chemical.warning")}
          </p>
          <ul className="mt-2 flex list-disc flex-col gap-1 pl-4 text-sm">
            {item.safety_precautions.map((precaution, index) => (
              <li key={index}>{precaution}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
