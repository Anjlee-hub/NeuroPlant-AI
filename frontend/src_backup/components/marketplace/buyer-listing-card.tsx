import { ArrowRight, MapPin, Store } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { AvailabilityBadge } from "@/components/marketplace/availability-badge";
import { Badge } from "@/components/ui/badge";
import { formatDateOnly } from "@/lib/format";
import type { CropListing } from "@/types/marketplace";

/**
 * One listing in the customer browse grid (M4 Task 3). The whole card is a
 * link to the detail page; it shows what a shopper needs at a glance — photo,
 * crop + variety, category, organic, price per unit, quantity, harvest date,
 * availability and the farmer's location. Images lazy-load so a large grid
 * doesn't stall first paint, and the card is one tab stop (the link).
 */
export function BuyerListingCard({ listing }: { listing: CropListing }) {
  const { t, i18n } = useTranslation();
  const unitLabel = t(`marketplace.units.${listing.unit}`);

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-lg border bg-card transition-shadow hover:shadow-md">
      <Link
        to={`/marketplace/listings/${listing.id}`}
        className="group flex h-full flex-col focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label={t("marketplaceBuy.card.viewDetails")}
      >
        <div className="aspect-square w-full overflow-hidden bg-muted">
          {listing.images?.[0] ? (
            <img
              src={listing.images[0]}
              alt={listing.crop_name}
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-muted-foreground">
              <Store className="size-10" aria-hidden />
            </div>
          )}
        </div>

        <div className="flex flex-1 flex-col gap-1.5 p-3">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-semibold leading-snug">{listing.crop_name}</h3>
            <AvailabilityBadge availability={listing.availability} />
          </div>

          {listing.variety && (
            <p className="text-sm text-muted-foreground">{listing.variety}</p>
          )}

          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="secondary">
              {t(`marketplace.categories.${listing.category}`)}
            </Badge>
            {listing.organic && (
              <Badge variant="success">{t("marketplace.card.organic")}</Badge>
            )}
          </div>

          <p className="mt-1 text-lg font-bold">
            {listing.price}
            <span className="text-sm font-normal">
              {t("marketplaceBuy.card.perUnit", { unit: unitLabel })}
            </span>
          </p>

          <p className="text-sm text-muted-foreground">
            {t("marketplaceBuy.card.quantity", {
              quantity: listing.quantity,
              unit: unitLabel,
            })}
          </p>

          {listing.harvest_date && (
            <p className="text-sm text-muted-foreground">
              {t("marketplaceBuy.card.harvestDate", {
                date: formatDateOnly(listing.harvest_date, i18n.language),
              })}
            </p>
          )}

          {listing.location && (
            <p className="inline-flex items-center gap-1 text-sm text-muted-foreground">
              <MapPin className="size-3.5 shrink-0" aria-hidden />
              {listing.location}
            </p>
          )}

          <span className="mt-auto inline-flex items-center gap-1 pt-2 text-sm font-medium text-brand-600 dark:text-brand-400">
            {t("marketplaceBuy.card.viewDetails")}
            <ArrowRight className="size-4" aria-hidden />
          </span>
        </div>
      </Link>
    </article>
  );
}
