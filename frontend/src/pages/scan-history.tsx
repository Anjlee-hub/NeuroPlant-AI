
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Filter,
  History,
  Leaf,
  RefreshCw,
  ScanLine,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useAuth } from "@/stores/auth";
import { api } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ConfidenceBadge,
  SeverityBadge,
  SyncBadge,
  confidenceVariant,
} from "@/components/ui/status-badges";
import { StateCard } from "@/components/ui/state-card";
import type {
  Scan,
  ScanListParams,
  ScanOrder,
  ScanPartType,
  ScanSeverity,
  ScanSort,
  ScanSyncStatus,
} from "@/types/scan";

const PAGE_SIZE = 12;

const CONFIDENCE_STEPS = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1];

const SEVERITY_OPTIONS: ScanSeverity[] = ["low", "moderate", "severe"];
const SYNC_OPTIONS: ScanSyncStatus[] = ["synced", "pending", "failed"];
const PART_TYPE_OPTIONS: ScanPartType[] = [
  "leaf",
  "fruit",
  "stem",
  "plant",
  "whole",
];

interface HistoryFilters {
  search: string;
  cropId: number | null;
  disease: string;
  dateFrom: string;
  dateTo: string;
  confidenceMin: number | null;
  confidenceMax: number | null;
  severity: ScanSeverity | "";
  syncStatus: ScanSyncStatus | "";
  partType: ScanPartType | "";
}

const DEFAULT_FILTERS: HistoryFilters = {
  search: "",
  cropId: null,
  disease: "",
  dateFrom: "",
  dateTo: "",
  confidenceMin: null,
  confidenceMax: null,
  severity: "",
  syncStatus: "",
  partType: "",
};

function FilterField({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <Label
        htmlFor={htmlFor}
        className="text-xs font-semibold text-muted-foreground"
      >
        {label}
      </Label>
      {children}
    </div>
  );
}

function ScanCard({ scan, index }: { scan: Scan; index: number }) {
  const { t, i18n } = useTranslation();
  const previewUrl = scan.media_items[0]?.url;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.3,
        delay: Math.min(index * 0.045, 0.35),
      }}
      whileHover={{ y: -4 }}
      className="h-full"
    >
      <Link
        to={`/scans/${scan.id}`}
        className="group block h-full rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
      >
        <Card className="h-full overflow-hidden rounded-2xl border-border/70 bg-card transition-all duration-300 group-hover:border-emerald-300 group-hover:shadow-lg dark:group-hover:border-emerald-800">
          {previewUrl ? (
            <div className="relative aspect-[16/9] overflow-hidden bg-muted">
              <img
                src={previewUrl}
                alt={scan.disease_name}
                loading="lazy"
                className="size-full object-cover transition-transform duration-500 group-hover:scale-105"
                onError={(event) => {
                  event.currentTarget.style.display = "none";
                }}
              />
              <div className="absolute right-3 top-3">
                <ConfidenceBadge
                  value={scan.confidence}
                  hint={t("scanHistory.confidence")}
                />
              </div>
            </div>
          ) : (
            <div className="relative flex aspect-[16/9] items-center justify-center overflow-hidden bg-gradient-to-br from-emerald-50 via-green-100 to-teal-100 dark:from-emerald-950/60 dark:via-green-950/40 dark:to-teal-950/50">
              <div className="absolute -right-8 -top-12 size-40 rounded-full bg-white/30 blur-2xl" />
              <div className="absolute -bottom-12 -left-8 size-40 rounded-full bg-emerald-300/20 blur-2xl" />
              <Leaf className="relative size-14 text-emerald-700/60 dark:text-emerald-300/60" />
              <div className="absolute right-3 top-3">
                <ConfidenceBadge
                  value={scan.confidence}
                  hint={t("scanHistory.confidence")}
                />
              </div>
            </div>
          )}

          <CardContent className="flex h-full flex-col gap-3 p-4 sm:p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="line-clamp-2 font-bold leading-snug transition-colors group-hover:text-emerald-700 dark:group-hover:text-emerald-300">
                  {scan.disease_name}
                </h3>
                <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Clock3 className="size-3.5 shrink-0" />
                  {formatDate(scan.created_at, i18n.language)}
                </p>
              </div>
              <span className="shrink-0 rounded-lg bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
                #{scan.id}
              </span>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {scan.severity && (
                <SeverityBadge severity={scan.severity} />
              )}
              <SyncBadge status={scan.sync_status} />
              {scan.part_type && (
                <Badge variant="outline">
                  {t(`scanHistory.partType.${scan.part_type}`)}
                </Badge>
              )}
            </div>

            <div className="mt-auto flex items-center justify-between border-t pt-3">
              <span className="text-xs text-muted-foreground">
                {t("scanHistory.confidence")}
              </span>
              <span
                className={
                  confidenceVariant(scan.confidence) === "success"
                    ? "text-sm font-bold text-emerald-700 dark:text-emerald-300"
                    : confidenceVariant(scan.confidence) === "secondary"
                      ? "text-sm font-bold text-amber-700 dark:text-amber-300"
                      : "text-sm font-bold text-destructive"
                }
              >
                {scan.confidence === null
                  ? t("scanHistory.needsReview")
                  : formatPercent(scan.confidence)}
              </span>
            </div>
          </CardContent>
        </Card>
      </Link>
    </motion.div>
  );
}

function ScanGridSkeleton({ t }: { t: (key: string) => string }) {
  return (
    <div
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      role="status"
      aria-label={t("scanHistory.loadingScans")}
    >
      {Array.from({ length: 6 }).map((_, index) => (
        <Card key={index} className="overflow-hidden rounded-2xl">
          <CardContent className="flex flex-col gap-3 p-4">
            <Skeleton className="aspect-video w-full rounded-xl" />
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-7 w-1/2" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function ScanHistoryPage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const [filters, setFilters] = useState<HistoryFilters>(DEFAULT_FILTERS);
  const [searchInput, setSearchInput] = useState("");
  const [sort, setSort] = useState<ScanSort>("created_at");
  const [order, setOrder] = useState<ScanOrder>("desc");
  const [page, setPage] = useState(1);
  const [filtersOpen, setFiltersOpen] = useState(false);

  useEffect(() => {
    const id = window.setTimeout(() => {
      setFilters((current) =>
        current.search === searchInput
          ? current
          : { ...current, search: searchInput },
      );
      setPage(1);
    }, 300);

    return () => window.clearTimeout(id);
  }, [searchInput]);

  const patchFilters = (patch: Partial<HistoryFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters(DEFAULT_FILTERS);
    setSearchInput("");
    setPage(1);
  };

  const hasActiveFilters =
    filters.search !== "" ||
    filters.cropId !== null ||
    filters.disease !== "" ||
    filters.dateFrom !== "" ||
    filters.dateTo !== "" ||
    filters.confidenceMin !== null ||
    filters.confidenceMax !== null ||
    filters.severity !== "" ||
    filters.syncStatus !== "" ||
    filters.partType !== "";

  const activeFilterCount = [
    filters.cropId !== null,
    filters.disease !== "",
    filters.dateFrom !== "",
    filters.dateTo !== "",
    filters.confidenceMin !== null,
    filters.confidenceMax !== null,
    filters.severity !== "",
    filters.syncStatus !== "",
    filters.partType !== "",
  ].filter(Boolean).length;

  const buildParams = (): ScanListParams => {
    const params: ScanListParams = {
      page,
      page_size: PAGE_SIZE,
      sort,
      order,
    };

    if (filters.search) params.search = filters.search;
    if (filters.disease) params.disease = filters.disease;
    if (filters.cropId !== null) params.crop_id = filters.cropId;
    if (filters.partType) params.part_type = filters.partType;
    if (filters.severity) params.severity = filters.severity;
    if (filters.syncStatus) params.sync_status = filters.syncStatus;
    if (filters.dateFrom) {
      params.date_from = `${filters.dateFrom}T00:00:00`;
    }
    if (filters.dateTo) {
      params.date_to = `${filters.dateTo}T23:59:59`;
    }
    if (filters.confidenceMin !== null) {
      params.confidence_min = filters.confidenceMin;
    }
    if (filters.confidenceMax !== null) {
      params.confidence_max = filters.confidenceMax;
    }

    return params;
  };

  const scansQuery = useQuery({
    queryKey: ["scans", filters, sort, order, page],
    queryFn: () => api.listScans(buildParams()),
    enabled: !!user,
  });

  const cropsQuery = useQuery({
    queryKey: ["crops"],
    queryFn: () => api.listCrops(),
    staleTime: 5 * 60_000,
    enabled: !!user,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard
          icon={History}
          title={t("scanHistory.authRequired")}
        >
          <Button asChild>
            <Link to="/login">{t("scanHistory.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const data = scansQuery.data;
  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.page_size))
    : 1;

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50/50 via-background to-background dark:from-emerald-950/15">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-9">
        {/* Page heading */}
        <motion.header
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="mb-7 flex flex-col justify-between gap-5 sm:flex-row sm:items-end"
        >
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-300">
              <History className="size-3.5" />
              NeuroPlant AI
            </div>

            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              {t("scanHistory.title")}
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
              {t("scanHistory.subtitle")}
            </p>
          </div>

          <Button
            asChild
            className="w-full gap-2 bg-emerald-700 text-white hover:bg-emerald-800 sm:w-auto dark:bg-emerald-600 dark:hover:bg-emerald-700"
          >
            <Link to="/detect">
              <ScanLine className="size-4" />
              {t("scanHistory.scanNow")}
            </Link>
          </Button>
        </motion.header>

        {/* Overview */}
        <div className="mb-6 grid gap-3 sm:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
          >
            <Card className="overflow-hidden rounded-2xl border-emerald-100 bg-gradient-to-br from-white to-emerald-50 dark:border-emerald-900/50 dark:from-card dark:to-emerald-950/30">
              <CardContent className="flex items-center gap-4 p-5">
                <div className="flex size-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
                  <History className="size-6" />
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground">
                    {t("scanHistory.totalScans", {
                      count: data?.total ?? 0,
                    })}
                  </p>
                  <p className="mt-1 text-2xl font-bold tabular-nums">
                    {scansQuery.isPending ? "—" : data?.total ?? 0}
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="overflow-hidden rounded-2xl border-sky-100 bg-gradient-to-br from-white to-sky-50 dark:border-sky-900/50 dark:from-card dark:to-sky-950/30">
              <CardContent className="flex items-center gap-4 p-5">
                <div className="flex size-12 items-center justify-center rounded-2xl bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-300">
                  <CalendarDays className="size-6" />
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground">
                    {t("scanHistory.page", {
                      page,
                      pages: totalPages,
                    })}
                  </p>
                  <p className="mt-1 text-2xl font-bold tabular-nums">
                    {data?.items.length ?? 0}
                    <span className="ml-1 text-sm font-medium text-muted-foreground">
                      / {PAGE_SIZE}
                    </span>
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Search and sorting */}
        <Card className="mb-4 overflow-hidden rounded-2xl border-border/70 shadow-sm">
          <CardContent className="p-4 sm:p-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="h-11 rounded-xl pl-10"
                  type="search"
                  placeholder={t("scanHistory.searchPlaceholder")}
                  aria-label={t("scanHistory.searchPlaceholder")}
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                />
              </div>

              <div className="flex items-center gap-2">
                <Label htmlFor="scans-sort" className="sr-only">
                  {t("scanHistory.sort")}
                </Label>

                <Select
                  id="scans-sort"
                  className="h-11 min-w-0 flex-1 rounded-xl lg:w-48 lg:flex-none"
                  value={sort}
                  onChange={(event) => {
                    setSort(event.target.value as ScanSort);
                    setPage(1);
                  }}
                >
                  <option value="created_at">
                    {t("scanHistory.sortCreated")}
                  </option>
                  <option value="confidence">
                    {t("scanHistory.sortConfidence")}
                  </option>
                  <option value="disease_name">
                    {t("scanHistory.sortDisease")}
                  </option>
                </Select>

                <Button
                  variant="outline"
                  size="icon"
                  className="size-11 shrink-0 rounded-xl"
                  aria-label={
                    order === "asc"
                      ? t("scanHistory.orderAsc")
                      : t("scanHistory.orderDesc")
                  }
                  onClick={() => {
                    setOrder((current) =>
                      current === "asc" ? "desc" : "asc",
                    );
                    setPage(1);
                  }}
                >
                  {order === "asc" ? (
                    <ArrowUp className="size-4" />
                  ) : (
                    <ArrowDown className="size-4" />
                  )}
                </Button>

                <Button
                  type="button"
                  variant={filtersOpen ? "secondary" : "outline"}
                  className="h-11 shrink-0 gap-2 rounded-xl"
                  onClick={() => setFiltersOpen((open) => !open)}
                  aria-expanded={filtersOpen}
                >
                  <SlidersHorizontal className="size-4" />
                  <span className="hidden sm:inline">
                    {t("scanHistory.filterCrop")}
                  </span>
                  <Filter className="size-4 sm:hidden" />
                  {activeFilterCount > 0 && (
                    <span className="flex size-5 items-center justify-center rounded-full bg-emerald-700 text-[10px] font-bold text-white">
                      {activeFilterCount}
                    </span>
                  )}
                </Button>
              </div>
            </div>

            {/* Advanced filters */}
            <motion.div
              initial={false}
              animate={{
                height: filtersOpen ? "auto" : 0,
                opacity: filtersOpen ? 1 : 0,
              }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
              aria-hidden={!filtersOpen}
            >
              <div className="mt-5 border-t pt-5">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h2 className="text-sm font-semibold">
                      {t("scanHistory.filterCrop")}
                    </h2>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {t("scanHistory.subtitle")}
                    </p>
                  </div>

                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={!hasActiveFilters}
                    onClick={clearFilters}
                    className="gap-1.5"
                  >
                    <X className="size-3.5" />
                    {t("scanHistory.clear")}
                  </Button>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                  <FilterField
                    label={t("scanHistory.filterCrop")}
                    htmlFor="f-crop"
                  >
                    <Select
                      id="f-crop"
                      value={
                        filters.cropId === null
                          ? ""
                          : String(filters.cropId)
                      }
                      onChange={(event) =>
                        patchFilters({
                          cropId: event.target.value
                            ? Number(event.target.value)
                            : null,
                        })
                      }
                    >
                      <option value="">{t("scanHistory.all")}</option>
                      {(cropsQuery.data ?? []).map((crop) => (
                        <option key={crop.id} value={crop.id}>
                          {crop.name}
                        </option>
                      ))}
                    </Select>
                  </FilterField>

                  <FilterField
                    label={t("scanHistory.filterDisease")}
                    htmlFor="f-disease"
                  >
                    <Input
                      id="f-disease"
                      placeholder={t("scanHistory.filterDisease")}
                      value={filters.disease}
                      onChange={(event) =>
                        patchFilters({ disease: event.target.value })
                      }
                    />
                  </FilterField>

                  <FilterField
                    label={t("scanHistory.filterSeverity")}
                    htmlFor="f-severity"
                  >
                    <Select
                      id="f-severity"
                      value={filters.severity}
                      onChange={(event) =>
                        patchFilters({
                          severity: event.target.value as HistoryFilters["severity"],
                        })
                      }
                    >
                      <option value="">{t("scanHistory.all")}</option>
                      {SEVERITY_OPTIONS.map((severity) => (
                        <option key={severity} value={severity}>
                          {t(`scanHistory.severity.${severity}`)}
                        </option>
                      ))}
                    </Select>
                  </FilterField>

                  <FilterField
                    label={t("scanHistory.filterSync")}
                    htmlFor="f-sync"
                  >
                    <Select
                      id="f-sync"
                      value={filters.syncStatus}
                      onChange={(event) =>
                        patchFilters({
                          syncStatus: event.target.value as HistoryFilters["syncStatus"],
                        })
                      }
                    >
                      <option value="">{t("scanHistory.all")}</option>
                      {SYNC_OPTIONS.map((syncStatus) => (
                        <option key={syncStatus} value={syncStatus}>
                          {t(`scanHistory.sync.${syncStatus}`)}
                        </option>
                      ))}
                    </Select>
                  </FilterField>

                  <FilterField
                    label={t("scanHistory.filterPartType")}
                    htmlFor="f-part"
                  >
                    <Select
                      id="f-part"
                      value={filters.partType}
                      onChange={(event) =>
                        patchFilters({
                          partType: event.target.value as HistoryFilters["partType"],
                        })
                      }
                    >
                      <option value="">{t("scanHistory.all")}</option>
                      {PART_TYPE_OPTIONS.map((partType) => (
                        <option key={partType} value={partType}>
                          {t(`scanHistory.partType.${partType}`)}
                        </option>
                      ))}
                    </Select>
                  </FilterField>

                  <FilterField
                    label={t("scanHistory.filterDateFrom")}
                    htmlFor="f-date-from"
                  >
                    <Input
                      id="f-date-from"
                      type="date"
                      value={filters.dateFrom}
                      onChange={(event) =>
                        patchFilters({ dateFrom: event.target.value })
                      }
                    />
                  </FilterField>

                  <FilterField
                    label={t("scanHistory.filterDateTo")}
                    htmlFor="f-date-to"
                  >
                    <Input
                      id="f-date-to"
                      type="date"
                      value={filters.dateTo}
                      onChange={(event) =>
                        patchFilters({ dateTo: event.target.value })
                      }
                    />
                  </FilterField>

                  <FilterField
                    label={t("scanHistory.filterConfidenceMin")}
                    htmlFor="f-conf-min"
                  >
                    <Select
                      id="f-conf-min"
                      value={
                        filters.confidenceMin === null
                          ? ""
                          : String(filters.confidenceMin)
                      }
                      onChange={(event) =>
                        patchFilters({
                          confidenceMin: event.target.value
                            ? Number(event.target.value)
                            : null,
                        })
                      }
                    >
                      <option value="">{t("scanHistory.all")}</option>
                      {CONFIDENCE_STEPS.map((step) => (
                        <option key={step} value={step}>
                          {formatPercent(step)}
                        </option>
                      ))}
                    </Select>
                  </FilterField>

                  <FilterField
                    label={t("scanHistory.filterConfidenceMax")}
                    htmlFor="f-conf-max"
                  >
                    <Select
                      id="f-conf-max"
                      value={
                        filters.confidenceMax === null
                          ? ""
                          : String(filters.confidenceMax)
                      }
                      onChange={(event) =>
                        patchFilters({
                          confidenceMax: event.target.value
                            ? Number(event.target.value)
                            : null,
                        })
                      }
                    >
                      <option value="">{t("scanHistory.all")}</option>
                      {CONFIDENCE_STEPS.map((step) => (
                        <option key={step} value={step}>
                          {formatPercent(step)}
                        </option>
                      ))}
                    </Select>
                  </FilterField>
                </div>
              </div>
            </motion.div>
          </CardContent>
        </Card>

        {/* Results heading */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold">
              {t("scanHistory.title")}
            </h2>
            {data && (
              <p className="mt-1 text-sm text-muted-foreground">
                {t("scanHistory.totalScans", { count: data.total })}
              </p>
            )}
          </div>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="gap-2 text-muted-foreground"
            onClick={() => void scansQuery.refetch()}
            disabled={scansQuery.isFetching}
          >
            <RefreshCw
              className={`size-4 ${scansQuery.isFetching ? "animate-spin" : ""}`}
            />
            {t("common.retry")}
          </Button>
        </div>

        {/* Results */}
        <div>
          {scansQuery.isPending ? (
            <ScanGridSkeleton t={t} />
          ) : scansQuery.isError ? (
            <StateCard
              icon={AlertCircle}
              title={t("scanHistory.errorTitle")}
              body={t("scanHistory.errorBody")}
              tone="destructive"
            >
              <Button
                variant="outline"
                onClick={() => void scansQuery.refetch()}
              >
                <RefreshCw className="mr-2 size-4" />
                {t("common.retry")}
              </Button>
            </StateCard>
          ) : !data || data.items.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <StateCard
                icon={ScanLine}
                title={t("scanHistory.emptyTitle")}
                body={t("scanHistory.emptyBody")}
              >
                <div className="flex flex-wrap justify-center gap-2">
                  {hasActiveFilters && (
                    <Button
                      variant="outline"
                      onClick={clearFilters}
                    >
                      <X className="mr-2 size-4" />
                      {t("scanHistory.clear")}
                    </Button>
                  )}
                  <Button asChild>
                    <Link to="/detect">
                      <ScanLine className="mr-2 size-4" />
                      {t("scanHistory.scanNow")}
                    </Link>
                  </Button>
                </div>
              </StateCard>
            </motion.div>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {data.items.map((scan, index) => (
                  <ScanCard
                    key={scan.id}
                    scan={scan}
                    index={index}
                  />
                ))}
              </div>

              {/* Pagination */}
              <nav
                className="mt-7 flex items-center justify-between gap-3 rounded-2xl border bg-card p-3 sm:p-4"
                aria-label={t("scanHistory.pagination")}
              >
                <Button
                  variant="outline"
                  size="sm"
                  className="h-10 gap-1.5 rounded-xl"
                  disabled={page <= 1 || scansQuery.isFetching}
                  onClick={() => setPage((current) => current - 1)}
                >
                  <ChevronLeft className="size-4" />
                  <span className="hidden sm:inline">
                    {t("scanHistory.prev")}
                  </span>
                </Button>

                <div className="text-center">
                  <p className="text-sm font-semibold">
                    {t("scanHistory.page", {
                      page,
                      pages: totalPages,
                    })}
                  </p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    {data.total} records
                  </p>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="h-10 gap-1.5 rounded-xl"
                  disabled={!data.has_next || scansQuery.isFetching}
                  onClick={() => setPage((current) => current + 1)}
                >
                  <span className="hidden sm:inline">
                    {t("scanHistory.next")}
                  </span>
                  <ChevronRight className="size-4" />
                </Button>
              </nav>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
