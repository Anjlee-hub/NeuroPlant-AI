import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlarmClock,
  Check,
  Droplets,
  Plus,
  Sprout,
  Trash2,
  X,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/format";
import type {
  CalendarTask,
  CalendarTaskBucket,
  CalendarTaskKind,
  CropCalendar,
} from "@/types/calendar";

/** The dashboard query every calendar mutation invalidates. */
export const CALENDAR_QUERY_KEY = ["farmer-calendar"] as const;

/** Task-kind badge colors (full class strings so Tailwind keeps them). */
export const KIND_STYLES: Record<CalendarTaskKind, string> = {
  watering: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  fertilizer: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  organic_treatment: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  chemical_treatment: "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300",
  disease_monitoring: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  soil_inspection: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  custom: "bg-muted text-muted-foreground",
};

/** Bucket a task exactly like the backend: completed first, then today/overdue/upcoming. */
export function bucketTask(task: CalendarTask, today: string): CalendarTaskBucket {
  if (task.completed_at) return "completed";
  const due = task.due_at.slice(0, 10);
  if (due === today) return "today";
  if (due < today) return "overdue";
  return "upcoming";
}

const BUCKET_ORDER: CalendarTaskBucket[] = ["overdue", "today", "upcoming", "completed"];

/** One scheduled crop: stage timeline + progress + task list + custom note form. */
export function ScheduleCard({
  schedule,
  today,
}: {
  schedule: CropCalendar;
  today: string;
}) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [customOpen, setCustomOpen] = useState(false);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: CALENDAR_QUERY_KEY });

  const completeMutation = useMutation({
    mutationFn: (taskId: number) =>
      api.updateCalendarTask(taskId, { completed: true }),
    onSuccess: () => invalidate(),
  });
  const snoozeMutation = useMutation({
    mutationFn: (taskId: number) =>
      api.updateCalendarTask(taskId, { snooze_days: 1 }),
    onSuccess: () => invalidate(),
  });
  const deleteMutation = useMutation({
    mutationFn: (taskId: number) => api.deleteCalendarTask(taskId),
    onSuccess: () => invalidate(),
  });

  const percent = Math.min(100, Math.round(schedule.progress * 100));
  const groups = BUCKET_ORDER.map((bucket) => ({
    bucket,
    tasks: schedule.tasks.filter((task) => bucketTask(task, today) === bucket),
  })).filter((group) => group.tasks.length > 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sprout className="size-5 text-brand-600 dark:text-brand-400" aria-hidden="true" />
              {schedule.crop_name}
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              {t("calendar.schedule.plantedOn", {
                date: formatDate(`${schedule.planting_date}T00:00:00`, i18n.language),
              })}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="text-lg font-bold tabular-nums">{percent}%</span>
          </div>
        </div>
        <div
          className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-label={t("calendar.schedule.progress")}
        >
          <div
            className="h-full rounded-full bg-brand-500"
            style={{ width: `${percent}%` }}
          />
        </div>
        <p className="mt-1 text-right text-xs text-muted-foreground">
          {t("calendar.schedule.completedCount", {
            completed: schedule.completed,
            total: schedule.total,
          })}
        </p>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/* Growth-stage timeline */}
        <div className="overflow-x-auto" aria-label={t("calendar.schedule.stages")}>
          <ol className="flex min-w-max gap-1.5">
            {schedule.stages.map((stage) => (
              <li
                key={stage.stage}
                className="flex min-w-24 flex-col gap-0.5 rounded-md border bg-muted/40 px-2.5 py-1.5"
              >
                <span className="text-xs font-semibold">
                  {t(`calendar.stages.${stage.stage}`)}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {new Intl.DateTimeFormat(i18n.language, {
                    month: "short",
                    day: "numeric",
                  }).format(new Date(`${stage.start_date}T00:00:00`))}
                  {stage.start_date !== stage.end_date &&
                    ` – ${new Intl.DateTimeFormat(i18n.language, {
                      month: "short",
                      day: "numeric",
                    }).format(new Date(`${stage.end_date}T00:00:00`))}`}
                </span>
              </li>
            ))}
          </ol>
        </div>

        {/* Task groups */}
        {groups.length === 0 ? (
          <p className="rounded-md border bg-muted/40 p-4 text-center text-sm text-muted-foreground">
            {t("calendar.schedule.noTasks")}
          </p>
        ) : (
          <div className="flex flex-col gap-4">
            {groups.map((group) => (
              <div key={group.bucket}>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {t(`calendar.buckets.${group.bucket}`)} ({group.tasks.length})
                </h4>
                <ul className="flex flex-col gap-2">
                  {group.tasks.map((task) => (
                    <TaskRow
                      key={task.id}
                      task={task}
                      busy={
                        completeMutation.isPending ||
                        snoozeMutation.isPending ||
                        deleteMutation.isPending
                      }
                      onComplete={() => completeMutation.mutate(task.id)}
                      onSnooze={() => snoozeMutation.mutate(task.id)}
                      onDelete={() => deleteMutation.mutate(task.id)}
                    />
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        {/* Custom note / to-do */}
        <div className="mt-1 border-t pt-3">
          {customOpen ? (
            <CustomTaskForm
              scheduleId={schedule.schedule_id}
              onCancel={() => setCustomOpen(false)}
              onSaved={() => {
                setCustomOpen(false);
                invalidate();
              }}
            />
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCustomOpen(true)}
              className="w-full"
            >
              <Plus className="size-4" aria-hidden="true" />
              {t("calendar.schedule.addCustom")}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

/** One task row: kind badge, title, due date, notes + complete/snooze/delete. */
function TaskRow({
  task,
  busy,
  onComplete,
  onSnooze,
  onDelete,
}: {
  task: CalendarTask;
  busy: boolean;
  onComplete: () => void;
  onSnooze: () => void;
  onDelete: () => void;
}) {
  const { t, i18n } = useTranslation();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isCompleted = task.completed_at !== null;

  return (
    <li
      className={cn(
        "rounded-md border bg-background p-3",
        isCompleted && "opacity-70",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <Button
            variant={isCompleted ? "default" : "outline"}
            size="icon"
            className="mt-0.5 size-7 shrink-0 rounded-full"
            aria-label={
              isCompleted
                ? t("calendar.task.undoComplete")
                : t("calendar.task.complete")
            }
            disabled={busy}
            onClick={onComplete}
          >
            <Check className="size-4" aria-hidden="true" />
          </Button>
          <div className="min-w-0">
            <p
              className={cn(
                "text-sm font-medium",
                isCompleted && "text-muted-foreground line-through",
              )}
            >
              {task.title}
            </p>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
              <Badge className={cn("text-[10px]", KIND_STYLES[task.kind] ?? "bg-muted")}>
                {t(`calendar.kinds.${task.kind}`)}
              </Badge>
              <span className="inline-flex items-center gap-1">
                <Droplets className="size-3" aria-hidden="true" />
                {formatDate(task.due_at, i18n.language)}
              </span>
              {task.snooze_count > 0 && (
                <span className="inline-flex items-center gap-1">
                  <AlarmClock className="size-3" aria-hidden="true" />
                  {task.snooze_count}
                </span>
              )}
            </p>
            {task.notes && (
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                {task.notes}
              </p>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {!isCompleted && (
            <Button
              variant="ghost"
              size="sm"
              disabled={busy}
              aria-label={t("calendar.task.snooze")}
              onClick={onSnooze}
            >
              <AlarmClock className="size-4" aria-hidden="true" />
            </Button>
          )}
          {confirmDelete ? (
            <>
              <Button
                variant="destructive"
                size="sm"
                disabled={busy}
                onClick={onDelete}
              >
                {t("calendar.task.delete")}
              </Button>
              <Button variant="ghost" size="icon" onClick={() => setConfirmDelete(false)}>
                <X className="size-4" aria-hidden="true" />
              </Button>
            </>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              aria-label={t("calendar.task.deleteConfirm")}
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 className="size-4" aria-hidden="true" />
            </Button>
          )}
        </div>
      </div>
    </li>
  );
}

/** Inline "add a custom note / to-do" form. */
function CustomTaskForm({
  scheduleId,
  onCancel,
  onSaved,
}: {
  scheduleId: number;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      api.addCalendarTask({
        schedule_id: scheduleId,
        title: title.trim(),
        due_at: dueDate ? `${dueDate}T00:00:00` : null,
      }),
    onSuccess: () => onSaved(),
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim() || mutation.isPending) return;
    mutation.mutate();
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        <Label htmlFor={`custom-title-${scheduleId}`}>{t("calendar.custom.titleLabel")}</Label>
        <Input
          id={`custom-title-${scheduleId}`}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder={t("calendar.custom.titlePlaceholder")}
          maxLength={300}
          required
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={`custom-date-${scheduleId}`}>{t("calendar.custom.dateLabel")}</Label>
        <input
          id={`custom-date-${scheduleId}`}
          type="date"
          value={dueDate}
          onChange={(event) => setDueDate(event.target.value)}
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm ring-offset-background transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        />
      </div>
      {mutation.isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("calendar.custom.error")}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" disabled={mutation.isPending || !title.trim()}>
          {mutation.isPending ? t("calendar.custom.saving") : t("calendar.custom.save")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          {t("calendar.custom.cancel")}
        </Button>
      </div>
    </form>
  );
}
