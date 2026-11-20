import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CalendarDays, Check, Plus, Sprout, Trash2, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { SpeakButton } from "@/components/assistant/speak-button";
import { describeRecovery } from "@/components/assistant/describe";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/format";
import type { RecoveryLog, RecoveryLogInput, RecoveryProgress, RecoveryTracker } from "@/types/recovery";

// Status badge/track colors (full class strings so Tailwind keeps them).
const RECOVERY_STYLES: Record<string, { badge: string; track: string }> = {
  at_risk: {
    badge: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    track: "bg-red-500",
  },
  on_track: {
    badge: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    track: "bg-amber-500",
  },
  improving: {
    badge: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
    track: "bg-green-500",
  },
  recovered: {
    badge: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    track: "bg-emerald-500",
  },
};

const PROGRESS_STYLES: Record<string, string> = {
  worsening: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  "no-change": "bg-muted text-muted-foreground",
  improving: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  recovered: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
};

const RECOVERY_PROGRESS_OPTIONS: RecoveryProgress[] = [
  "worsening",
  "no-change",
  "improving",
  "recovered",
];

const QUERY_KEY = (scanId: number) => ["scan-recovery", scanId] as const;

// ── Panel: fetch + loading / error states ────────────────────────────────

/**
 * Owns the `GET /scans/{id}/recovery` query and renders its three states
 * (loading skeleton, error with retry, or the full tracker). A tracker always
 * exists for an owned scan (its timeline may simply be empty), so a 404 is a
 * genuine error rather than an empty state.
 */
export function RecoveryTrackerPanel({
  scanId,
  className,
}: {
  scanId: number;
  className?: string;
}) {
  const { t } = useTranslation();
  const query = useQuery({
    queryKey: QUERY_KEY(scanId),
    queryFn: () => api.getScanRecoveryTracker(scanId),
    retry: false,
  });

  if (query.isPending) {
    return (
      <div
        role="status"
        aria-label={t("recovery.loading")}
        className={cn("flex flex-col gap-4", className)}
      >
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (query.isError) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center gap-3 p-6 text-center">
          <AlertCircle className="size-8 text-destructive" aria-hidden="true" />
          <p className="font-medium">{t("recovery.errorTitle")}</p>
          <p className="text-sm text-muted-foreground">{t("recovery.errorBody")}</p>
          <Button variant="outline" size="sm" onClick={() => void query.refetch()}>
            {t("recovery.retry")}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!query.data) return null;
  return <RecoveryTrackerView tracker={query.data} scanId={scanId} className={className} />;
}

// ── Full tracker: progress header + timeline + form ──────────────────────

export function RecoveryTrackerView({
  tracker,
  scanId,
  className,
}: {
  tracker: RecoveryTracker;
  scanId: number;
  className?: string;
}) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<RecoveryLog | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState<number | null>(null);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: QUERY_KEY(scanId) });

  const addMutation = useMutation({
    mutationFn: (payload: RecoveryLogInput) => api.addRecoveryLog(scanId, payload),
    onSuccess: () => invalidate(),
  });
  const updateMutation = useMutation({
    mutationFn: ({ logId, payload }: { logId: number; payload: Partial<RecoveryLogInput> }) =>
      api.updateRecoveryLog(scanId, logId, payload),
    onSuccess: () => invalidate(),
  });
  const deleteMutation = useMutation({
    mutationFn: (logId: number) => api.deleteRecoveryLog(scanId, logId),
    onSuccess: () => invalidate(),
  });

  const styles = RECOVERY_STYLES[tracker.status] ?? RECOVERY_STYLES.on_track;
  const statusLabel = t(`recovery.statusLevel.${tracker.status}`, {
    defaultValue: tracker.status,
  });
  const percent = Math.min(100, Math.round(tracker.recovery_percentage * 100));

  const handleSubmit = (payload: RecoveryLogInput) => {
    if (editing) {
      updateMutation.mutate({ logId: editing.id, payload });
    } else {
      addMutation.mutate(payload);
    }
    setEditing(null);
  };

  return (
    <section className={cn("flex flex-col gap-4", className)} aria-label={t("recovery.title")}>
      {/* Progress header */}
      <Card>
        <CardContent className="p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
                {t("recovery.title")}
              </p>
              <h3 className="mt-1 text-xl font-bold tracking-tight">{t("recovery.subtitle")}</h3>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <SpeakButton text={describeRecovery(tracker)} />
              <Badge className={cn("text-xs", styles.badge)}>{statusLabel}</Badge>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/40 p-3.5">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                <Sprout className="size-4" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold">{t("recovery.progress")}</p>
                <p className="text-xs text-muted-foreground">
                  {t("recovery.timeline")}: {tracker.total_treatments}
                </p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span className="text-2xl font-bold tabular-nums">{percent}%</span>
            </div>
            <div
              className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
              aria-label={t("recovery.percentage")}
            >
              <div
                className={cn("h-full rounded-full", styles.track)}
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Timeline */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("recovery.timeline")}</CardTitle>
        </CardHeader>
        <CardContent>
          {tracker.timeline.length === 0 ? (
            <div className="flex flex-col items-center gap-2 rounded-md border bg-muted/40 p-6 text-center">
              <Sprout className="size-8 text-muted-foreground" aria-hidden="true" />
              <p className="text-sm font-medium text-foreground">{t("recovery.emptyTitle")}</p>
              <p className="text-sm text-muted-foreground">{t("recovery.emptyBody")}</p>
            </div>
          ) : (
            <ol className="flex flex-col gap-3">
              {tracker.timeline.map((log) => (
                <li
                  key={log.id}
                  className="rounded-md border bg-background p-3.5 print:break-inside-avoid"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold">{log.treatment_applied}</p>
                      <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                        <CalendarDays className="size-3.5" aria-hidden="true" />
                        {t("recovery.appliedOn", { date: formatDate(log.applied_at, i18n.language) })}
                        {log.progress && (
                          <Badge className={cn("text-xs", PROGRESS_STYLES[log.progress] ?? "bg-muted")}>
                            {t(`recovery.progressLevel.${log.progress}`)}
                          </Badge>
                        )}
                      </p>
                      {log.notes && (
                        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                          {log.notes}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-1 print:hidden">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditing(editing?.id === log.id ? null : log);
                          setConfirmingDelete(null);
                        }}
                      >
                        {t("recovery.edit")}
                      </Button>
                      {confirmingDelete === log.id ? (
                        <>
                          <Button
                            variant="destructive"
                            size="sm"
                            disabled={deleteMutation.isPending}
                            onClick={() => deleteMutation.mutate(log.id)}
                          >
                            {deleteMutation.isPending ? t("recovery.deleting") : t("recovery.delete")}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setConfirmingDelete(null)}>
                            <X className="size-4" aria-hidden="true" />
                          </Button>
                        </>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={t("recovery.deleteConfirm")}
                          onClick={() => {
                            setConfirmingDelete(log.id);
                            setEditing(null);
                          }}
                        >
                          <Trash2 className="size-4" aria-hidden="true" />
                        </Button>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>

      {/* Add / edit form */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {editing ? t("recovery.update") : t("recovery.addTitle")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <RecoveryTrackerForm
            // Remount when the target changes (add ↔ edit) so fields reset cleanly.
            key={editing?.id ?? "new"}
            editing={editing}
            saving={addMutation.isPending || updateMutation.isPending}
            error={
              addMutation.isError
                ? t("recovery.addError")
                : updateMutation.isError
                  ? t("recovery.updateError")
                  : null
            }
            onCancel={() => setEditing(null)}
            onSubmit={handleSubmit}
          />
        </CardContent>
      </Card>
    </section>
  );
}

// ── Add / edit form ──────────────────────────────────────────────────────

function RecoveryTrackerForm({
  editing,
  saving,
  error,
  onCancel,
  onSubmit,
}: {
  editing: RecoveryLog | null;
  saving: boolean;
  error: string | null;
  onCancel: () => void;
  onSubmit: (payload: RecoveryLogInput) => void;
}) {
  const { t } = useTranslation();
  // State initializes from `editing`; the parent keys the form by
  // `editing?.id ?? "new"`, so switching targets remounts with fresh fields.
  const [treatment, setTreatment] = useState(editing?.treatment_applied ?? "");
  const [notes, setNotes] = useState(editing?.notes ?? "");
  const [progress, setProgress] = useState(editing?.progress ?? "");
  const [date, setDate] = useState(editing?.applied_at?.slice(0, 10) ?? "");

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!treatment.trim()) return;
    const payload: RecoveryLogInput = {
      treatment_applied: treatment.trim(),
      notes: notes.trim() || null,
      progress: (progress as RecoveryProgress) || null,
      applied_at: date ? `${date}T00:00:00Z` : null,
    };
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="recovery-treatment">{t("recovery.treatmentLabel")}</Label>
        <Input
          id="recovery-treatment"
          value={treatment}
          onChange={(event) => setTreatment(event.target.value)}
          placeholder={t("recovery.treatmentPlaceholder")}
          required
          maxLength={500}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="recovery-progress">{t("recovery.progressLabel")}</Label>
          <Select
            id="recovery-progress"
            value={progress}
            onChange={(event) => setProgress(event.target.value)}
          >
            <option value="">{t("recovery.progressPlaceholder")}</option>
            {RECOVERY_PROGRESS_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {t(`recovery.progressLevel.${option}`)}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="recovery-date">{t("recovery.dateLabel")}</Label>
          <Input
            id="recovery-date"
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="recovery-notes">{t("recovery.notesLabel")}</Label>
        <textarea
          id="recovery-notes"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder={t("recovery.notesPlaceholder")}
          maxLength={2000}
          className="flex min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        />
      </div>

      {error && (
        <p role="alert" className="flex items-start gap-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2 print:hidden">
        <Button type="submit" disabled={saving || !treatment.trim()}>
          {saving ? (
            t("recovery.saving")
          ) : editing ? (
            <>
              <Check className="size-4" aria-hidden="true" />
              {t("recovery.update")}
            </>
          ) : (
            <>
              <Plus className="size-4" aria-hidden="true" />
              {t("recovery.add")}
            </>
          )}
        </Button>
        {editing && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            {t("recovery.cancelEdit")}
          </Button>
        )}
      </div>
    </form>
  );
}
