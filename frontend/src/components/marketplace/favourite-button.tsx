import { Heart, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { useFavouriteStatus } from "@/lib/favourites";
import { cn } from "@/lib/utils";

/**
 * Save / remove one item (a crop listing or a product) from the buyer's
 * favourites (M4 Task 6). Server-backed: the pressed state loads from
 * `GET /marketplace/favorites/status` and toggling is an optimistic POST/DELETE.
 * Honest states — a disabled "Checking…" while the state loads, a spinner while
 * a toggle is in flight, and an inline error (with the button disabled) if the
 * state could not be fetched. The pressed state is exposed both visually
 * (filled heart) and to assistive tech (aria-pressed + aria-busy).
 */
export function FavouriteButton({
  listingId,
  productId,
}: {
  listingId?: number;
  productId?: number;
}) {
  const { t } = useTranslation();
  const {
    isFavourited,
    isStatusLoading,
    isStatusError,
    isMutating,
    toggle,
    error,
  } = useFavouriteStatus({ listingId, productId });

  const busy = isStatusLoading || isMutating;
  const label = isFavourited
    ? t("marketplaceBuy.actions.unfavourite")
    : t("marketplaceBuy.actions.favourite");
  const buttonLabel = busy
    ? isStatusLoading
      ? t("marketplaceBuy.actions.checking")
      : t("marketplaceBuy.actions.saving")
    : isFavourited
      ? t("marketplaceBuy.actions.favourited")
      : t("marketplaceBuy.actions.favourite");

  return (
    <div className="flex flex-col items-start gap-1.5">
      <Button
        variant={isFavourited ? "default" : "outline"}
        size="sm"
        aria-pressed={isFavourited}
        aria-busy={busy}
        aria-label={label}
        title={label}
        disabled={busy || isStatusError}
        onClick={toggle}
      >
        {busy ? (
          <Loader2 className="size-4 animate-spin" aria-hidden />
        ) : (
          <Heart
            className={cn("size-4", isFavourited && "fill-current")}
            aria-hidden
          />
        )}
        {buttonLabel}
      </Button>
      {isStatusError && (
        <p role="alert" className="text-xs text-destructive">
          {t("marketplaceBuy.actions.favouriteError")}
        </p>
      )}
      {error && !isStatusError && (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
