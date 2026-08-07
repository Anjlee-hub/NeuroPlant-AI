import { Heart } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { useFavourites } from "@/lib/favourites";
import { cn } from "@/lib/utils";

/**
 * Save / remove a listing from the buyer's favourites (M4 Task 3). LocalStorage
 * only — the hook is architecture-ready for a backend, so this button makes no
 * network call yet. The pressed state is exposed both visually (filled heart)
 * and to assistive tech (aria-pressed).
 */
export function FavouriteButton({ listingId }: { listingId: number }) {
  const { t } = useTranslation();
  const { isFavourite, toggle } = useFavourites();
  const favourite = isFavourite(listingId);
  const label = favourite
    ? t("marketplaceBuy.actions.unfavourite")
    : t("marketplaceBuy.actions.favourite");

  return (
    <Button
      variant={favourite ? "default" : "outline"}
      size="sm"
      aria-pressed={favourite}
      aria-label={label}
      title={label}
      onClick={() => toggle(listingId)}
    >
      <Heart
        className={cn("size-4", favourite && "fill-current")}
        aria-hidden
      />
      {favourite
        ? t("marketplaceBuy.actions.favourited")
        : t("marketplaceBuy.actions.favourite")}
    </Button>
  );
}
