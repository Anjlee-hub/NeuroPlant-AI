import {
  Archive,
  BadgeCheck,
  Loader2,
  MapPin,
  Pencil,
  Store,
  Trash2,
  X,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { AvailabilityBadge } from "@/components/marketplace/availability-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { CropAvailability, CropListing } from "@/types/marketplace";

/**
 * One crop listing on the farmer's dashboard (M4 Task 2). Shows every field
 * customers care about (photo, crop + variety, category, organic, price per
 * unit, quantity, location, availability) plus the farmer's actions. The
 * buttons are contextual: sold / available are a status flip (PATCH
 * availability), archive retires a listing, edit opens the form, delete
 * removes it. Mutations live in the page — the card only reports intents.
 */
export function ListingCard({
  listing,
  busy = false,
  onEdit,
  onAvailability,
  onDelete,
}: {
  listing: CropListing;
  /** True while a status/delete mutation for this listing is in flight. */
  busy?: boolean;
  onEdit: (listing: CropListing) => void;
  onAvailability: (listing: CropListing, availability: CropAvailability) => void;
  onDelete: (listing: CropListing) => void;
}) {
  const { t } = useTranslation();
  const unitLabel = t(`marketplace.units.${listing.unit}`);
  const archived = listing.availability === "archived";

  return (
    <article className="flex flex-col gap-4 rounded-lg border bg-card p-4 sm:flex-row sm:items-center">
      {/* Photo / placeholder — first image, else an honest empty slot. */}
      <div className="aspect-square w-full shrink-0 overflow-hidden rounded-md bg-muted sm:w-24">
        {listing.images?.[0] ? (
          <img
            src={listing.images[0]}
            alt={listing.crop_name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-muted-foreground">
            <Store className="size-8" aria-hidden />
          </div>
        )}
      </div>

      {/* Core details. */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-semibold">{listing.crop_name}</h3>
          {listing.variety && (
            <span className="text-sm text-muted-foreground">{listing.variety}</span>
          )}
          <Badge variant="secondary">{t(`marketplace.categories.${listing.category}`)}</Badge>
          {listing.organic && <Badge variant="success">{t("marketplace.card.organic")}</Badge>}
          <AvailabilityBadge availability={listing.availability} />
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <span className="text-lg font-bold text-foreground">
            {listing.price}
            <span className="text-sm font-normal">{t("marketplace.card.perUnit", { unit: unitLabel })}</span>
          </span>
          <span>{t("marketplace.card.quantity", { quantity: listing.quantity, unit: unitLabel })}</span>
          {listing.location && (
            <span className="inline-flex items-center gap-1">
              <MapPin className="size-3.5" aria-hidden />
              {listing.location}
            </span>
          )}
        </div>
      </div>

      {/* Farmer actions — contextual status flips + edit/delete. */}
      <div className="flex flex-wrap items-center gap-2 sm:flex-col sm:items-end">
        {busy ? (
          <Loader2 className="size-5 animate-spin text-muted-foreground" aria-label={t("common.loading")} />
        ) : (
          <>
            {!archived && listing.availability !== "sold_out" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAvailability(listing, "sold_out")}
              >
                <BadgeCheck className="size-4" aria-hidden />
                {t("marketplace.card.markSold")}
              </Button>
            )}
            {listing.availability === "sold_out" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAvailability(listing, "available")}
              >
                <X className="size-4" aria-hidden />
                {t("marketplace.card.markAvailable")}
              </Button>
            )}
            {!archived && (
              <Button variant="outline" size="sm" onClick={() => onAvailability(listing, "archived")}>
                <Archive className="size-4" aria-hidden />
                {t("marketplace.card.archive")}
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => onEdit(listing)}>
              <Pencil className="size-4" aria-hidden />
              {t("marketplace.card.edit")}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onDelete(listing)}>
              <Trash2 className="size-4" aria-hidden />
              {t("marketplace.card.delete")}
            </Button>
          </>
        )}
      </div>
    </article>
  );
}
