import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { RatingInput } from "@/components/marketplace/star-rating";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  REVIEW_CONTENT_MAX_LENGTH,
  REVIEW_TITLE_MAX_LENGTH,
  type ReviewUpdateInput,
} from "@/types/trust";

export interface ReviewFormValue {
  rating: number;
  title: string | null;
  content: string;
}

/**
 * Write / edit one review (M4 Task 6). The form owns rating + title + content
 * state and the local blank-content guard (mirroring the backend's boundary
 * validation); the network call lives in the parent's mutation. Editing starts
 * with the review's current values so only the sent fields change on PATCH.
 */
export function ReviewForm({
  initial,
  submitLabel,
  isPending,
  error,
  onSubmit,
  onCancel,
}: {
  /** Pre-fill values when editing an existing review. */
  initial?: ReviewFormValue | null;
  submitLabel: string;
  isPending?: boolean;
  /** Server-side failure message from the parent mutation. */
  error?: string | null;
  onSubmit: (value: ReviewFormValue) => void;
  onCancel?: () => void;
}) {
  const { t } = useTranslation();
  const [rating, setRating] = useState<number>(initial?.rating ?? 5);
  const [title, setTitle] = useState(initial?.title ?? "");
  const [content, setContent] = useState(initial?.content ?? "");
  const [localError, setLocalError] = useState<string | null>(null);

  const submit = () => {
    if (content.trim().length === 0) {
      setLocalError(t("reviews.contentRequired"));
      return;
    }
    setLocalError(null);
    onSubmit({ rating, title: title.trim() || null, content: content.trim() });
  };

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div className="space-y-1.5">
        <span className="text-sm font-medium leading-none">{t("reviews.ratingLabel")}</span>
        <RatingInput value={rating} onChange={setRating} disabled={isPending} />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="review-title">{t("reviews.titleLabel")}</Label>
        <Input
          id="review-title"
          name="review-title"
          value={title}
          maxLength={REVIEW_TITLE_MAX_LENGTH}
          placeholder={t("reviews.titlePlaceholder")}
          disabled={isPending}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="review-content">{t("reviews.contentLabel")}</Label>
        <Textarea
          id="review-content"
          name="review-content"
          value={content}
          maxLength={REVIEW_CONTENT_MAX_LENGTH}
          placeholder={t("reviews.contentPlaceholder")}
          disabled={isPending}
          onChange={(e) => setContent(e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          {t("reviews.contentHint", { max: REVIEW_CONTENT_MAX_LENGTH })}
        </p>
      </div>

      {(localError || error) && (
        <p role="alert" className="text-sm text-destructive">
          {localError ?? error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" disabled={isPending} aria-busy={isPending}>
          {isPending && <Loader2 className="size-4 animate-spin" aria-hidden />}
          {submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" disabled={isPending} onClick={onCancel}>
            {t("common.cancel")}
          </Button>
        )}
      </div>
    </form>
  );
}

/** The mutable subset of a review the form edits (PATCH payload). */
export function toReviewUpdate(value: ReviewFormValue): ReviewUpdateInput {
  return { rating: value.rating, title: value.title, content: value.content };
}
