import {
  Archive,
  Loader2,
  Pencil,
  Trash2,
  RefreshCw,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { ProductAvailabilityBadge } from "@/components/marketplace/availability-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Product, ProductAvailability } from "@/types/marketplace";

/**
 * One product on the seller's dashboard (M4 Task 4).
 * Mirrors ListingCard but with seller-specific actions:
 * - Stock toggle: in_stock ↔ out_of_stock
 * - Archive: moves to archived
 * - Edit: opens ProductForm
 * - Delete: removes product
 * Availability badge shows current status.
 */
export function ProductCard({
  product,
  busy = false,
  onEdit,
  onAvailability,
  onDelete,
}: {
  product: Product;
  /** True while a status/delete mutation for this product is in flight. */
  busy?: boolean;
  onEdit: (product: Product) => void;
  onAvailability: (product: Product, availability: ProductAvailability) => void;
  onDelete: (product: Product) => void;
}) {
  const { t } = useTranslation();
  const unitLabel = t(`marketplace.units.${product.unit}`);
  const archived = product.availability === "archived";
  const inStock = product.availability === "in_stock";

  // Determine available stock actions based on current availability
  const canToggleStock = !archived;
  const nextStockStatus: ProductAvailability = inStock ? "out_of_stock" : "in_stock";
  const toggleLabel = inStock
    ? t("sellerPortal.card.markOutOfStock")
    : t("sellerPortal.card.markInStock");

  return (
    <article className="flex flex-col gap-4 rounded-lg border bg-card p-4 sm:flex-row sm:items-center">
      {/* Photo / placeholder — first image, else an honest empty slot. */}
      <div className="aspect-square w-full shrink-0 overflow-hidden rounded-md bg-muted sm:w-24">
        {product.images?.[0] ? (
          <img
            src={product.images[0]}
            alt={product.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-muted-foreground">
            <span className="text-3xl">📦</span>
          </div>
        )}
      </div>

      {/* Core details. */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-semibold">{product.name}</h3>
          {product.brand && (
            <span className="text-sm text-muted-foreground">{product.brand}</span>
          )}
          <Badge variant="secondary">{t(`sellerPortal.categories.${product.category}`)}</Badge>
          {product.organic && <Badge variant="success">{t("sellerPortal.card.organic")}</Badge>}
          <ProductAvailabilityBadge availability={product.availability} />
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <span className="text-lg font-bold text-foreground">
            {product.price}
            <span className="text-sm font-normal">{t("sellerPortal.card.perUnit", { unit: unitLabel })}</span>
          </span>
          {product.stock_quantity != null && (
            <span>{t("sellerPortal.card.stock", { quantity: product.stock_quantity, unit: unitLabel })}</span>
          )}
        </div>

        {product.description && (
          <p className="mt-2 text-sm line-clamp-2 text-muted-foreground">{product.description}</p>
        )}
      </div>

      {/* Seller actions — contextual status toggles + edit/delete. */}
      <div className="flex flex-wrap items-center gap-2 sm:flex-col sm:items-end">
        {busy ? (
          <Loader2 className="size-5 animate-spin text-muted-foreground" aria-label={t("common.loading")} />
        ) : (
          <>
            {canToggleStock && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAvailability(product, nextStockStatus)}
              >
                <RefreshCw className="size-4" aria-hidden />
                {toggleLabel}
              </Button>
            )}
            {!archived && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAvailability(product, "archived")}
              >
                <Archive className="size-4" aria-hidden />
                {t("sellerPortal.card.archive")}
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => onEdit(product)}>
              <Pencil className="size-4" aria-hidden />
              {t("sellerPortal.card.edit")}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onDelete(product)}>
              <Trash2 className="size-4" aria-hidden />
              {t("sellerPortal.card.delete")}
            </Button>
          </>
        )}
      </div>
    </article>
  );
}