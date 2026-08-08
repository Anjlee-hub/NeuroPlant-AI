import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Store } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ProductCard } from "@/components/marketplace/product-card";
import { ProductForm } from "@/components/marketplace/product-form";
import { ProductStatsCards } from "@/components/marketplace/product-stats-cards";
import {
  DEFAULT_SELLER_FILTERS,
  SellerProductFilterBar,
  type SellerProductFilters,
} from "@/components/marketplace/seller-product-filter-bar";
import { ShopProfileForm } from "@/components/marketplace/shop-profile-form";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import type { Product, ProductAvailability } from "@/types/marketplace";

/**
 * Seller portal dashboard (M4 Task 4) — the seller's shop profile, product
 * catalog, and stats at a glance. Stats cards (total / in_stock / out_of_stock
 * / archived) come from the stats endpoint; filters + search are applied
 * client-side over the seller's own list. Actions hit the same PATCH/DELETE
 * endpoints the marketplace uses; on success both the list and the stats are
 * invalidated so the four counts stay honest.
 */

export const SELLER_PRODUCTS_KEY = ["seller-products"] as const;
export const SELLER_STATS_KEY = ["seller-stats"] as const;
export const SELLER_SHOP_KEY = ["seller-shop"] as const;

export function SellerDashboardPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<SellerProductFilters>(DEFAULT_SELLER_FILTERS);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showProductForm, setShowProductForm] = useState<{
    open: boolean;
    product?: Product;
  }>({ open: false, product: undefined });

  const shopQuery = useQuery({
    queryKey: SELLER_SHOP_KEY,
    queryFn: () => api.getMyShop(),
    enabled: !!user,
  });
  const productsQuery = useQuery({
    queryKey: SELLER_PRODUCTS_KEY,
    queryFn: () => api.myProducts(),
    enabled: !!user,
  });
  const statsQuery = useQuery({
    queryKey: SELLER_STATS_KEY,
    queryFn: () => api.getProductStats(),
    enabled: !!user,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: SELLER_PRODUCTS_KEY });
    queryClient.invalidateQueries({ queryKey: SELLER_STATS_KEY });
    queryClient.invalidateQueries({ queryKey: SELLER_SHOP_KEY });
  };

  const availabilityMutation = useMutation({
    mutationFn: ({ id, availability }: { id: number; availability: ProductAvailability }) =>
      api.updateProduct(id, { availability }),
    onMutate: ({ id }) => {
      setActionError(null);
      setBusyId(id);
    },
    onSuccess: () => invalidate(),
    onError: () => setActionError(t("sellerPortal.actions.error")),
    onSettled: () => setBusyId(null),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteProduct(id),
    onMutate: (id) => {
      setActionError(null);
      setBusyId(id);
    },
    onSuccess: () => invalidate(),
    onError: () => setActionError(t("sellerPortal.actions.error")),
    onSettled: () => setBusyId(null),
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={Store} title={t("sellerPortal.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("sellerPortal.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const handleAvailability = (product: Product, availability: ProductAvailability) => {
    if (availability === "archived") {
      const ok = window.confirm(
        `${t("sellerPortal.actions.confirmArchive")}\n${t("sellerPortal.actions.confirmArchiveBody")}`,
      );
      if (!ok) return;
    }
    availabilityMutation.mutate({ id: product.id, availability });
  };

  const handleDelete = (product: Product) => {
    const ok = window.confirm(
      `${t("sellerPortal.actions.confirmDelete")}\n${t("sellerPortal.actions.confirmDeleteBody")}`,
    );
    if (!ok) return;
    deleteMutation.mutate(product.id);
  };

  const handleEdit = (product: Product) => {
    setShowProductForm({ open: true, product });
  };

  const handleNewProduct = () => {
    setShowProductForm({ open: true, product: undefined });
  };

  const shop = shopQuery.data;
  const products = productsQuery.data ?? [];
  const filtered = products.filter((product) => matchesFilters(product, filters));

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
            <Store className="size-7 text-brand-600 dark:text-brand-400" />
            {t("sellerPortal.title")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("sellerPortal.subtitle")}</p>
        </div>
        <Button onClick={handleNewProduct}>
          <Plus className="size-4" aria-hidden />
          {t("sellerPortal.addProduct")}
        </Button>
      </header>

      <div className="mt-6 flex flex-col gap-6">
        {shopQuery.isPending || productsQuery.isPending || statsQuery.isPending ? (
          <DashboardSkeleton />
        ) : shopQuery.isError || productsQuery.isError || statsQuery.isError ? (
          <StateCard icon={Store} title={t("sellerPortal.errorTitle")} body={t("sellerPortal.errorBody")} tone="destructive">
            <Button variant="outline" onClick={() => void shopQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : (
          <>
            {shop && (
              <section aria-labelledby="shop-profile-heading">
                <h2 id="shop-profile-heading" className="text-lg font-semibold">
                  {t("sellerPortal.profile.title")}
                </h2>
                <ShopProfileForm
                  shop={shop}
                  onSaved={(saved) => {
                    queryClient.setQueryData(SELLER_SHOP_KEY, saved);
                  }}
                  onCancel={() => {}}
                />
              </section>
            )}

            {statsQuery.data && <ProductStatsCards stats={statsQuery.data} />}

            <SellerProductFilterBar filters={filters} onChange={setFilters} />

            {actionError && <p className="text-sm text-destructive">{actionError}</p>}

            {filtered.length === 0 ? (
              products.length === 0 ? (
                <StateCard icon={Store} title={t("sellerPortal.empty")}>
                  <Button onClick={handleNewProduct}>
                    <Plus className="size-4" aria-hidden />
                    {t("sellerPortal.addProduct")}
                  </Button>
                </StateCard>
              ) : (
                <p className="rounded-md border bg-muted/40 p-6 text-center text-sm text-muted-foreground">
                  {t("sellerPortal.filter.noResults")}
                </p>
              )
            ) : (
              <section className="flex flex-col gap-4">
                {filtered.map((product) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    busy={busyId === product.id}
                    onEdit={handleEdit}
                    onAvailability={handleAvailability}
                    onDelete={handleDelete}
                  />
                ))}
              </section>
            )}
          </>
        )}
      </div>

      {showProductForm.open && (
        <ProductForm
          product={showProductForm.product}
          onCancel={() => setShowProductForm({ open: false, product: undefined })}
          onSaved={() => {
            // The form submits to the API itself; on save we refresh the
            // catalog + stats and close the dialog.
            invalidate();
            setShowProductForm({ open: false, product: undefined });
          }}
        />
      )}
    </div>
  );
}

/** Client-side filter predicate over the seller's own products. */
function matchesFilters(product: Product, filters: SellerProductFilters): boolean {
  if (filters.availability !== "all" && product.availability !== filters.availability) return false;
  if (filters.category !== "all" && product.category !== filters.category) return false;
  if (filters.organic && !product.organic) return false;

  const q = filters.q.trim().toLowerCase();
  if (!q) return true;
  return [
    product.name,
    product.brand,
    product.description,
    product.category,
    product.manufacturer,
  ]
    .filter((s): s is string => Boolean(s))
    .some((s) => s.toLowerCase().includes(q));
}

function DashboardSkeleton() {
  const { t } = useTranslation();
  return (
    <div role="status" aria-label={t("sellerPortal.title")} className="flex flex-col gap-6">
      <Skeleton className="h-24 w-full" />
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