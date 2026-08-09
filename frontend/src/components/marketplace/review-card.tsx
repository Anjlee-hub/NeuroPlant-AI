import { Loader2, Pencil, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { StarRating } from "@/components/marketplace/star-rating";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/format";
import type { Review } from "@/types/trust";

/**
 * One review as rendered on an item's detail page (M4 Task 6): the reviewer's
 * initial avatar + name + date, the star rating, optional title and the review
 * text. When it's the caller's own review the edit/delete actions appear — the
 * delete button shows its busy state inline and both are owner-scoped (the API
 * answers 404 for anyone else's, matching the platform's enumeration guard).
 */
export function ReviewCard({
  review,
  isOwn,
  isDeleting,
  onEdit,
  onDelete,
}: {
  review: Review;
  /** Whether this is the authenticated user's own review (shows actions). */
  isOwn?: boolean;
  isDeleting?: boolean;
  onEdit?: (review: Review) => void;
  onDelete?: (review: Review) => void;
}) {
  const { t, i18n } = useTranslation();
  const initial = review.reviewer_name.trim().charAt(0).toUpperCase() || "?";

  return (
    <article className="rounded-lg border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span
            aria-hidden
            className="flex size-9 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold"
          >
            {initial}
          </span>
          <div>
            <p className="text-sm font-semibold">{review.reviewer_name}</p>
            <p className="text-xs text-muted-foreground">
              {formatDate(review.created_at, i18n.language)}
            </p>
          </div>
        </div>
        <StarRating value={review.rating} />
      </div>

      {review.title && <h4 className="mt-2 text-sm font-semibold">{review.title}</h4>}
      <p className="mt-1 text-sm whitespace-pre-line text-foreground/90">{review.content}</p>

      {isOwn && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3">
          <Button size="sm" variant="outline" onClick={() => onEdit?.(review)}>
            <Pencil className="size-4" aria-hidden />
            {t("reviews.edit")}
          </Button>
          <Button
            size="sm"
            variant="destructive"
            disabled={isDeleting}
            aria-busy={isDeleting}
            onClick={() => onDelete?.(review)}
          >
            {isDeleting ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Trash2 className="size-4" aria-hidden />
            )}
            {isDeleting ? t("reviews.deleting") : t("reviews.delete")}
          </Button>
        </div>
      )}
    </article>
  );
}
