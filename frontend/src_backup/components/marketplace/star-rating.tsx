import { Star } from "lucide-react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { RATING_MAX } from "@/types/trust";

/** All scale values, 5→1 — the order ratings render in. */
export const STAR_VALUES = Array.from({ length: RATING_MAX }, (_, i) => RATING_MAX - i);

function starClass(filled: boolean, sizeClass = "size-4") {
  return cn(
    sizeClass,
    filled ? "fill-amber-400 text-amber-400" : "text-muted-foreground",
  );
}

/**
 * Read-only star row (M4 Task 6) — shows one item's rating on a 1–5 scale.
 * Rendered as an image to screen readers with a plain-text label (never just
 * unlabeled icons). Used in the rating summary, each review, and the favourites
 * / my-reviews surfaces.
 */
export function StarRating({
  value,
  label,
  className,
}: {
  value: number;
  /** Accessible label; defaults to "N out of 5". */
  label?: string;
  className?: string;
}) {
  const { t } = useTranslation();
  const ariaLabel = label ?? t("reviews.ratingValue", { count: value });
  return (
    <div className={cn("flex items-center gap-0.5", className)} role="img" aria-label={ariaLabel}>
      {STAR_VALUES.map((star) => (
        <Star
          key={star}
          className={starClass(star <= value)}
          aria-hidden
        />
      ))}
    </div>
  );
}

/**
 * Interactive 1–5 star picker (M4 Task 6) for the write/edit review form.
 * Exposed as a radio group so keyboard + screen-reader users can set the rating
 * one star at a time; each star is a real button with aria-checked.
 */
export function RatingInput({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div
      role="radiogroup"
      aria-label={t("reviews.ratingLabel")}
      className="flex items-center gap-1"
    >
      {STAR_VALUES.map((star) => (
        <button
          key={star}
          type="button"
          role="radio"
          aria-checked={value === star}
          aria-label={t("reviews.ratingValue", { count: star })}
          disabled={disabled}
          className={cn(
            "rounded-sm p-0.5 transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            disabled && "cursor-not-allowed opacity-50",
          )}
          onClick={() => onChange(star)}
        >
          <Star className={starClass(star <= value, "size-6")} aria-hidden />
        </button>
      ))}
    </div>
  );
}
