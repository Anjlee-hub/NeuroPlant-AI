import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, MapPin, Store } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { AvailabilityBadge } from "@/components/marketplace/availability-badge";
import { ContactSellerButton } from "@/components/messages/contact-seller-button";
import { CopyLinkButton } from "@/components/marketplace/copy-link-button";
import { FavouriteButton } from "@/components/marketplace/favourite-button";
import { ListingGallery } from "@/components/marketplace/listing-gallery";
import { ReviewSection } from "@/components/marketplace/review-section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { formatDate, formatDateOnly } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import type { CropListingDetail } from "@/types/marketplace";

/**
 * Buyer listing detail (M4 Task 3) at /marketplace/listings/:id. Loads the
 * single listing with its farmer attached, shows the full photo gallery with a
 * lightbox, every field the seller entered, and the buyer actions — save to
 * favourites (server-backed, M4 Task 6), copy the shareable link, and Contact
 * Farmer (M4 Task 5) which opens a real message thread with the listing's
 * farmer. Ratings & reviews for the listing render below the detail grid.
 */

export const MARKETPLACE_DETAIL_KEY = ["marketplace-listing-detail"] as const;

export function MarketplaceListingDetailPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { listingId } = useParams<{ listingId: string }>();
  const id = Number(listingId);
  const validId = Number.isInteger(id) && id > 0;

  const detailQuery = useQuery({
    queryKey: [...MARKETPLACE_DETAIL_KEY, id],
    queryFn: () => api.getCropListing(id),
    enabled: !!user && validId,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={Store} title={t("marketplaceBuy.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("marketplaceBuy.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  if (!validId) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={Store} title={t("marketplaceBuy.errorTitle")} body={t("marketplaceBuy.errorBody")}>
          <Button asChild variant="outline">
            <Link to="/marketplace/browse">{t("marketplaceBuy.detail.back")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link
        to="/marketplace/browse"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <span aria-hidden>←</span>
        {t("marketplaceBuy.detail.back")}
      </Link>

      <div className="mt-4">
        {detailQuery.isPending ? (
          <DetailSkeleton />
        ) : detailQuery.isError || !detailQuery.data ? (
          <StateCard
            icon={Store}
            title={t("marketplaceBuy.errorTitle")}
            body={t("marketplaceBuy.errorBody")}
            tone="destructive"
          >
            <Button variant="outline" onClick={() => void detailQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : (
          <ListingDetail listing={detailQuery.data} />
        )}
      </div>
    </div>
  );
}

function ListingDetail({ listing }: { listing: CropListingDetail }) {
  const { t, i18n } = useTranslation();
  const unitLabel = t(`marketplace.units.${listing.unit}`);
  const images = listing.images ?? [];

  return (
    <div>
      <div className="grid gap-8 lg:grid-cols-2">
      <ListingGallery images={images} name={listing.crop_name} />

      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <AvailabilityBadge availability={listing.availability} />
          <Badge variant="secondary">
            {t(`marketplace.categories.${listing.category}`)}
          </Badge>
          {listing.organic ? (
            <Badge variant="success">{t("marketplaceBuy.detail.organic")}</Badge>
          ) : (
            <Badge variant="outline">{t("marketplaceBuy.detail.notOrganic")}</Badge>
          )}
        </div>

        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            {listing.crop_name}
          </h1>
          {listing.variety && (
            <p className="mt-1 text-base text-muted-foreground">{listing.variety}</p>
          )}
        </div>

        <p className="text-3xl font-bold">
          {listing.price}
          <span className="text-lg font-normal">
            {t("marketplaceBuy.card.perUnit", { unit: unitLabel })}
          </span>
        </p>

        {listing.description && (
          <section aria-label={t("marketplaceBuy.detail.descriptionLabel")}>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {t("marketplaceBuy.detail.descriptionLabel")}
            </h2>
            <p className="mt-1 text-sm text-foreground/90 whitespace-pre-line">
              {listing.description}
            </p>
          </section>
        )}

        <dl className="rounded-lg border bg-muted/30 px-4 py-2">
          <DetailRow
            label={t("marketplaceBuy.detail.quantity")}
            value={`${listing.quantity} ${unitLabel}`}
          />
          {listing.harvest_date && (
            <DetailRow
              label={t("marketplaceBuy.detail.harvestDate")}
              value={formatDateOnly(listing.harvest_date, i18n.language)}
            />
          )}
          <DetailRow
            label={t("marketplaceBuy.detail.listedOn")}
            value={formatDate(listing.created_at, i18n.language)}
          />
          {listing.location && (
            <DetailRow
              label={t("marketplaceBuy.detail.location")}
              value={
                <span className="inline-flex items-center gap-1">
                  <MapPin className="size-3.5" aria-hidden />
                  {listing.location}
                </span>
              }
            />
          )}
        </dl>

        {/* Farmer block + buyer actions. */}
        <Card>
          <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div className="flex items-center gap-3">
              <span className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
                <Store className="size-5" aria-hidden />
              </span>
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  {t("marketplaceBuy.detail.farmer")}
                </p>
                <p className="flex items-center gap-1.5 font-semibold">
                  {listing.farmer.name}
                  {listing.farmer.verified && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 dark:text-brand-400">
                      <BadgeCheck className="size-4" aria-hidden />
                      {t("marketplaceBuy.detail.verified")}
                    </span>
                  )}
                </p>
              </div>
            </div>
            <ContactSellerButton
              label={t("marketplaceBuy.actions.contactFarmer")}
              listingId={listing.id}
            />
          </CardContent>
        </Card>

        <div className="flex flex-wrap items-center gap-2">
          <FavouriteButton listingId={listing.id} />
          <CopyLinkButton url={window.location.href} />
        </div>
      </div>
    </div>

    <ReviewSection listingId={listing.id} />
  </div>
  );
}

function DetailRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  );
}

function DetailSkeleton() {
  const { t } = useTranslation();
  return (
    <div
      role="status"
      aria-label={t("marketplaceBuy.detail.back")}
      className="grid gap-8 lg:grid-cols-2"
    >
      <Skeleton className="aspect-square w-full rounded-lg" />
      <div className="flex flex-col gap-3">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
    </div>
  );
}
