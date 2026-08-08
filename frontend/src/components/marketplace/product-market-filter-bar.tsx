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
 * Server-side filters + sort for the public product market browse page (M4 Task 4).
 * Mirrors BuyerFilterBar but for products:
 * - Search by name/brand/description/manufacturer
 * - Category filter (5 product categories)
 * - Organic filter
 * - Availability filter (excludes archived by default)
 * - Price range (min/max)
 * - Brand filter (free text)
 * - Sort: newest, oldest, price_asc, price_desc
 */
export interface ProductMarketFilters {
  q: string;
  category: ProductCategory | "all";
  organic: boolean;
  availability: ProductAvailability | "all";
  min_price: string;
  max_price: string;
  brand: string;
  sort: ProductQuery["sort"];
}

export const DEFAULT_PRODUCT_MARKET_FILTERS: ProductMarketFilters = {
  q: "",
  category: "all",
  organic: false,
  availability: "all",
  min_price: "",
  max_price: "",
  brand: "",
  sort: "newest",
};

export function hasActiveProductMarketFilters(f: ProductMarketFilters): boolean {
  return (
    f.q !== "" ||
    f.category !== "all" ||
    f.organic ||
    f.availability !== "all" ||
    f.min_price !== "" ||
    f.max_price !== "" ||
    f.brand !== "" ||
    f.sort !== "newest"
  );
}

const SORT_OPTIONS: NonNullable<ProductQuery["sort"]>[] = [
  "newest",
  "oldest",
  "price_asc",
  "price_desc",
];

export function toProductMarketQuery(
  filters: ProductMarketFilters,
  page: number,
): ProductQuery {
  const price = (raw: string) => {
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : undefined;
  };
  return {
    q: filters.q.trim() || undefined,
    category: filters.category === "all" ? undefined : filters.category,
    organic: filters.organic || undefined,
    availability: filters.availability === "all" ? undefined : filters.availability,
    min_price: price(filters.min_price),
    max_price: price(filters.max_price),
    brand: filters.brand.trim() || undefined,
    sort: filters.sort,
    page,
  };
}

export function ProductMarketFilterBar({
  filters,
  onChange,
}: {
  filters: ProductMarketFilters;
  onChange: (next: ProductMarketFilters) => void;
}) {
  const { t } = useTranslation();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const active = hasActiveProductMarketFilters(filters);

  const set = <K extends keyof ProductMarketFilters>(
    key: K,
    value: ProductMarketFilters[K],
  ) => onChange({ ...filters, [key]: value });

  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
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
            placeholder={t("productMarket.filter.searchPlaceholder")}
            className="pl-9"
            aria-label={t("productMarket.filter.searchPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pm-sort" className="sr-only">
            {t("productMarket.sort.label")}
          </Label>
          <Select
            id="pm-sort"
            value={filters.sort}
            onChange={(e) => set("sort", e.target.value as ProductMarketFilters["sort"])}
          >
            {SORT_OPTIONS.map((sort) => (
              <option key={sort} value={sort}>
                {t(`productMarket.sort.${sort}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pm-category" className="sr-only">
            {t("productMarket.filter.categoryLabel")}
          </Label>
          <Select
            id="pm-category"
            value={filters.category}
            onChange={(e) =>
              set("category", e.target.value as ProductCategory | "all")
            }
          >
            <option value="all">{t("productMarket.filter.categoryAll")}</option>
            {PRODUCT_CATEGORY_OPTIONS.map((category) => (
              <option key={category} value={category}>
                {t(`sellerPortal.categories.${category}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pm-availability" className="sr-only">
            {t("productMarket.filter.availabilityLabel")}
          </Label>
          <Select
            id="pm-availability"
            value={filters.availability}
            onChange={(e) =>
              set("availability", e.target.value as ProductAvailability | "all")
            }
          >
            <option value="all">
              {t("productMarket.filter.availabilityAll")}
            </option>
            {PRODUCT_AVAILABILITY_OPTIONS.map((availability) => (
              <option key={availability} value={availability}>
                {t(`sellerPortal.availability.${availability}`)}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {advancedOpen && (
        <div className="grid gap-3 rounded-md border bg-muted/30 p-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="pm-min-price" className="text-xs">
              {t("productMarket.filter.minPrice")}
            </Label>
            <Input
              id="pm-min-price"
              type="number"
              min={0}
              value={filters.min_price}
              onChange={(e) => set("min_price", e.target.value)}
              placeholder={t("productMarket.filter.minPrice")}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="pm-max-price" className="text-xs">
              {t("productMarket.filter.maxPrice")}
            </Label>
            <Input
              id="pm-max-price"
              type="number"
              min={0}
              value={filters.max_price}
              onChange={(e) => set("max_price", e.target.value)}
              placeholder={t("productMarket.filter.maxPrice")}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="pm-brand" className="text-xs">
              {t("productMarket.filter.brandPlaceholder")}
            </Label>
            <Input
              id="pm-brand"
              type="search"
              value={filters.brand}
              onChange={(e) => set("brand", e.target.value)}
              placeholder={t("productMarket.filter.brandPlaceholder")}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">{t("productMarket.filter.organicLabel")}</Label>
            <Select
              id="pm-organic"
              value={filters.organic ? "true" : "false"}
              onChange={(e) => set("organic", e.target.value === "true")}
            >
              <option value="false">{t("common.all")}</option>
              <option value="true">{t("common.yes")}</option>
            </Select>
          </div>
        </div>
      )}

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
            onClick={() => onChange(DEFAULT_PRODUCT_MARKET_FILTERS)}
          >
            <X className="size-3.5" aria-hidden />
            {t("productMarket.filter.clear")}
          </Button>
        )}
      </div>
    </div>
  );
}