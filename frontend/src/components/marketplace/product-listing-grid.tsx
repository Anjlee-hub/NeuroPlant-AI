import { useTranslation } from "react-i18next";

import { ProductListingCard } from "@/components/marketplace/product-listing-card";
import type { Product } from "@/types/marketplace";

/** Responsive grid of product listing cards (M4 Task 4). 1 → 2 → 3 columns as
 * viewport grows; the caller owns fetching/pagination/empty states. */
export function ProductListingGrid({ products }: { products: Product[] }) {
  const { t } = useTranslation();
  return (
    <section
      aria-label={t("productMarket.grid.listLabel")}
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {products.map((product) => (
        <ProductListingCard key={product.id} product={product} />
      ))}
    </section>
  );
}