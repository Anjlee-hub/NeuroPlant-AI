import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PenLine, Star } from "lucide-react";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";

import { Pagination } from "@/components/marketplace/pagination";
import { RatingSummaryCard } from "@/components/marketplace/rating-summary";
import { ReviewCard } from "@/components/marketplace/review-card";
import { ReviewForm, toReviewUpdate, type ReviewFormValue } from "@/components/marketplace/review-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api, errorMessage } from "@/lib/api";
import type { Review } from "@/types/trust";

/** Query-key prefix for an item's reviews (all pages share the target part). */
export function reviewsQueryKey(target: { listingId?: number; productId?: number }, page: number) {
  return ["reviews", target.listingId ?? null, target.productId ?? null, page] as const;
}

/**
 * Ratings & reviews block for one item (a crop listing or a product — M4 Task 6).
 * Loads the paginated reviews with the rating summary and the caller's own
 * review in one request, shows the 5→1 distribution, and owns the write / edit /
 * delete mutations. The caller's review sits in its own "Your review" card on
 * top (edit swaps it for the form) and is excluded from the list below, so it
 * never renders twice. Reuses the marketplace `Pagination` for paging.
 */
export function ReviewSection({
  listingId,
  productId,
}: {
  listingId?: number;
  productId?: number;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Review | null>(null);

  const target = { listingId, productId };
  const reviewsQuery = useQuery({
    queryKey: reviewsQueryKey(target, page),
    queryFn: () => api.listReviews({ listing_id: listingId, product_id: productId, page }),
    enabled: listingId != null || productId != null,
  });

  /** Invalidate every page of this item's reviews (all keys share the prefix). */
  const invalidate = useCallback(() => {
    void queryClient.invalidateQueries({
      queryKey: ["reviews", listingId ?? null, productId ?? null],
    });
  }, [queryClient, listingId, productId]);

  const create = useMutation({
    mutationFn: (value: ReviewFormValue) =>
      api.createReview({ listing_id: listingId, product_id: productId, ...value }),
    onSuccess: () => {
      setShowForm(false);
      invalidate();
    },
  });

  const update = useMutation({
    mutationFn: ({ id, value }: { id: number; value: ReviewFormValue }) =>
      api.updateReview(id, toReviewUpdate(value)),
    onSuccess: () => {
      setEditing(null);
      invalidate();
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteReview(id),
    onSuccess: () => {
      setShowForm(false);
      setEditing(null);
      invalidate();
    },
  });

  const data = reviewsQuery.data;
  const myReview = data?.my_review ?? null;
  const others = (data?.items ?? []).filter((review) => review.id !== myReview?.id);
  const createError = create.isError ? errorMessage(create.error) : null;
  const updateError = update.isError ? errorMessage(update.error) : null;

  return (
    <section aria-label={t("reviews.title")} className="mt-10">
      <h2 className="text-xl font-bold tracking-tight">{t("reviews.title")}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{t("reviews.subtitle")}</p>

      {reviewsQuery.isPending ? (
        <ReviewsSkeleton />
      ) : reviewsQuery.isError || !data ? (
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
      ) : (
        <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,300px)_1fr]">
          <RatingSummaryCard summary={data.summary} />

          <div className="space-y-4">
            {myReview ? (
              editing?.id === myReview.id ? (
                <Card>
                  <CardContent className="p-4">
                    <ReviewForm
                      initial={myReview}
                      submitLabel={t("reviews.submitEdit")}
                      isPending={update.isPending}
                      error={updateError}
                      onSubmit={(value) => update.mutate({ id: myReview.id, value })}
                      onCancel={() => setEditing(null)}
                    />
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="p-4">
                    <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                      {t("reviews.yourReview")}
                    </h3>
                    <ReviewCard
                      review={myReview}
                      isOwn
                      isDeleting={remove.isPending}
                      onEdit={() => setEditing(myReview)}
                      onDelete={() => remove.mutate(myReview.id)}
                    />
                  </CardContent>
                </Card>
              )
            ) : showForm ? (
              <Card>
                <CardContent className="p-4">
                  <ReviewForm
                    submitLabel={t("reviews.submit")}
                    isPending={create.isPending}
                    error={createError}
                    onSubmit={(value) => create.mutate(value)}
                    onCancel={() => setShowForm(false)}
                  />
                </CardContent>
              </Card>
            ) : (
              <Button variant="outline" size="sm" onClick={() => setShowForm(true)}>
                <PenLine className="size-4" aria-hidden />
                {t("reviews.writeReview")}
              </Button>
            )}

            {others.length === 0 ? (
              <StateCard icon={Star} title={t("reviews.emptyTitle")} body={t("reviews.emptyBody")} />
            ) : (
              <ul className="space-y-3">
                {others.map((review) => (
                  <li key={review.id}>
                    <ReviewCard review={review} />
                  </li>
                ))}
              </ul>
            )}

            <Pagination page={data.page} pages={data.pages} onPageChange={setPage} />
          </div>
        </div>
      )}
    </section>
  );
}

function ReviewsSkeleton() {
  return (
    <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,300px)_1fr]" aria-hidden>
      <div className="space-y-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
      <div className="space-y-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
}
