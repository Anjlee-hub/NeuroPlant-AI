import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Store } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { FilterBar } from "@/components/marketplace/filter-bar";
import {
  DEFAULT_LISTING_FILTERS,
  type ListingDateRange,
  type ListingFilters,
} from "@/components/marketplace/filter-bar";
import { ListingCard } from "@/components/marketplace/listing-card";
import { StatsCards } from "@/components/marketplace/stats-cards";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import type { CropAvailability, CropListing } from "@/types/marketplace";

/**
 * Farmer Crop Listing dashboard (M4 Task 2) — the farmer's own listings at a
 * glance. Stats cards (total / active / sold / archived) come from the stats
 * endpoint; filters + search are applied client-side over the farmer's own
 * list (the backend still owns every business rule). Actions hit the same
 * PATCH/DELETE endpoints the rest of the marketplace uses; on success both
 * the list and the stats are invalidated so the four counts stay honest.
 */

export const MARKETPLACE_LISTINGS_KEY = ["marketplace-listings"] as const;
export const MARKETPLACE_STATS_KEY = ["marketplace-stats"] as const;

/** 1 day / 7 days / 30 days in ms for the "listed" filter windows. */
const DAY_MS = 24 * 60 * 60 * 1000;

export function MarketplaceDashboardPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ListingFilters>(DEFAULT_LISTING_FILTERS);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const listingsQuery = useQuery({
    queryKey: MARKETPLACE_LISTINGS_KEY,
    queryFn: () => api.myCropListings(),
    enabled: !!user,
  });
  const statsQuery = useQuery({
    queryKey: MARKETPLACE_STATS_KEY,
    queryFn: () => api.getCropListingStats(),
    enabled: !!user,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: MARKETPLACE_LISTINGS_KEY });
    queryClient.invalidateQueries({ queryKey: MARKETPLACE_STATS_KEY });
  };

  const availabilityMutation = useMutation({
    mutationFn: ({ id, availability }: { id: number; availability: CropAvailability }) =>
      api.updateCropListing(id, { availability }),
    onMutate: ({ id }) => {
      setActionError(null);
      setBusyId(id);
    },
    onSuccess: () => invalidate(),
    onError: () => setActionError(t("marketplace.actions.error")),
    onSettled: () => setBusyId(null),
  });

  const deleteMutation = useMutation({
    mutationFn: (listing: CropListing) => api.deleteCropListing(listing.id),
    onMutate: (listing) => {
      setActionError(null);
      setBusyId(listing.id);
    },
    onSuccess: () => invalidate(),
    onError: () => setActionError(t("marketplace.actions.error")),
    onSettled: () => setBusyId(null),
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={Store} title={t("marketplace.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("marketplace.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const handleAvailability = (listing: CropListing, availability: CropAvailability) => {
    if (availability === "archived") {
      const ok = window.confirm(
        `${t("marketplace.actions.confirmArchive")}\n${t("marketplace.actions.confirmArchiveBody")}`,
      );
      if (!ok) return;
    }
    availabilityMutation.mutate({ id: listing.id, availability });
  };

  const handleDelete = (listing: CropListing) => {
    const ok = window.confirm(
      `${t("marketplace.actions.confirmDelete")}\n${t("marketplace.actions.confirmDeleteBody")}`,
    );
    if (!ok) return;
    deleteMutation.mutate(listing);
  };

  const listings = listingsQuery.data ?? [];
  const filtered = listings.filter((listing) => matchesFilters(listing, filters));

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
            <Store className="size-7 text-brand-600 dark:text-brand-400" />
            {t("marketplace.title")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("marketplace.subtitle")}</p>
        </div>
        <Button onClick={() => navigate("/marketplace/listings/new")}>
          <Plus className="size-4" aria-hidden />
          {t("marketplace.newListing")}
        </Button>
      </header>

      <div className="mt-6 flex flex-col gap-6">
        {statsQuery.isPending || listingsQuery.isPending ? (
          <DashboardSkeleton />
        ) : statsQuery.isError || listingsQuery.isError ? (
          <StateCard icon={Store} title={t("marketplace.errorTitle")} body={t("marketplace.errorBody")} tone="destructive">
            <Button variant="outline" onClick={() => void listingsQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : (
          <>
            {statsQuery.data && <StatsCards stats={statsQuery.data} />}

            <FilterBar filters={filters} onChange={setFilters} />

            {actionError && <p className="text-sm text-destructive">{actionError}</p>}

            {filtered.length === 0 ? (
              listings.length === 0 ? (
                <StateCard icon={Store} title={t("marketplace.empty")}>
                  <Button onClick={() => navigate("/marketplace/listings/new")}>
                    <Plus className="size-4" aria-hidden />
                    {t("marketplace.newListing")}
                  </Button>
                </StateCard>
              ) : (
                <p className="rounded-md border bg-muted/40 p-6 text-center text-sm text-muted-foreground">
                  {t("marketplace.filter.noResults")}
                </p>
              )
            ) : (
              <section className="flex flex-col gap-4">
                {filtered.map((listing) => (
                  <ListingCard
                    key={listing.id}
                    listing={listing}
                    busy={busyId === listing.id}
                    onEdit={(l) => navigate(`/marketplace/listings/${l.id}/edit`)}
                    onAvailability={handleAvailability}
                    onDelete={handleDelete}
                  />
                ))}
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/** Client-side filter predicate over the farmer's own listings. */
function matchesFilters(listing: CropListing, filters: ListingFilters): boolean {
  if (filters.status !== "all" && listing.availability !== filters.status) return false;
  if (filters.category !== "all" && listing.category !== filters.category) return false;
  if (filters.organic && !listing.organic) return false;
  if (!matchesListed(listing.created_at, filters.listed)) return false;

  const q = filters.search.trim().toLowerCase();
  if (!q) return true;
  return [listing.crop_name, listing.variety, listing.description, listing.location]
    .filter((s): s is string => Boolean(s))
    .some((s) => s.toLowerCase().includes(q));
}

function matchesListed(createdAt: string, range: ListingDateRange): boolean {
  if (range === "all") return true;
  const age = Date.now() - new Date(createdAt).getTime();
  if (range === "today") return age < DAY_MS;
  if (range === "week") return age < 7 * DAY_MS;
  return age < 30 * DAY_MS;
}

function DashboardSkeleton() {
  const { t } = useTranslation();
  return (
    <div role="status" aria-label={t("marketplace.title")} className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-28 w-full" />
    </div>
  );
}
