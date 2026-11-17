import { Star } from "lucide-react";
import { useTranslation } from "react-i18next";

import { StarRating, STAR_VALUES } from "@/components/marketplace/star-rating";
import { cn } from "@/lib/utils";
import type { RatingSummary } from "@/types/trust";

/**
 * Aggregate rating for an item or a seller (M4 Task 6): the big average, the
 * review count, and a 5→1 star distribution with proportional bars. The
 * distribution arrives with JSON string keys ("1".."5"), so each star value is
 * read as `distribution[String(star)]` — never a number-keyed lookup.
 */
export function RatingSummaryCard({ summary, className }: { summary: RatingSummary; className?: string }) {
  const { t } = useTranslation();
  const counts = STAR_VALUES.map((star) => summary.distribution[String(star)] ?? 0);
  const max = Math.max(1, ...counts);

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center gap-3">
        <span className="text-4xl font-bold tabular-nums">
          {summary.average.toFixed(1)}
        </span>
        <div>
          <StarRating value={summary.average} label={t("reviews.summaryLabel")} />
          <p className="mt-0.5 text-xs text-muted-foreground">
            {t("reviews.summaryCount", { count: summary.total })}
          </p>
        </div>
      </div>

      <dl className="space-y-1.5">
        {STAR_VALUES.map((star, index) => {
          const count = counts[index];
          const pct = Math.round((count / max) * 100);
          return (
            <div key={star} className="flex items-center gap-2 text-sm">
              <dt className="flex w-9 shrink-0 items-center gap-1 text-xs text-muted-foreground">
                <Star className="size-3.5 fill-amber-400 text-amber-400" aria-hidden />
                {star}
              </dt>
              <dd
                className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
                role="presentation"
              >
                <div
                  className="h-full rounded-full bg-amber-400"
                  style={{ width: `${pct}%` }}
                />
              </dd>
              <dd className="w-7 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                {count}
              </dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}
