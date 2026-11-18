
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  CalendarRange,
  Leaf,
  Sprout,
  Sparkles,
} from "lucide-react";
import { motion } from "motion/react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { BucketSummary } from "@/components/calendar/bucket-summary";
import { CalendarCropPicker } from "@/components/calendar/calendar-crop-picker";
import {
  CALENDAR_QUERY_KEY,
  ScheduleCard,
} from "@/components/calendar/schedule-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { useAuth } from "@/stores/auth";

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
        <StateCard
          icon={CalendarDays}
          title={t("calendar.authRequired")}
        >
          <Button asChild>
            <Link to="/login">
              {t("calendar.signIn")}
            </Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50/70 via-background to-background dark:from-emerald-950/20">
      <div className="mx-auto max-w-7xl px-4 py-7 sm:px-6 sm:py-10">

        {/* Hero section */}
        <motion.header
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="relative mb-8 overflow-hidden rounded-3xl border border-emerald-100 bg-gradient-to-br from-white via-emerald-50 to-green-100/80 p-6 shadow-sm dark:border-emerald-900/50 dark:from-card dark:via-emerald-950/30 dark:to-green-950/40 sm:p-9"
        >
          <div className="pointer-events-none absolute -right-12 -top-16 size-64 rounded-full bg-emerald-200/30 blur-3xl dark:bg-emerald-500/10" />
          <div className="pointer-events-none absolute -bottom-20 right-1/4 size-52 rounded-full bg-lime-200/30 blur-3xl dark:bg-lime-500/10" />

          <div className="relative flex flex-col justify-between gap-6 md:flex-row md:items-center">
            <div className="max-w-2xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/70 px-3 py-1.5 text-xs font-semibold text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                <Sparkles className="size-3.5" />
                NeuroPlant AI · Smart Farm Planner
              </div>

              <h1 className="flex items-center gap-3 text-3xl font-bold tracking-tight sm:text-4xl">
                <CalendarDays className="size-8 shrink-0 text-emerald-700 dark:text-emerald-400" />
                {t("calendar.title")}
              </h1>

              <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground sm:text-base">
                {t("calendar.subtitle")}
              </p>
            </div>

            <div className="hidden shrink-0 items-center justify-center md:flex">
              <div className="flex size-28 items-center justify-center rounded-[2rem] border border-emerald-200/70 bg-white/70 shadow-sm dark:border-emerald-800/60 dark:bg-emerald-950/40">
                <div className="flex size-20 items-center justify-center rounded-3xl bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300">
                  <Sprout className="size-11" />
                </div>
              </div>
            </div>
          </div>
        </motion.header>

        {/* Dashboard content */}
        <div className="flex flex-col gap-8">
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
              {/* Task summary */}
              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
              >
                <div className="mb-4 flex items-center gap-3">
                  <div className="flex size-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300">
                    <CalendarRange className="size-5" />
                  </div>

                  <div>
                    <h2 className="text-lg font-bold tracking-tight">
                      {t("calendar.title")}
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      {t("calendar.subtitle")}
                    </p>
                  </div>
                </div>

                <BucketSummary
                  today={dashboardQuery.data.today_count}
                  upcoming={dashboardQuery.data.upcoming_count}
                  overdue={dashboardQuery.data.overdue_count}
                  completed={dashboardQuery.data.completed_count}
                />
              </motion.section>

              {/* Schedule crop */}
              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.08 }}
                className="overflow-hidden rounded-2xl border border-emerald-100 bg-card shadow-sm dark:border-emerald-900/50"
              >
                <div className="border-b border-border/70 bg-gradient-to-r from-emerald-50/80 to-transparent px-5 py-4 dark:from-emerald-950/30 sm:px-6">
                  <div className="flex items-center gap-3">
                    <div className="flex size-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300">
                      <Sprout className="size-5" />
                    </div>

                    <div>
                      <h2 className="font-bold tracking-tight">
                        {t("calendar.title")}
                      </h2>
                      <p className="text-xs text-muted-foreground">
                        {t("calendar.subtitle")}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-5 sm:p-6">
                  <CalendarCropPicker
                    onScheduled={() =>
                      queryClient.invalidateQueries({
                        queryKey: CALENDAR_QUERY_KEY,
                      })
                    }
                  />
                </div>
              </motion.section>

              {/* Crop schedules */}
              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.45, delay: 0.12 }}
                aria-label={t("calendar.schedules")}
              >
                <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex size-10 items-center justify-center rounded-xl bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300">
                      <Leaf className="size-5" />
                    </div>

                    <div>
                      <h2 className="text-lg font-bold tracking-tight sm:text-xl">
                        {t("calendar.schedules")}
                      </h2>
                      <p className="text-xs text-muted-foreground">
                        {t("calendar.subtitle")}
                      </p>
                    </div>
                  </div>
                </div>

                {dashboardQuery.data.schedules.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-emerald-300 bg-emerald-50/50 px-5 py-12 text-center dark:border-emerald-800 dark:bg-emerald-950/20">
                    <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300">
                      <CalendarDays className="size-8" />
                    </div>

                    <p className="text-sm font-semibold">
                      {t("calendar.empty")}
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-6">
                    {dashboardQuery.data.schedules.map(
                      (schedule, index) => (
                        <motion.div
                          key={schedule.schedule_id}
                          initial={{ opacity: 0, y: 12 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{
                            duration: 0.3,
                            delay: Math.min(index * 0.06, 0.3),
                          }}
                        >
                          <ScheduleCard
                            schedule={schedule}
                            today={today}
                          />
                        </motion.div>
                      ),
                    )}
                  </div>
                )}
              </motion.section>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function CalendarSkeleton() {
  const { t } = useTranslation();

  return (
    <div
      role="status"
      aria-label={t("calendar.title")}
      className="flex flex-col gap-7"
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Skeleton className="h-24 w-full rounded-2xl" />
        <Skeleton className="h-24 w-full rounded-2xl" />
        <Skeleton className="h-24 w-full rounded-2xl" />
        <Skeleton className="h-24 w-full rounded-2xl" />
      </div>

      <Skeleton className="h-56 w-full rounded-2xl" />
      <Skeleton className="h-72 w-full rounded-2xl" />
      <Skeleton className="h-72 w-full rounded-2xl" />
    </div>
  );
}
