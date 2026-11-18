import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Page navigation for the buyer browse grid (M4 Task 3). The backend paginates
 * server-side (CropListingPageOut), so the page shows a compact window of page
 * buttons plus prev/next. Fully keyboard-accessible via the native buttons and
 * announces the current position to screen readers.
 */
export function Pagination({
  page,
  pages,
  onPageChange,
}: {
  /** 1-based current page. */
  page: number;
  /** Total page count (>= 1). */
  pages: number;
  onPageChange: (page: number) => void;
}) {
  const { t } = useTranslation();

  if (pages <= 1) return null;

  // A window of up to 5 pages around the current one (with first/last pinned
  // when they're off-window) keeps long result sets navigable without a
  // thousand buttons.
  const windowStart = Math.max(1, Math.min(page - 2, pages - 4));
  const windowEnd = Math.min(pages, windowStart + 4);
  const visible: number[] = [];
  for (let p = windowStart; p <= windowEnd; p += 1) visible.push(p);

  const go = (target: number) => {
    if (target < 1 || target > pages || target === page) return;
    onPageChange(target);
  };

  return (
    <nav
      aria-label={t("marketplaceBuy.pagination.label")}
      className="flex flex-wrap items-center justify-center gap-1 pt-4"
    >
      <Button
        variant="outline"
        size="sm"
        disabled={page <= 1}
        onClick={() => go(page - 1)}
        aria-label={t("marketplaceBuy.pagination.previous")}
      >
        <ChevronLeft className="size-4" aria-hidden />
        <span className="sr-only">{t("marketplaceBuy.pagination.previous")}</span>
      </Button>

      {visible.map((p) => (
        <Button
          key={p}
          variant={p === page ? "default" : "outline"}
          size="sm"
          className={cn(p === page && "pointer-events-none")}
          aria-current={p === page ? "page" : undefined}
          aria-label={t("marketplaceBuy.pagination.goTo", { page: p })}
          onClick={() => go(p)}
        >
          {p}
        </Button>
      ))}

      <Button
        variant="outline"
        size="sm"
        disabled={page >= pages}
        onClick={() => go(page + 1)}
        aria-label={t("marketplaceBuy.pagination.next")}
      >
        <span className="sr-only">{t("marketplaceBuy.pagination.next")}</span>
        <ChevronRight className="size-4" aria-hidden />
      </Button>

      <span className="ml-2 text-sm text-muted-foreground">
        {t("marketplaceBuy.pagination.page", { page, pages })}
      </span>
    </nav>
  );
}
