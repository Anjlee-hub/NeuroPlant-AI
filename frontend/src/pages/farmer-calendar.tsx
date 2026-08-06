import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, CalendarRange } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { BucketSummary } from "@/components/calendar/bucket-summary";
import { CalendarCropPicker } from "@/components/calendar/calendar-crop-picker";
import { CALENDAR_QUERY_KEY, ScheduleCard } from "@/components/calendar/schedule-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { useAuth } from "@/stores/auth";
import { api } from "@/lib/api";

/**
 * Farmer Calendar dashboard (M3, Task 5) — the per-farmer planning surface.
 * Shows bucket counts (today / upcoming / overdue / completed) at the top, a
 * "schedule a crop" picker, then one ScheduleCard per active crop with its
 * growth-stage timeline and smart task list. Bucketing is computed client-side
 * with the same rule the server uses (completed first, then today/overdue/
 * upcoming by UTC date), so actions feel instant while the server stays the
 * source of truth.
 */
export function FarmerCalendarPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const dashboardQuery = useQuery({
    queryKey: CALENDAR_QUERY_KEY,
    queryFn: () => api.getFarmerCalendar(),
    enabled: !!user,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={CalendarDays} title={t("calendar.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("calendar.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
            <CalendarDays className="size-7 text-brand-600 dark:text-brand-400" />
            {t("calendar.title")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("calendar.subtitle")}</p>
        </div>
      </header>

      <div className="mt-6 flex flex-col gap-6">
        {dashboardQuery.isPending ? (
          <CalendarSkeleton />
        ) : dashboardQuery.isError ? (
          <StateCard
            icon={CalendarRange}
            title={t("calendar.errorTitle")}
            body={t("calendar.errorBody")}
            tone="destructive"
          >
            <Button
              variant="outline"
              onClick={() => void dashboardQuery.refetch()}
            >
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : dashboardQuery.data ? (
          <>
            <BucketSummary
              today={dashboardQuery.data.today_count}
              upcoming={dashboardQuery.data.upcoming_count}
              overdue={dashboardQuery.data.overdue_count}
              completed={dashboardQuery.data.completed_count}
            />

            <CalendarCropPicker
              onScheduled={() =>
                queryClient.invalidateQueries({ queryKey: CALENDAR_QUERY_KEY })
              }
            />

            {dashboardQuery.data.schedules.length === 0 ? (
              <p className="rounded-md border bg-muted/40 p-6 text-center text-sm text-muted-foreground">
                {t("calendar.empty")}
              </p>
            ) : (
              <section aria-label={t("calendar.schedules")} className="flex flex-col gap-6">
                {dashboardQuery.data.schedules.map((schedule) => (
                  <ScheduleCard key={schedule.schedule_id} schedule={schedule} today={today} />
                ))}
              </section>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}

function CalendarSkeleton() {
  const { t } = useTranslation();
  return (
    <div role="status" aria-label={t("calendar.title")} className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
