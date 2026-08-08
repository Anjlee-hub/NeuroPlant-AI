import { ArrowRight, Leaf } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ProductAvailabilityBadge } from "@/components/marketplace/availability-badge";
import { Badge } from "@/components/ui/badge";
import type { Product } from "@/types/marketplace";

/**
 * One product in the public product market browse grid (M4 Task 4).
 * Mirrors BuyerListingCard but for agricultural inputs:
 * - Photo, product name, brand, category, organic badge
 * - Price per unit
 * - Availability badge
 * - Link to detail page
 */
export function ProductListingCard({ product }: { product: Product }) {
  const { t } = useTranslation();
  const unitLabel = t(`marketplace.units.${product.unit}`);

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-lg border bg-card transition-shadow hover:shadow-md">
      <Link
        to={`/marketplace/products/${product.id}`}
        className="group flex h-full flex-col focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label={t("productMarket.card.viewDetails")}
      >
        <div className="aspect-square w-full overflow-hidden bg-muted">
          {product.images?.[0] ? (
            <img
              src={product.images[0]}
              alt={product.name}
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-muted-foreground">
              <Leaf className="size-10" aria-hidden />
            </div>
          )}
        </div>

        <div className="flex flex-1 flex-col gap-1.5 p-3">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-semibold leading-snug">{product.name}</h3>
            <ProductAvailabilityBadge availability={product.availability} />
          </div>

          {product.brand && (
            <p className="text-sm text-muted-foreground">{product.brand}</p>
          )}

          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="secondary">
              {t(`sellerPortal.categories.${product.category}`)}
            </Badge>
            {product.organic && (
              <Badge variant="success">{t("productMarket.card.organic")}</Badge>
            )}
          </div>

          <p className="mt-1 text-lg font-bold">
            {product.price}
            <span className="text-sm font-normal">
              {t("productMarket.card.perUnit", { unit: unitLabel })}
            </span>
          </p>

          {product.availability === "out_of_stock" && (
            <p className="text-sm text-destructive">
              {t("productMarket.card.outOfStock")}
            </p>
          )}

          <span className="mt-auto inline-flex items-center gap-1 pt-2 text-sm font-medium text-brand-600 dark:text-brand-400">
            {t("productMarket.card.viewDetails")}
            <ArrowRight className="size-4" aria-hidden />
          </span>
        </div>
      </Link>
    </article>
  );
}