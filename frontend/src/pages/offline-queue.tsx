import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  CloudUpload,
  History,
  ImageOff,
  RotateCcw,
  ScanLine,
  Trash2,
  Wifi,
  WifiOff,
  X,
  XCircle,
} from "lucide-react";
import { motion } from "motion/react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import {
  clearCompletedSyncs,
  completedSyncs,
  pendingSync,
  removeCompletedSync,
  removeSync,
  type CompletedSync,
  type SyncEntry,
} from "@/offline/db";
import { useNetwork } from "@/offline/network";
import {
  CONFLICT_CODE,
  SCAN_SYNC_TYPE,
  type ScanSyncPayload,
} from "@/offline/scan-sync";
import { processSyncQueue, replayEntry } from "@/offline/sync";
import { useSyncUi } from "@/offline/sync-store";
import { useAuth } from "@/stores/auth";

/** Derive a queue entry's visible status from its attempts + drain state. */
function entryStatus(
  entry: SyncEntry,
  syncing: boolean,
): "pending" | "syncing" | "failed" {
  if (syncing) return "syncing";
  if (entry.attempts >= 1) return "failed";
  return "pending";
}

const STATUS_VARIANT = {
  pending: "secondary",
  syncing: "outline",
  synced: "success",
  failed: "destructive",
} as const;

function StatusBadge({ status }: { status: keyof typeof STATUS_VARIANT }) {
  const { t } = useTranslation();
  return <Badge variant={STATUS_VARIANT[status]}>{t(`offlineQueue.status.${status}`)}</Badge>;
}

/** One queued scan: thumbnail, crop, timestamp, status, retry count, actions. */
function EntryCard({
  entry,
  syncing,
  cropName,
  index,
  onRetry,
  onCancel,
}: {
  entry: SyncEntry;
  syncing: boolean;
  cropName: string;
  index: number;
  onRetry: (id: number) => void;
  onCancel: (id: number) => void;
}) {
  const { t, i18n } = useTranslation();
  const payload = entry.payload as ScanSyncPayload | undefined;
  const image = payload?.images?.[0];
  const thumbnail = image
    ? `data:${image.content_type};base64,${image.data}`
    : null;
  const isConflict = entry.lastError?.includes(CONFLICT_CODE) ?? false;
  const status = entryStatus(entry, syncing);

  return (
    <motion.li
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.2 }}
      className="flex gap-3 rounded-lg border border-border bg-card p-3"
    >
      {thumbnail ? (
        <img
          src={thumbnail}
          alt={t("offlineQueue.thumbnailAlt")}
          className="size-16 shrink-0 rounded-md border object-cover"
        />
      ) : (
        <div className="flex size-16 shrink-0 items-center justify-center rounded-md border bg-muted/40 text-muted-foreground">
          <ImageOff className="size-6" />
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{cropName}</p>
            <p className="text-xs text-muted-foreground">
              {formatDate(new Date(entry.createdAt).toISOString(), i18n.language)}
            </p>
          </div>
          <StatusBadge status={status} />
        </div>

        {status === "failed" && (
          <div
            className={
              isConflict
                ? "flex items-start gap-1.5 rounded-md border border-amber-300 bg-amber-50 px-2 py-1.5 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
                : "flex items-start gap-1.5 rounded-md bg-muted/60 px-2 py-1.5 text-xs text-muted-foreground"
            }
          >
            {isConflict ? <AlertTriangle className="mt-0.5 size-3.5 shrink-0" /> : <XCircle className="mt-0.5 size-3.5 shrink-0" />}
            <span>
              {isConflict ? t("offlineQueue.conflict") : t("offlineQueue.lastError", { message: entry.lastError })}
            </span>
          </div>
        )}

        <div className="mt-1 flex flex-wrap items-center gap-2">
          {entry.attempts >= 1 && (
            <span
              className="text-xs text-muted-foreground"
              aria-label={t("offlineQueue.retryCount", { count: entry.attempts })}
            >
              {t("offlineQueue.retryCount", { count: entry.attempts })}
            </span>
          )}
          <div className="ml-auto flex gap-1.5">
            {status === "failed" && !syncing && (
              <Button variant="outline" size="sm" onClick={() => onRetry(entry.id!)}>
                <RotateCcw />
                {t("offlineQueue.retry")}
              </Button>
            )}
            {!syncing && (
              <Button
                variant="ghost"
                size="icon"
                aria-label={t("offlineQueue.cancelAria")}
                onClick={() => onCancel(entry.id!)}
              >
                <X />
              </Button>
            )}
          </div>
        </div>
      </div>
    </motion.li>
  );
}

/** A record from the recently-synced list. */
function CompletedRow({
  record,
  index,
  onRemove,
}: {
  record: CompletedSync;
  index: number;
  onRemove: (id: number) => void;
}) {
  const { t, i18n } = useTranslation();
  return (
    <motion.li
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, duration: 0.2 }}
      className="flex items-center gap-3 rounded-lg border border-border bg-card p-3"
    >
      <CheckCircle2 className="size-5 shrink-0 text-brand-600" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{record.diseaseName || t("offlineQueue.notSet")}</p>
        <p className="text-xs text-muted-foreground">
          {formatDate(new Date(record.syncedAt).toISOString(), i18n.language)}
        </p>
      </div>
      <Badge variant="success">{t("offlineQueue.status.synced")}</Badge>
      <Button
        variant="ghost"
        size="icon"
        aria-label={t("offlineQueue.removeAria")}
        onClick={() => onRemove(record.id!)}
      >
        <Trash2 />
      </Button>
    </motion.li>
  );
}

export function OfflineQueuePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isOnline = useNetwork((state) => state.isOnline);
  const syncUi = useSyncUi();
  const queryClient = useQueryClient();

  // Pending + recently-synced scans come from IndexedDB; the query owns the
  // loading / error states and is refetched after every mutation.
  const queueQuery = useQuery({
    queryKey: ["offline-queue"],
    queryFn: async () => {
      const [pending, done] = await Promise.all([pendingSync(), completedSyncs()]);
      return {
        entries: pending.filter((entry) => entry.type === SCAN_SYNC_TYPE),
        completed: done,
      };
    },
    enabled: !!user,
  });
  const entries = queueQuery.data?.entries ?? [];
  const completed = queueQuery.data?.completed ?? [];

  const cropsQuery = useQuery({
    queryKey: ["crops"],
    queryFn: () => api.listCrops(),
    enabled: !!user,
    staleTime: 5 * 60_000,
  });

  // Reload when connectivity changes (the auto-drain loop may have flushed the
  // queue) or any drain reports an outcome, including ones this screen didn't
  // start itself. Invalidating (rather than refetching here) keeps the loading
  // skeleton from flashing on every drain tick.
  useEffect(() => {
    void queryClient.invalidateQueries({ queryKey: ["offline-queue"] });
  }, [queryClient, isOnline, syncUi.version]);

  const cropName = (cropId: number | null | undefined): string => {
    if (cropId == null) return t("offlineQueue.notSet");
    return cropsQuery.data?.find((crop) => crop.id === cropId)?.name ?? String(cropId);
  };

  const syncAll = async () => {
    if (!isOnline || syncUi.active || entries.length === 0) return;
    useSyncUi.getState().begin(entries.length);
    try {
      await processSyncQueue(() => useSyncUi.getState().tick());
    } finally {
      useSyncUi.getState().finish();
    }
    await queueQuery.refetch();
  };

  const retry = async (id: number) => {
    if (!isOnline || syncUi.active) return;
    useSyncUi.getState().begin(1);
    try {
      await replayEntry(id);
    } finally {
      useSyncUi.getState().finish();
    }
    await queueQuery.refetch();
  };

  const cancel = async (id: number) => {
    await removeSync(id);
    await queueQuery.refetch();
  };

  const removeCompleted = async (id: number) => {
    await removeCompletedSync(id);
    await queueQuery.refetch();
  };

  const clearCompleted = async () => {
    await clearCompletedSyncs();
    await queueQuery.refetch();
  };

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <Card>
          <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
            <History className="size-10 text-muted-foreground" />
            <p className="text-muted-foreground">{t("offlineQueue.authRequired")}</p>
            <Button asChild>
              <Link to="/login">{t("offlineQueue.signIn")}</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const percent =
    syncUi.total > 0 ? Math.round((syncUi.done / syncUi.total) * 100) : 0;
  const syncedTotal = syncUi.created + syncUi.replayed;
  const showResult = !syncUi.active && syncedTotal + syncUi.failed > 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            {t("offlineQueue.title")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("offlineQueue.subtitle")}</p>
        </div>
        <Button
          onClick={() => void syncAll()}
          disabled={!isOnline || syncUi.active || entries.length === 0}
        >
          <CloudUpload />
          {t("offlineQueue.syncAll")}
        </Button>
      </header>

      {/* ── Network banner ─────────────────────────────────────────── */}
      {isOnline ? (
        <div
          role="status"
          className="mt-4 flex items-center gap-2 rounded-md border border-brand-200 bg-brand-50 px-3 py-2 text-sm text-brand-800 dark:border-brand-800 dark:bg-brand-950/40 dark:text-brand-200"
        >
          <Wifi className="size-4 shrink-0" />
          {t("offlineQueue.onlineBanner")}
        </div>
      ) : (
        <div
          role="status"
          className="mt-4 flex items-center gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
        >
          <WifiOff className="size-4 shrink-0" />
          {t("offlineQueue.offlineBanner")}
        </div>
      )}

      {/* ── In-flight progress + last result ───────────────────────── */}
      <div aria-live="polite">
        {syncUi.active && (
          <div
            className="mt-4 rounded-md border border-border bg-card p-4"
            role="status"
            aria-label={t("offlineQueue.progressLabel", { done: syncUi.done, total: syncUi.total })}
          >
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="flex items-center gap-2 font-medium">
                <ScanLine className="size-4 animate-pulse text-brand-600" />
                {t("offlineQueue.syncing")}
              </span>
              <span className="text-muted-foreground">
                {syncUi.done} / {syncUi.total}
              </span>
            </div>
            <div
              className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted"
              role="progressbar"
              aria-valuenow={syncUi.done}
              aria-valuemin={0}
              aria-valuemax={syncUi.total}
            >
              <div
                className="h-full rounded-full bg-brand-500 transition-all duration-300"
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>
        )}

        {showResult && (
          <div
            role="status"
            className={`mt-4 flex items-start gap-2 rounded-md border px-3 py-2.5 text-sm ${
              syncUi.failed > 0
                ? "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
                : "border-brand-200 bg-brand-50 text-brand-800 dark:border-brand-800 dark:bg-brand-950/40 dark:text-brand-200"
            }`}
          >
            {syncUi.failed > 0 ? (
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            ) : (
              <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
            )}
            <div>
              <p className="font-medium">
                {t("offlineQueue.syncSummary", {
                  created: syncUi.created,
                  replayed: syncUi.replayed,
                  failed: syncUi.failed,
                })}
              </p>
              {syncUi.failed > 0 && syncUi.lastError && (
                <p className="mt-0.5 text-xs opacity-90">
                  {t("offlineQueue.lastError", { message: syncUi.lastError })}
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Content ────────────────────────────────────────────────── */}
      {queueQuery.isPending ? (
        <div className="mt-6 flex flex-col gap-3" role="status" aria-label={t("offlineQueue.loading")}>
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : queueQuery.isError ? (
        <Card className="mt-6">
          <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
            <AlertTriangle className="size-10 text-muted-foreground" />
            <h3 className="text-lg font-semibold">{t("offlineQueue.errorTitle")}</h3>
            <p className="text-sm text-muted-foreground">{t("offlineQueue.errorBody")}</p>
            <Button variant="outline" onClick={() => void queueQuery.refetch()}>
              {t("offlineQueue.retry")}
            </Button>
          </CardContent>
        </Card>
      ) : entries.length === 0 && completed.length === 0 ? (
        <Card className="mt-6">
          <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
            <CloudUpload className="size-10 text-muted-foreground" />
            <h3 className="text-lg font-semibold">{t("offlineQueue.emptyTitle")}</h3>
            <p className="text-sm text-muted-foreground">{t("offlineQueue.emptyBody")}</p>
            <Button asChild>
              <Link to="/detect">{t("offlineQueue.scanNow")}</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="mt-6 flex flex-col gap-6">
          {entries.length > 0 && (
            <section aria-labelledby="offline-pending-title">
              <div className="flex items-center justify-between gap-3">
                <h2
                  id="offline-pending-title"
                  className="text-lg font-semibold"
                >
                  {t("offlineQueue.pendingSection")}
                </h2>
                <span className="text-sm text-muted-foreground">
                  {t("offlineQueue.pendingCount", { count: entries.length })}
                </span>
              </div>
              <ul
                className="mt-3 flex flex-col gap-3"
                aria-busy={syncUi.active}
              >
                {entries.map((entry, index) => (
                  <EntryCard
                    key={entry.id}
                    entry={entry}
                    syncing={syncUi.active}
                    cropName={cropName((entry.payload as ScanSyncPayload)?.crop_id)}
                    index={index}
                    onRetry={(id) => void retry(id)}
                    onCancel={(id) => void cancel(id)}
                  />
                ))}
              </ul>
            </section>
          )}

          {completed.length > 0 && (
            <section aria-labelledby="offline-completed-title">
              <div className="flex items-center justify-between gap-3">
                <h2 id="offline-completed-title" className="text-lg font-semibold">
                  {t("offlineQueue.completedSection")}
                </h2>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void clearCompleted()}
                  disabled={syncUi.active}
                >
                  <Trash2 />
                  {t("offlineQueue.clearCompleted")}
                </Button>
              </div>
              <ul className="mt-3 flex flex-col gap-3">
                {completed.map((record, index) => (
                  <CompletedRow
                    key={record.id}
                    record={record}
                    index={index}
                    onRemove={(id) => void removeCompleted(id)}
                  />
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
