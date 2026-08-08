import { useQuery } from "@tanstack/react-query";
import { Store } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { ProductAvailabilityBadge } from "@/components/marketplace/availability-badge";
import { ProductListingGallery } from "@/components/marketplace/product-listing-gallery";
import { ContactSellerButton } from "@/components/messages/contact-seller-button";
import { CopyLinkButton } from "@/components/marketplace/copy-link-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import type { ProductDetail } from "@/types/marketplace";

/**
 * Public product market detail (M4 Task 4) at /marketplace/products/:id. Loads
 * the single product with its seller shop attached, shows the full photo gallery
 * with a lightbox, every field the seller entered, and buyer actions — copy the
 * shareable link and Contact Seller (M4 Task 5) which opens a real message
 * thread with the product's shop.
 */

export const PRODUCT_MARKET_DETAIL_KEY = ["product-market-detail"] as const;

export function ProductMarketDetailPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { id: idParam } = useParams<{ id: string }>();
  const id = Number(idParam);
  const validId = Number.isInteger(id) && id > 0;

  const detailQuery = useQuery({
    queryKey: [...PRODUCT_MARKET_DETAIL_KEY, id],
    queryFn: () => api.getProduct(id),
    enabled: !!user && validId,
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

  if (!validId) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={Store} title={t("productMarket.errorTitle")} body={t("productMarket.errorBody")}>
          <Button asChild variant="outline">
            <Link to="/marketplace/products">{t("productMarket.detail.back")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link
        to="/marketplace/products"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <span aria-hidden>←</span>
        {t("productMarket.detail.back")}
      </Link>

      <div className="mt-4">
        {detailQuery.isPending ? (
          <DetailSkeleton />
        ) : detailQuery.isError || !detailQuery.data ? (
          <StateCard
            icon={Store}
            title={t("productMarket.errorTitle")}
            body={t("productMarket.errorBody")}
            tone="destructive"
          >
            <Button variant="outline" onClick={() => void detailQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : (
          <ProductMarketDetail product={detailQuery.data} />
        )}
      </div>
    </div>
  );
}

function ProductMarketDetail({ product }: { product: ProductDetail }) {
  const { t, i18n } = useTranslation();
  const unitLabel = t(`marketplace.units.${product.unit}`);
  const images = product.images ?? [];

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <ProductListingGallery images={images} name={product.name} />

      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <ProductAvailabilityBadge availability={product.availability} />
          <Badge variant="secondary">
            {t(`sellerPortal.categories.${product.category}`)}
          </Badge>
          {product.organic ? (
            <Badge variant="success">{t("productMarket.card.organic")}</Badge>
          ) : (
            <Badge variant="outline">{t("productMarket.card.notOrganic")}</Badge>
          )}
        </div>

        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            {product.name}
          </h1>
          {product.brand && (
            <p className="mt-1 text-base text-muted-foreground">{product.brand}</p>
          )}
        </div>

        <p className="text-3xl font-bold">
          {product.price}
          <span className="text-lg font-normal">
            {t("productMarket.card.perUnit", { unit: unitLabel })}
          </span>
        </p>

        {product.description && (
          <section aria-label={t("productMarket.detail.descriptionLabel")}>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {t("productMarket.detail.descriptionLabel")}
            </h2>
            <p className="mt-1 text-sm text-foreground/90 whitespace-pre-line">
              {product.description}
            </p>
          </section>
        )}

        {product.manufacturer && (
          <section aria-label={t("productMarket.detail.manufacturerLabel")}>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {t("productMarket.detail.manufacturerLabel")}
            </h2>
            <p className="mt-1 text-sm text-foreground/90">{product.manufacturer}</p>
          </section>
        )}

        {product.usage_instructions && (
          <section aria-label={t("productMarket.detail.usageLabel")}>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {t("productMarket.detail.usageLabel")}
            </h2>
            <p className="mt-1 text-sm text-foreground/90 whitespace-pre-line">
              {product.usage_instructions}
            </p>
          </section>
        )}

        <dl className="rounded-lg border bg-muted/30 px-4 py-2">
          <DetailRow
            label={t("productMarket.detail.stockQuantity")}
            value={`${product.stock_quantity} ${unitLabel}`}
          />
          <DetailRow
            label={t("productMarket.detail.listedOn")}
            value={formatDate(product.created_at, i18n.language)}
          />
          {product.shop && (
            <DetailRow
              label={t("productMarket.detail.seller")}
              value={
                <span className="inline-flex items-center gap-1">
                  <Store className="size-3.5" aria-hidden />
                  {product.shop.shop_name}
                </span>
              }
            />
          )}
        </dl>

        {/* Seller block + buyer actions. */}
        {product.shop && (
          <Card>
            <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div className="flex items-center gap-3">
                <span className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <Store className="size-5" aria-hidden />
                </span>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {t("productMarket.detail.seller")}
                  </p>
                  <p className="font-semibold">{product.shop.shop_name}</p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <CopyLinkButton url={window.location.href} />
                <ContactSellerButton
                  label={t("productMarket.detail.contactSeller")}
                  productId={product.id}
                />
              </div>
            </CardContent>
          </Card>
        )}
      </div>
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
      aria-label={t("productMarket.detail.back")}
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