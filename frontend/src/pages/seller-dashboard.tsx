import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Clock3,
  MapPin,
  Pencil,
  Phone,
  Plus,
  Store,
  Truck,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { ProductCard } from "@/components/marketplace/product-card";
import { ProductForm } from "@/components/marketplace/product-form";
import { ProductStatsCards } from "@/components/marketplace/product-stats-cards";
import { SellerInquiriesSection } from "@/components/messages/seller-inquiries-section";
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
import type { Product, ProductAvailability, SellerProfile } from "@/types/marketplace";

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
  const [editingProfile, setEditingProfile] = useState(false);

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
  const shopMissing = shopQuery.isError && isNotFoundError(shopQuery.error);
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
        ) : (shopQuery.isError && !shopMissing) || productsQuery.isError || statsQuery.isError ? (
          <StateCard icon={Store} title={t("sellerPortal.errorTitle")} body={t("sellerPortal.errorBody")} tone="destructive">
            <Button variant="outline" onClick={() => void shopQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : (
          <>
            {!shop || editingProfile ? (
              <section aria-labelledby="shop-profile-heading" className="rounded-xl border bg-card p-5 sm:p-6">
                <h2 id="shop-profile-heading" className="mb-5 text-lg font-semibold">
                  {shop ? t("sellerPortal.editProfile") : t("sellerPortal.profile.title")}
                </h2>
                <ShopProfileForm
                  shop={shop ?? null}
                  showCancel={!!shop}
                  onSaved={(saved) => {
                    queryClient.setQueryData(SELLER_SHOP_KEY, saved);
                    setEditingProfile(false);
                  }}
                  onCancel={() => setEditingProfile(false)}
                />
              </section>
            ) : (
              <Storefront
                shop={shop}
                onEdit={() => setEditingProfile(true)}
                onAddProduct={handleNewProduct}
              />
            )}

            {shop && statsQuery.data && <ProductStatsCards stats={statsQuery.data} />}

            <SellerInquiriesSection currentUserId={user.id} />

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
              <section aria-labelledby="shop-products-heading" className="flex flex-col gap-4">
                <h2 id="shop-products-heading" className="text-xl font-semibold">
                  {t("sellerPortal.storefront.catalog")}
                </h2>
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
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
                </div>
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
            invalidate();
            setShowProductForm({ open: false, product: undefined });
          }}
        />
      )}
    </div>
  );
}

function Storefront({
  shop,
  onEdit,
  onAddProduct,
}: {
  shop: SellerProfile;
  onEdit: () => void;
  onAddProduct: () => void;
}) {
  const { t } = useTranslation();

  return (
    <section aria-labelledby="storefront-heading" className="overflow-hidden rounded-xl border bg-card shadow-sm">
      <div className="relative h-40 bg-gradient-to-r from-brand-800 to-brand-600 sm:h-56">
        {shop.banner_url && (
          <img
            src={shop.banner_url}
            alt=""
            className="absolute inset-0 size-full object-cover"
          />
        )}
      </div>
      <div className="px-5 pb-5 sm:px-7 sm:pb-7">
        <div className="-mt-12 flex flex-wrap items-end justify-between gap-4">
          <div className="flex size-24 items-center justify-center overflow-hidden rounded-xl border-4 border-card bg-card shadow-md sm:size-28">
            {shop.logo_url ? (
              <img src={shop.logo_url} alt={t("sellerPortal.storefront.logoAlt")} className="size-full object-cover" />
            ) : (
              <Store className="size-10 text-brand-700 dark:text-brand-300" aria-hidden />
            )}
          </div>
          <div className="flex flex-wrap gap-2 pb-1">
            <Button variant="outline" onClick={onEdit}>
              <Pencil className="size-4" aria-hidden />
              {t("sellerPortal.editProfile")}
            </Button>
            <Button onClick={onAddProduct}>
              <Plus className="size-4" aria-hidden />
              {t("sellerPortal.addProduct")}
            </Button>
          </div>
        </div>

        <div className="mt-4">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="storefront-heading" className="text-2xl font-bold tracking-tight">
              {shop.shop_name || shop.owner_name}
            </h2>
            <Badge variant={shop.delivery_available ? "success" : "secondary"}>
              <Truck className="mr-1 size-3.5" aria-hidden />
              {t(
                shop.delivery_available
                  ? "sellerPortal.storefront.deliveryAvailable"
                  : "sellerPortal.storefront.deliveryUnavailable",
              )}
            </Badge>
          </div>
          {shop.description && (
            <p className="mt-2 max-w-3xl whitespace-pre-line text-sm text-muted-foreground">
              {shop.description}
            </p>
          )}
        </div>

        <dl className="mt-6 grid gap-4 border-t pt-5 sm:grid-cols-3">
          <StorefrontDetail
            icon={MapPin}
            label={t("sellerPortal.profile.addressLabel")}
            value={shop.address || t("sellerPortal.storefront.notProvided")}
          />
          <StorefrontDetail
            icon={Phone}
            label={t("sellerPortal.profile.phoneLabel")}
            value={shop.phone || t("sellerPortal.storefront.notProvided")}
          />
          <StorefrontDetail
            icon={Clock3}
            label={t("sellerPortal.profile.openingHoursLabel")}
            value={shop.opening_hours || t("sellerPortal.storefront.notProvided")}
          />
        </dl>
      </div>
    </section>
  );
}

function StorefrontDetail({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="flex min-w-0 items-start gap-3">
      <Icon className="mt-0.5 size-4 shrink-0 text-brand-700 dark:text-brand-300" aria-hidden />
      <div className="min-w-0">
        <dt className="text-xs text-muted-foreground">{label}</dt>
        <dd className="mt-0.5 break-words text-sm font-medium">{value}</dd>
      </div>
    </div>
  );
}

function isNotFoundError(error: unknown): boolean {
  return error instanceof Error && "status" in error && error.status === 404;
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