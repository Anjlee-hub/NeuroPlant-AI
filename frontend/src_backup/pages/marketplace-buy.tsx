import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ShoppingBag } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import {
  BuyerFilterBar,
  DEFAULT_BUYER_FILTERS,
  hasActiveFilters,
  toBrowseQuery,
  type BuyerFilters,
} from "@/components/marketplace/buyer-filter-bar";
import { BuyerListingGrid } from "@/components/marketplace/buyer-listing-grid";
import { Pagination } from "@/components/marketplace/pagination";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { useAuth } from "@/stores/auth";

/**
 * Buyer marketplace storefront (M4 Task 3) — browse every farm listing, search
 * by crop name, filter by category / organic / availability / price / harvest
 * date / location, and sort by newest / oldest / price. All of that is
 * server-side: the filter state is mapped to browse API query params and the
 * backend paginates, so the page never holds more than one page of listings.
 * `keepPreviousData` keeps the grid on screen between fetches (no layout
 * jump), and the query key includes the full query so each filter combo is
 * cached by React Query.
 */

export const MARKETPLACE_BROWSE_KEY = ["marketplace-browse"] as const;

export function MarketplaceBuyPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [filters, setFilters] = useState<BuyerFilters>(DEFAULT_BUYER_FILTERS);
  const [page, setPage] = useState(1);

  const handleFiltersChange = (next: BuyerFilters) => {
    setFilters(next);
    setPage(1); // A new filter set starts back at the first page.
  };

  const query = toBrowseQuery(filters, page);
  const browseQuery = useQuery({
    queryKey: [...MARKETPLACE_BROWSE_KEY, query],
    queryFn: () => api.browseCrops(query),
    placeholderData: keepPreviousData,
    enabled: !!user,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={ShoppingBag} title={t("marketplaceBuy.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("marketplaceBuy.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const data = browseQuery.data;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
          <ShoppingBag className="size-7 text-brand-600 dark:text-brand-400" />
          {t("marketplaceBuy.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("marketplaceBuy.subtitle")}
        </p>
      </header>

      <div className="mt-6 flex flex-col gap-5">
        <BuyerFilterBar filters={filters} onChange={handleFiltersChange} />

        {browseQuery.isPending ? (
          <BrowseSkeleton />
        ) : browseQuery.isError || !data ? (
          <StateCard
            icon={ShoppingBag}
            title={t("marketplaceBuy.errorTitle")}
            body={t("marketplaceBuy.errorBody")}
            tone="destructive"
          >
            <Button variant="outline" onClick={() => void browseQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : data.items.length === 0 ? (
          hasActiveFilters(filters) ? (
            <StateCard
              icon={ShoppingBag}
              title={t("marketplaceBuy.noResults")}
            />
          ) : (
            <StateCard icon={ShoppingBag} title={t("marketplaceBuy.empty")} />
          )
        ) : (
          <>
            <p className="text-sm text-muted-foreground" aria-live="polite">
              {t("marketplaceBuy.resultsCount", { count: data.total })}
            </p>
            <div aria-busy={browseQuery.isFetching} className="transition-opacity">
              <BuyerListingGrid listings={data.items} />
            </div>
            <Pagination
              page={data.page}
              pages={data.pages}
              onPageChange={setPage}
            />
          </>
        )}
      </div>
    </div>
  );
}

function BrowseSkeleton() {
  const { t } = useTranslation();
  return (
    <div
      role="status"
      aria-label={t("marketplaceBuy.title")}
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-72 w-full" />
      ))}
    </div>
  );
}
