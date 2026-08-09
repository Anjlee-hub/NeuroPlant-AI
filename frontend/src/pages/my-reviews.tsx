import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Star } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ReviewCard } from "@/components/marketplace/review-card";
import { ReviewForm, toReviewUpdate, type ReviewFormValue } from "@/components/marketplace/review-form";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import type { Review } from "@/types/trust";

export const MY_REVIEWS_KEY = ["my-reviews"] as const;

/**
 * My Reviews (M4 Task 6) at /marketplace/my-reviews — every review the caller
 * has written, newest first, each with a link back to the item it rates (or an
 * honest "deleted" marker once that item is gone) and the edit / delete actions.
 * Editing swaps the card for the same form used on the detail pages.
 */
export function MyReviewsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<number | null>(null);

  const reviewsQuery = useQuery({
    queryKey: MY_REVIEWS_KEY,
    queryFn: () => api.listMyReviews(),
    enabled: !!user,
  });

  const invalidate = () => void queryClient.invalidateQueries({ queryKey: MY_REVIEWS_KEY });

  const update = useMutation({
    mutationFn: ({ id, value }: { id: number; value: ReviewFormValue }) =>
      api.updateReview(id, toReviewUpdate(value)),
    onSuccess: () => {
      setEditingId(null);
      invalidate();
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteReview(id),
    onSuccess: invalidate,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <StateCard icon={Star} title={t("reviews.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("reviews.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const reviews = reviewsQuery.data;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
          <Star className="size-7 text-brand-600 dark:text-brand-400" aria-hidden />
          {t("reviews.myTitle")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("reviews.mySubtitle")}</p>
      </header>

      <div className="mt-6">
        {reviewsQuery.isPending ? (
          <div className="space-y-3" aria-hidden>
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-28 w-full rounded-lg" />
            ))}
          </div>
        ) : reviewsQuery.isError || !reviews ? (
          <StateCard
            icon={Star}
            title={t("reviews.errorTitle")}
            body={t("reviews.errorBody")}
            tone="destructive"
          >
            <Button variant="outline" onClick={() => void reviewsQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : reviews.length === 0 ? (
          <StateCard icon={Star} title={t("reviews.myEmptyTitle")} body={t("reviews.myEmptyBody")}>
            <Button asChild>
              <Link to="/marketplace/browse">{t("reviews.browseMarketplace")}</Link>
            </Button>
          </StateCard>
        ) : (
          <ul className="space-y-3">
            {reviews.map((review) => (
              <li key={review.id} className="rounded-lg border bg-card p-4">
                <ReviewTargetLink review={review} />
                <div className="mt-3">
                  {editingId === review.id ? (
                    <ReviewForm
                      initial={review}
                      submitLabel={t("reviews.submitEdit")}
                      isPending={update.isPending}
                      error={update.isError ? errorMessage(update.error) : null}
                      onSubmit={(value) => update.mutate({ id: review.id, value })}
                      onCancel={() => setEditingId(null)}
                    />
                  ) : (
                    <ReviewCard
                      review={review}
                      isOwn
                      isDeleting={remove.isPending && remove.variables === review.id}
                      onEdit={() => setEditingId(review.id)}
                      onDelete={() => remove.mutate(review.id)}
                    />
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/** Link back to the item a review is about (or a deleted-item marker). */
function ReviewTargetLink({ review }: { review: Review }) {
  const { t } = useTranslation();

  if (review.listing) {
    return (
      <Link
        to={`/marketplace/listings/${review.listing.id}`}
        className="inline-flex max-w-full items-center gap-1.5 text-sm font-medium text-brand-600 hover:underline dark:text-brand-400"
      >
        <span className="truncate">{review.listing.crop_name}</span>
        <ArrowRight className="size-3.5 shrink-0" aria-hidden />
      </Link>
    );
  }
  if (review.product) {
    return (
      <Link
        to={`/marketplace/products/${review.product.id}`}
        className="inline-flex max-w-full items-center gap-1.5 text-sm font-medium text-brand-600 hover:underline dark:text-brand-400"
      >
        <span className="truncate">{review.product.name}</span>
        <ArrowRight className="size-3.5 shrink-0" aria-hidden />
      </Link>
    );
  }
  return (
    <p className="text-sm italic text-muted-foreground">{t("reviews.itemDeleted")}</p>
  );
}
