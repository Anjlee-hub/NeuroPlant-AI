import { Search, SlidersHorizontal, X } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type {
  ProductAvailability,
  ProductCategory,
  ProductQuery,
} from "@/types/marketplace";
import { PRODUCT_AVAILABILITY_OPTIONS, PRODUCT_CATEGORY_OPTIONS } from "@/types/marketplace";

/**
 * Server-side filters + sort for the seller's product list (M4 Task 4).
 * Mirrors BuyerFilterBar but tailored for seller dashboard:
 * - Search by name/brand
 * - Category filter
 * - Organic filter
 * - Availability filter (includes archived)
 * - No price/harvest/location filters for seller's own products
 * - Sort options matching public browse
 */
export interface SellerProductFilters {
  q: string;
  category: ProductCategory | "all";
  organic: boolean;
  availability: ProductAvailability | "all";
  sort: ProductQuery["sort"];
}

export const DEFAULT_SELLER_FILTERS: SellerProductFilters = {
  q: "",
  category: "all",
  organic: false,
  availability: "all",
  sort: "newest",
};

export function hasActiveSellerFilters(f: SellerProductFilters): boolean {
  return (
    f.q !== "" ||
    f.category !== "all" ||
    f.organic ||
    f.availability !== "all" ||
    f.sort !== "newest"
  );
}

const SORT_OPTIONS: NonNullable<ProductQuery["sort"]>[] = [
  "newest",
  "oldest",
  "price_asc",
  "price_desc",
];

export function toSellerProductQuery(
  filters: SellerProductFilters,
  page: number,
): ProductQuery {
  return {
    q: filters.q.trim() || undefined,
    category: filters.category === "all" ? undefined : filters.category,
    organic: filters.organic || undefined,
    availability: filters.availability === "all" ? undefined : filters.availability,
    sort: filters.sort,
    page,
  };
}

export function SellerProductFilterBar({
  filters,
  onChange,
}: {
  filters: SellerProductFilters;
  onChange: (next: SellerProductFilters) => void;
}) {
  const { t } = useTranslation();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const active = hasActiveSellerFilters(filters);

  const set = <K extends keyof SellerProductFilters>(
    key: K,
    value: SellerProductFilters[K],
  ) => onChange({ ...filters, [key]: value });

  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* Search — spans two columns on desktop. */}
        <div className="relative sm:col-span-2">
          <Search
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            type="search"
            value={filters.q}
            onChange={(e) => set("q", e.target.value)}
            placeholder={t("sellerPortal.filter.searchPlaceholder")}
            className="pl-9"
            aria-label={t("sellerPortal.filter.searchPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="sell-sort" className="sr-only">
            {t("productMarket.sort.label")}
          </Label>
          <Select
            id="sell-sort"
            value={filters.sort}
            onChange={(e) => set("sort", e.target.value as SellerProductFilters["sort"])}
          >
            {SORT_OPTIONS.map((sort) => (
              <option key={sort} value={sort}>
                {t(`productMarket.sort.${sort}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="sell-category" className="sr-only">
            {t("sellerPortal.filter.categoryLabel")}
          </Label>
          <Select
            id="sell-category"
            value={filters.category}
            onChange={(e) =>
              set("category", e.target.value as ProductCategory | "all")
            }
          >
            <option value="all">{t("sellerPortal.filter.categoryAll")}</option>
            {PRODUCT_CATEGORY_OPTIONS.map((category) => (
              <option key={category} value={category}>
                {t(`sellerPortal.categories.${category}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="sell-availability" className="sr-only">
            {t("sellerPortal.filter.statusLabel")}
          </Label>
          <Select
            id="sell-availability"
            value={filters.availability}
            onChange={(e) =>
              set("availability", e.target.value as ProductAvailability | "all")
            }
          >
            <option value="all">{t("sellerPortal.filter.statusAll")}</option>
            {PRODUCT_AVAILABILITY_OPTIONS.map((availability) => (
              <option key={availability} value={availability}>
                {t(`sellerPortal.availability.${availability}`)}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          aria-expanded={advancedOpen}
          onClick={() => setAdvancedOpen((open) => !open)}
        >
          <SlidersHorizontal className="size-4" aria-hidden />
          {t("productMarket.filter.showFilters")}
        </Button>
        {active && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onChange(DEFAULT_SELLER_FILTERS)}
          >
            <X className="size-3.5" aria-hidden />
            {t("productMarket.filter.clear")}
          </Button>
        )}
      </div>
    </div>
  );
}