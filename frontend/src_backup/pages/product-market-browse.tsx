import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  Check,
  GitCompareArrows,
  ShoppingBag,
  Store,
  X,
} from "lucide-react";
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
import type { Product, ProductQuery } from "@/types/marketplace";

export const PRODUCT_MARKET_BROWSE_KEY = ["product-market-browse"] as const;

const MAX_COMPARE_PRODUCTS = 3;

export function ProductMarketBrowsePage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const [filters, setFilters] = useState<ProductMarketFilters>({
    ...DEFAULT_PRODUCT_MARKET_FILTERS,
    availability: "in_stock",
  });
  const [page, setPage] = useState(1);
  const [selectedProducts, setSelectedProducts] = useState<Product[]>([]);
  const [showComparison, setShowComparison] = useState(false);

  const handleFiltersChange = (next: ProductMarketFilters) => {
    setFilters(next);
    setPage(1);
  };

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

  const toggleCompare = (product: Product) => {
    setSelectedProducts((current) => {
      const alreadySelected = current.some((item) => item.id === product.id);

      if (alreadySelected) {
        return current.filter((item) => item.id !== product.id);
      }

      if (current.length >= MAX_COMPARE_PRODUCTS) {
        return current;
      }

      return [...current, product];
    });
    setShowComparison(false);
  };

  const clearComparison = () => {
    setSelectedProducts([]);
    setShowComparison(false);
  };

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

      {data?.items && data.items.length > 0 && (
        <section className="mt-6 rounded-xl border p-4">
          <h2 className="text-lg font-semibold">
            Recommended Products
          </h2>
          <p className="mb-4 text-sm text-muted-foreground">
            Explore available products selected from the current results.
          </p>
          <ProductListingGrid products={data.items.slice(0, 3)} />
        </section>
      )}

      <div className="mt-6 flex flex-col gap-5">
        <ProductMarketFilterBar
          filters={filters}
          onChange={handleFiltersChange}
        />

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
            {/* Product comparison selection */}
            <section className="rounded-xl border bg-card p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="flex items-center gap-2 font-semibold">
                    <GitCompareArrows className="size-5" />
                    Compare products
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Select up to 3 products from this page to compare their
                    prices, brands, stock and other details.
                  </p>
                </div>
                <span className="text-sm font-medium">
                  {selectedProducts.length}/{MAX_COMPARE_PRODUCTS} selected
                </span>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {data.items.map((product) => {
                  const selected = selectedProducts.some(
                    (item) => item.id === product.id,
                  );
                  const limitReached =
                    selectedProducts.length >= MAX_COMPARE_PRODUCTS;

                  return (
                    <Button
                      key={product.id}
                      size="sm"
                      variant={selected ? "default" : "outline"}
                      disabled={!selected && limitReached}
                      onClick={() => toggleCompare(product)}
                    >
                      {selected ? (
                        <Check className="mr-1 size-4" />
                      ) : (
                        <GitCompareArrows className="mr-1 size-4" />
                      )}
                      {product.name}
                    </Button>
                  );
                })}
              </div>

              {selectedProducts.length > 0 && (
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <Button
                    onClick={() => setShowComparison((current) => !current)}
                    disabled={selectedProducts.length < 2}
                  >
                    <GitCompareArrows className="mr-2 size-4" />
                    {showComparison ? "Hide comparison" : "Compare selected"}
                  </Button>
                  <Button variant="ghost" onClick={clearComparison}>
                    <X className="mr-1 size-4" />
                    Clear selection
                  </Button>
                  {selectedProducts.length < 2 && (
                    <span className="text-sm text-muted-foreground">
                      Select at least 2 products to compare.
                    </span>
                  )}
                </div>
              )}

              {showComparison && selectedProducts.length >= 2 && (
                <div className="mt-5 overflow-x-auto">
                  <h3 className="mb-3 font-semibold">Product comparison</h3>
                  <table className="w-full min-w-[600px] border-collapse text-sm">
                    <thead>
                      <tr>
                        <th className="border p-3 text-left">Feature</th>
                        {selectedProducts.map((product) => (
                          <th
                            key={product.id}
                            className="border p-3 text-left"
                          >
                            {product.name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <ComparisonRow
                        label="Price"
                        products={selectedProducts}
                        value={(p) =>
                          `${Number(p.price).toFixed(2)} / ${p.unit}`
                        }
                      />
                      <ComparisonRow
                        label="Category"
                        products={selectedProducts}
                        value={(p) => p.category}
                      />
                      <ComparisonRow
                        label="Brand"
                        products={selectedProducts}
                        value={(p) => p.brand || "Not specified"}
                      />
                      <ComparisonRow
                        label="Manufacturer"
                        products={selectedProducts}
                        value={(p) => p.manufacturer || "Not specified"}
                      />
                      <ComparisonRow
                        label="Organic"
                        products={selectedProducts}
                        value={(p) => (p.organic ? "Yes" : "No")}
                      />
                      <ComparisonRow
                        label="Availability"
                        products={selectedProducts}
                        value={(p) => p.availability.replaceAll("_", " ")}
                      />
                      <ComparisonRow
                        label="Stock quantity"
                        products={selectedProducts}
                        value={(p) =>
                          p.stock_quantity === null
                            ? "Not specified"
                            : String(p.stock_quantity)
                        }
                      />
                      <ComparisonRow
                        label="Description"
                        products={selectedProducts}
                        value={(p) => p.description || "Not specified"}
                      />
                      <ComparisonRow
                        label="Usage instructions"
                        products={selectedProducts}
                        value={(p) =>
                          p.usage_instructions || "Not specified"
                        }
                      />
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <p className="text-sm text-muted-foreground" aria-live="polite">
              {t("productMarket.resultsCount", { count: data.total })}
            </p>

            <div
              aria-busy={browseQuery.isFetching}
              className="transition-opacity"
            >
              <ProductListingGrid products={data.items} />
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

function ComparisonRow({
  label,
  products,
  value,
}: {
  label: string;
  products: Product[];
  value: (product: Product) => string;
}) {
  return (
    <tr>
      <th className="border p-3 text-left font-medium">{label}</th>
      {products.map((product) => (
        <td key={product.id} className="border p-3">
          {value(product)}
        </td>
      ))}
    </tr>
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
