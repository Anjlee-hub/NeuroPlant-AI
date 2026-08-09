import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Heart, HeartCrack, Loader2, ShoppingBag, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { BuyerListingCard } from "@/components/marketplace/buyer-listing-card";
import { ProductListingCard } from "@/components/marketplace/product-listing-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { FAVOURITES_KEY } from "@/lib/favourites";
import { useAuth } from "@/stores/auth";
import type { Favourite } from "@/types/trust";

/**
 * Saved items (M4 Task 6) at /marketplace/favorites — every crop listing and
 * product the caller has favourited, newest first, rendered with the exact same
 * cards as the browse grids so they read identically. Each card carries a remove
 * button (the owner-only DELETE /marketplace/favorites/{id}); the list refetches
 * on any button toggle via the shared FAVOURITES_KEY, so a save on a detail page
 * appears here immediately.
 */
export function MarketplaceFavoritesPage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const favouritesQuery = useQuery({
    queryKey: FAVOURITES_KEY,
    queryFn: () => api.listFavourites(),
    enabled: !!user,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={Heart} title={t("favourites.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("favourites.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const favourites = favouritesQuery.data;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
          <Heart className="size-7 text-brand-600 dark:text-brand-400" aria-hidden />
          {t("favourites.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("favourites.subtitle")}</p>
      </header>

      <div className="mt-6">
        {favouritesQuery.isPending ? (
          <FavouritesSkeleton />
        ) : favouritesQuery.isError || !favourites ? (
          <StateCard
            icon={HeartCrack}
            title={t("favourites.errorTitle")}
            body={t("favourites.errorBody")}
            tone="destructive"
          >
            <Button variant="outline" onClick={() => void favouritesQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : favourites.length === 0 ? (
          <StateCard icon={Heart} title={t("favourites.emptyTitle")} body={t("favourites.emptyBody")}>
            <Button asChild>
              <Link to="/marketplace/browse">
                <ShoppingBag className="size-4" aria-hidden />
                {t("favourites.browseMarketplace")}
              </Link>
            </Button>
          </StateCard>
        ) : (
          <FavouritesGrid favourites={favourites} />
        )}
      </div>
    </div>
  );
}

function FavouritesGrid({ favourites }: { favourites: Favourite[] }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const remove = useMutation({
    mutationFn: (favouriteId: number) => api.removeFavourite(favouriteId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: FAVOURITES_KEY }),
  });

  return (
    <ul
      aria-label={t("favourites.listLabel")}
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {favourites.map((favourite) => (
        <li key={favourite.id} className="relative">
          {favourite.listing ? (
            <BuyerListingCard listing={favourite.listing} />
          ) : favourite.product ? (
            <ProductListingCard product={favourite.product} />
          ) : null}
          <Button
            size="icon"
            variant="outline"
            className="absolute right-2 top-2 bg-background/90 backdrop-blur"
            aria-label={t("favourites.removeItem")}
            aria-busy={remove.isPending && remove.variables === favourite.id}
            disabled={remove.isPending}
            onClick={() => remove.mutate(favourite.id)}
          >
            {remove.isPending && remove.variables === favourite.id ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Trash2 className="size-4" aria-hidden />
            )}
          </Button>
        </li>
      ))}
    </ul>
  );
}

function FavouritesSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {Array.from({ length: 6 }, (_, i) => (
        <Skeleton key={i} className="aspect-[4/5] w-full rounded-lg" />
      ))}
    </div>
  );
}
