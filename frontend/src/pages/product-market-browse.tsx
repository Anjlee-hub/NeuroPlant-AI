import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ShoppingBag, Store } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ProductListingGrid } from "@/components/marketplace/product-listing-grid";
import {
  DEFAULT_PRODUCT_MARKET_FILTERS,
  ProductMarketFilterBar,
  toProductMarketQuery,
  type ProductMarketFilters,
} from "@/components/marketplace/product-market-filter-bar";
import { Pagination } from "@/components/marketplace/pagination";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import type { ProductQuery } from "@/types/marketplace";

/**
 * Public product market browse (M4 Task 4) — browse every seller product,
 * search by name, filter by category / organic / availability / price / brand,
 * and sort by newest / oldest / price. All of that is server-side: the filter
 * state is mapped to browse API query params and the backend paginates, so the
 * page never holds more than one page of products. `keepPreviousData` keeps the
 * grid on screen between fetches (no layout jump), and the query key includes
 * the full query so each filter combo is cached by React Query.
 */

export const PRODUCT_MARKET_BROWSE_KEY = ["product-market-browse"] as const;

export function ProductMarketBrowsePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [filters, setFilters] = useState<ProductMarketFilters>({
    ...DEFAULT_PRODUCT_MARKET_FILTERS,
    availability: "in_stock",
  });
  const [page, setPage] = useState(1);

  const handleFiltersChange = (next: ProductMarketFilters) => {
    setFilters(next);
    setPage(1); // A new filter set starts back at the first page.
  };

  // Build the ProductQuery object for the API — reuse the filter bar's mapper
  // so the string→number price conversion stays in one place.
  const queryParams: ProductQuery = {
    ...toProductMarketQuery(filters, page),
    page_size: 12,
  };

  const browseQuery = useQuery({
    queryKey: [...PRODUCT_MARKET_BROWSE_KEY, queryParams],
    queryFn: () => api.browseProducts(queryParams),
    placeholderData: keepPreviousData,
    enabled: !!user,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={Store} title={t("productMarket.authRequired")}>
          <a href="/login" className="text-brand-600 hover:underline">
            {t("productMarket.signIn")}
          </a>
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
          {t("productMarket.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("productMarket.subtitle")}
        </p>
      </header>

      <div className="mt-6 flex flex-col gap-5">
        <ProductMarketFilterBar filters={filters} onChange={handleFiltersChange} />

        {browseQuery.isPending ? (
          <BrowseSkeleton />
        ) : browseQuery.isError || !data ? (
          <StateCard
            icon={ShoppingBag}
            title={t("productMarket.errorTitle")}
            body={t("productMarket.errorBody")}
            tone="destructive"
          >
            <Button variant="outline" onClick={() => void browseQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : data.items.length === 0 ? (
          <StateCard icon={ShoppingBag} title={t("productMarket.noResults")} />
        ) : (
          <>
            <p className="text-sm text-muted-foreground" aria-live="polite">
              {t("productMarket.resultsCount", { count: data.total })}
            </p>
            <div aria-busy={browseQuery.isFetching} className="transition-opacity">
              <ProductListingGrid products={data.items} />
            </div>
            <Pagination page={data.page} pages={data.pages} onPageChange={setPage} />
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
      aria-label={t("productMarket.title")}
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-72 w-full" />
      ))}
    </div>
  );
}