import {
  AlertTriangle,
  CalendarCheck2,
  CalendarClock,
  CalendarDays,
  type LucideIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** The four dashboard buckets, in display order. */
const BUCKETS: Array<{
  key: "today" | "upcoming" | "overdue" | "completed";
  icon: LucideIcon;
  accent: string;
}> = [
  {
    key: "overdue",
    icon: AlertTriangle,
    accent: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  },
  {
    key: "today",
    icon: CalendarClock,
    accent: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  },
  {
    key: "upcoming",
    icon: CalendarDays,
    accent: "bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300",
  },
  {
    key: "completed",
    icon: CalendarCheck2,
    accent: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  },
];

/**
 * The Farmer Calendar summary strip — one stat card per bucket
 * (today / upcoming / overdue / completed). Counts come from the server;
 * the page just renders them.
 */
export function BucketSummary({
  today,
  upcoming,
  overdue,
  completed,
}: {
  today: number;
  upcoming: number;
  overdue: number;
  completed: number;
}) {
  const { t } = useTranslation();
  const counts = { today, upcoming, overdue, completed };

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {BUCKETS.map((bucket) => (
        <Card key={bucket.key}>
          <CardContent className="flex items-center gap-3 p-4">
            <span
              className={cn(
                "flex size-9 shrink-0 items-center justify-center rounded-lg",
                bucket.accent,
              )}
            >
              <bucket.icon className="size-4" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="text-2xl font-bold leading-none tabular-nums">
                {counts[bucket.key]}
              </p>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {t(`calendar.buckets.${bucket.key}`)}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
