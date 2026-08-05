import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  History,
  RefreshCw,
  ScanLine,
  Search,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useAuth } from "@/stores/auth";
import { api } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
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

/** Confidence cutoffs that select the badge color (mirrors backend bands). */
const CONFIDENCE_HIGH = 0.85;
const CONFIDENCE_MEDIUM = 0.6;

const CONFIDENCE_STEPS = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1];

const SEVERITY_OPTIONS: ScanSeverity[] = ["low", "moderate", "severe"];
const SYNC_OPTIONS: ScanSyncStatus[] = ["synced", "pending", "failed"];
const PART_TYPE_OPTIONS: ScanPartType[] = ["leaf", "fruit", "stem", "plant", "whole"];

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

function confidenceVariant(confidence: number): "success" | "secondary" | "destructive" {
  if (confidence >= CONFIDENCE_HIGH) return "success";
  if (confidence >= CONFIDENCE_MEDIUM) return "secondary";
  return "destructive";
}

function severityVariant(severity: ScanSeverity): "success" | "secondary" | "destructive" {
  if (severity === "low") return "success";
  if (severity === "moderate") return "secondary";
  return "destructive";
}

function syncVariant(status: ScanSyncStatus): "success" | "outline" | "destructive" {
  if (status === "synced") return "success";
  if (status === "pending") return "outline";
  return "destructive";
}

/** One scan row — links to the detail page. */
function ScanCard({ scan }: { scan: Scan }) {
  const { t, i18n } = useTranslation();
  const previewUrl = scan.media_items[0]?.url;

  return (
    <Link to={`/scans/${scan.id}`} className="group block h-full">
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardContent className="flex h-full flex-col gap-3 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate font-semibold group-hover:text-brand-600 dark:group-hover:text-brand-400">
                {scan.disease_name}
              </h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {formatDate(scan.created_at, i18n.language)}
              </p>
            </div>
            <Badge variant={confidenceVariant(scan.confidence)} title={t("scanHistory.confidence")}>
              {formatPercent(scan.confidence)}
            </Badge>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {scan.severity && (
              <Badge variant={severityVariant(scan.severity)}>
                {t(`scanHistory.severity.${scan.severity}`)}
              </Badge>
            )}
            <Badge variant={syncVariant(scan.sync_status)}>
              {t(`scanHistory.sync.${scan.sync_status}`)}
            </Badge>
            {scan.part_type && (
              <Badge variant="outline">{t(`scanHistory.partType.${scan.part_type}`)}</Badge>
            )}
          </div>

          {/* Media URLs are not mounted until M11; broken images hide gracefully. */}
          {previewUrl && (
            <img
              src={previewUrl}
              alt=""
              loading="lazy"
              className="mt-auto aspect-video w-full rounded-md border object-cover"
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          )}
        </CardContent>
      </Card>
    </Link>
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
        <Card key={index}>
          <CardContent className="flex flex-col gap-3 p-4">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-24 w-full" />
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

  // Debounce the free-text search so keystrokes don't fire a request each one.
  useEffect(() => {
    const id = window.setTimeout(() => {
      setFilters((current) => (current.search === searchInput ? current : { ...current, search: searchInput }));
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

  const buildParams = (): ScanListParams => {
    const params: ScanListParams = { page, page_size: PAGE_SIZE, sort, order };
    if (filters.search) params.search = filters.search;
    if (filters.disease) params.disease = filters.disease;
    if (filters.cropId !== null) params.crop_id = filters.cropId;
    if (filters.partType) params.part_type = filters.partType;
    if (filters.severity) params.severity = filters.severity;
    if (filters.syncStatus) params.sync_status = filters.syncStatus;
    if (filters.dateFrom) params.date_from = `${filters.dateFrom}T00:00:00`;
    if (filters.dateTo) params.date_to = `${filters.dateTo}T23:59:59`;
    if (filters.confidenceMin !== null) params.confidence_min = filters.confidenceMin;
    if (filters.confidenceMax !== null) params.confidence_max = filters.confidenceMax;
    return params;
  };

  // Queries are gated on auth — a logged-out visitor never fires an API call.
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
        <Card>
          <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
            <History className="size-10 text-muted-foreground" />
            <p className="text-muted-foreground">{t("scanHistory.authRequired")}</p>
            <Button asChild>
              <Link to="/login">{t("scanHistory.signIn")}</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const data = scansQuery.data;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{t("scanHistory.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("scanHistory.subtitle")}</p>
      </header>

      {/* ── Search / sort / filters ──────────────────────────────────── */}
      <Card className="mt-6">
        <CardContent className="p-4 sm:p-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
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
                className="w-full lg:w-44"
                value={sort}
                onChange={(event) => {
                  setSort(event.target.value as ScanSort);
                  setPage(1);
                }}
              >
                <option value="created_at">{t("scanHistory.sortCreated")}</option>
                <option value="confidence">{t("scanHistory.sortConfidence")}</option>
                <option value="disease_name">{t("scanHistory.sortDisease")}</option>
              </Select>
              <Button
                variant="outline"
                size="icon"
                className="shrink-0"
                aria-label={order === "asc" ? t("scanHistory.orderAsc") : t("scanHistory.orderDesc")}
                onClick={() => {
                  setOrder((current) => (current === "asc" ? "desc" : "asc"));
                  setPage(1);
                }}
              >
                {order === "asc" ? <ArrowUp /> : <ArrowDown />}
              </Button>
            </div>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-crop" className="text-xs font-medium text-muted-foreground">
                {t("scanHistory.filterCrop")}
              </Label>
              <Select
                id="f-crop"
                value={filters.cropId === null ? "" : String(filters.cropId)}
                onChange={(event) =>
                  patchFilters({ cropId: event.target.value ? Number(event.target.value) : null })
                }
              >
                <option value="">{t("scanHistory.all")}</option>
                {(cropsQuery.data ?? []).map((crop) => (
                  <option key={crop.id} value={crop.id}>
                    {crop.name}
                  </option>
                ))}
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-disease" className="text-xs font-medium text-muted-foreground">
                {t("scanHistory.filterDisease")}
              </Label>
              <Input
                id="f-disease"
                placeholder={t("scanHistory.filterDisease")}
                value={filters.disease}
                onChange={(event) => patchFilters({ disease: event.target.value })}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-severity" className="text-xs font-medium text-muted-foreground">
                {t("scanHistory.filterSeverity")}
              </Label>
              <Select
                id="f-severity"
                value={filters.severity}
                onChange={(event) => patchFilters({ severity: event.target.value as HistoryFilters["severity"] })}
              >
                <option value="">{t("scanHistory.all")}</option>
                {SEVERITY_OPTIONS.map((severity) => (
                  <option key={severity} value={severity}>
                    {t(`scanHistory.severity.${severity}`)}
                  </option>
                ))}
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-sync" className="text-xs font-medium text-muted-foreground">
                {t("scanHistory.filterSync")}
              </Label>
              <Select
                id="f-sync"
                value={filters.syncStatus}
                onChange={(event) =>
                  patchFilters({ syncStatus: event.target.value as HistoryFilters["syncStatus"] })
                }
              >
                <option value="">{t("scanHistory.all")}</option>
                {SYNC_OPTIONS.map((syncStatus) => (
                  <option key={syncStatus} value={syncStatus}>
                    {t(`scanHistory.sync.${syncStatus}`)}
                  </option>
                ))}
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-part" className="text-xs font-medium text-muted-foreground">
                {t("scanHistory.filterPartType")}
              </Label>
              <Select
                id="f-part"
                value={filters.partType}
                onChange={(event) =>
                  patchFilters({ partType: event.target.value as HistoryFilters["partType"] })
                }
              >
                <option value="">{t("scanHistory.all")}</option>
                {PART_TYPE_OPTIONS.map((partType) => (
                  <option key={partType} value={partType}>
                    {t(`scanHistory.partType.${partType}`)}
                  </option>
                ))}
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-date-from" className="text-xs font-medium text-muted-foreground">
                {t("scanHistory.filterDateFrom")}
              </Label>
              <Input
                id="f-date-from"
                type="date"
                value={filters.dateFrom}
                onChange={(event) => patchFilters({ dateFrom: event.target.value })}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-date-to" className="text-xs font-medium text-muted-foreground">
                {t("scanHistory.filterDateTo")}
              </Label>
              <Input
                id="f-date-to"
                type="date"
                value={filters.dateTo}
                onChange={(event) => patchFilters({ dateTo: event.target.value })}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-conf-min" className="text-xs font-medium text-muted-foreground">
                {t("scanHistory.filterConfidenceMin")}
              </Label>
              <Select
                id="f-conf-min"
                value={filters.confidenceMin === null ? "" : String(filters.confidenceMin)}
                onChange={(event) =>
                  patchFilters({
                    confidenceMin: event.target.value ? Number(event.target.value) : null,
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
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="f-conf-max" className="text-xs font-medium text-muted-foreground">
                {t("scanHistory.filterConfidenceMax")}
              </Label>
              <Select
                id="f-conf-max"
                value={filters.confidenceMax === null ? "" : String(filters.confidenceMax)}
                onChange={(event) =>
                  patchFilters({
                    confidenceMax: event.target.value ? Number(event.target.value) : null,
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
            </div>

            <div className="flex items-end">
              <Button
                variant="ghost"
                size="sm"
                className="w-full"
                disabled={!hasActiveFilters}
                onClick={clearFilters}
              >
                <X />
                {t("scanHistory.clear")}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Results ──────────────────────────────────────────────────── */}
      <div className="mt-6">
        {scansQuery.isPending ? (
          <ScanGridSkeleton t={t} />
        ) : scansQuery.isError ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
              <AlertCircle className="size-10 text-destructive" />
              <h3 className="text-lg font-semibold">{t("scanHistory.errorTitle")}</h3>
              <p className="text-muted-foreground">{t("scanHistory.errorBody")}</p>
              <Button variant="outline" onClick={() => void scansQuery.refetch()}>
                <RefreshCw />
                {t("common.retry")}
              </Button>
            </CardContent>
          </Card>
        ) : !data || data.items.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
              <ScanLine className="size-10 text-muted-foreground" />
              <h3 className="text-lg font-semibold">{t("scanHistory.emptyTitle")}</h3>
              <p className="text-muted-foreground">{t("scanHistory.emptyBody")}</p>
              <Button asChild>
                <Link to="/detect">
                  <ScanLine />
                  {t("scanHistory.scanNow")}
                </Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            <p className="mb-3 text-sm text-muted-foreground">
              {t("scanHistory.totalScans", { count: data.total })}
            </p>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((scan) => (
                <ScanCard key={scan.id} scan={scan} />
              ))}
            </div>

            <nav
              className="mt-6 flex items-center justify-between gap-3"
              aria-label={t("scanHistory.pagination")}
            >
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft />
                {t("scanHistory.prev")}
              </Button>
              <p className="text-sm text-muted-foreground">
                {t("scanHistory.page", { page, pages: totalPages })}
              </p>
              <Button
                variant="outline"
                size="sm"
                disabled={!data.has_next}
                onClick={() => setPage((p) => p + 1)}
              >
                {t("scanHistory.next")}
                <ChevronRight />
              </Button>
            </nav>
          </>
        )}
      </div>
    </div>
  );
}
