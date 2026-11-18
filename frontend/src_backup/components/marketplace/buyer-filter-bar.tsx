import { Search, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type {
  CropAvailability,
  CropCategory,
  CropListingQuery,
  CropListingSort,
} from "@/types/marketplace";
import { CROP_AVAILABILITY_OPTIONS } from "@/types/marketplace";

/**
 * Server-side filters + sort for the buyer browse page (M4 Task 3). Unlike the
 * farmer dashboard's client-side FilterBar, every control here feeds a query
 * param that the backend applies (browse_crops) — the page turns this state
 * into a `CropListingQuery` via `toBrowseQuery` and refetches. The advanced
 * price / harvest-date / location row is collapsed behind a toggle so the main
 * controls stay one glance tall on mobile.
 */

/** UI filter state for the browse page (stringly-typed inputs, converted to a
 * query before hitting the API). */
export interface BuyerFilters {
  q: string;
  category: CropCategory | "all";
  organic: boolean;
  availability: CropAvailability | "all";
  min_price: string;
  max_price: string;
  harvest_from: string;
  harvest_to: string;
  location: string;
  sort: CropListingSort;
}

export const DEFAULT_BUYER_FILTERS: BuyerFilters = {
  q: "",
  category: "all",
  organic: false,
  availability: "all",
  min_price: "",
  max_price: "",
  harvest_from: "",
  harvest_to: "",
  location: "",
  sort: "newest",
};

/** True when any filter (other than sort) deviates from the default — controls
 * whether the "Clear filters" affordance shows. */
export function hasActiveFilters(f: BuyerFilters): boolean {
  return (
    f.q !== "" ||
    f.category !== "all" ||
    f.organic ||
    f.availability !== "all" ||
    f.min_price !== "" ||
    f.max_price !== "" ||
    f.harvest_from !== "" ||
    f.harvest_to !== "" ||
    f.location !== ""
  );
}

const SORT_OPTIONS: CropListingSort[] = [
  "newest",
  "oldest",
  "price_asc",
  "price_desc",
];

const CROP_CATEGORIES: CropCategory[] = [
  "vegetable",
  "fruit",
  "grain",
  "pulses",
  "spice",
  "other",
];

/** Convert the UI filter state to the browse API's query params. Page is added
 * by the caller. Undefined values are dropped (the client skips empty params). */
export function toBrowseQuery(
  filters: BuyerFilters,
  page: number,
): CropListingQuery {
  const price = (raw: string) => {
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : undefined;
  };
  return {
    q: filters.q.trim() || undefined,
    category: filters.category === "all" ? undefined : filters.category,
    organic: filters.organic || undefined,
    availability:
      filters.availability === "all" ? undefined : filters.availability,
    min_price: price(filters.min_price),
    max_price: price(filters.max_price),
    harvest_from: filters.harvest_from || undefined,
    harvest_to: filters.harvest_to || undefined,
    location: filters.location.trim() || undefined,
    sort: filters.sort,
    page,
  };
}

export function BuyerFilterBar({
  filters,
  onChange,
}: {
  filters: BuyerFilters;
  onChange: (next: BuyerFilters) => void;
}) {
  const { t } = useTranslation();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const active = hasActiveFilters(filters);

  const set = <K extends keyof BuyerFilters>(
    key: K,
    value: BuyerFilters[K],
  ) => onChange({ ...filters, [key]: value });

  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {/* Search — spans two columns so it keeps its width on desktop. */}
        <div className="relative sm:col-span-2">
          <Search
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            type="search"
            value={filters.q}
            onChange={(e) => set("q", e.target.value)}
            placeholder={t("marketplaceBuy.filter.searchPlaceholder")}
            className="pl-9"
            aria-label={t("marketplaceBuy.filter.searchPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="buy-sort" className="sr-only">
            {t("marketplaceBuy.sort.label")}
          </Label>
          <Select
            id="buy-sort"
            value={filters.sort}
            onChange={(e) => set("sort", e.target.value as CropListingSort)}
          >
            {SORT_OPTIONS.map((sort) => (
              <option key={sort} value={sort}>
                {t(`marketplaceBuy.sort.${sort}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="buy-category" className="sr-only">
            {t("marketplaceBuy.filter.categoryLabel")}
          </Label>
          <Select
            id="buy-category"
            value={filters.category}
            onChange={(e) =>
              set("category", e.target.value as CropCategory | "all")
            }
          >
            <option value="all">{t("marketplaceBuy.filter.categoryAll")}</option>
            {CROP_CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {t(`marketplace.categories.${category}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="buy-availability" className="sr-only">
            {t("marketplaceBuy.filter.availabilityLabel")}
          </Label>
          <Select
            id="buy-availability"
            value={filters.availability}
            onChange={(e) =>
              set("availability", e.target.value as CropAvailability | "all")
            }
          >
            <option value="all">
              {t("marketplaceBuy.filter.availabilityAll")}
            </option>
            {CROP_AVAILABILITY_OPTIONS.map((availability) => (
              <option key={availability} value={availability}>
                {t(`marketplace.availability.${availability}`)}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {advancedOpen && (
        <div className="grid gap-3 rounded-md border bg-muted/30 p-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="buy-min-price" className="text-xs">
              {t("marketplaceBuy.filter.minPrice")}
            </Label>
            <Input
              id="buy-min-price"
              type="number"
              min={0}
              value={filters.min_price}
              onChange={(e) => set("min_price", e.target.value)}
              placeholder={t("marketplaceBuy.filter.minPrice")}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="buy-max-price" className="text-xs">
              {t("marketplaceBuy.filter.maxPrice")}
            </Label>
            <Input
              id="buy-max-price"
              type="number"
              min={0}
              value={filters.max_price}
              onChange={(e) => set("max_price", e.target.value)}
              placeholder={t("marketplaceBuy.filter.maxPrice")}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="buy-harvest-from" className="text-xs">
              {t("marketplaceBuy.filter.harvestFrom")}
            </Label>
            <Input
              id="buy-harvest-from"
              type="date"
              value={filters.harvest_from}
              onChange={(e) => set("harvest_from", e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="buy-harvest-to" className="text-xs">
              {t("marketplaceBuy.filter.harvestTo")}
            </Label>
            <Input
              id="buy-harvest-to"
              type="date"
              value={filters.harvest_to}
              onChange={(e) => set("harvest_to", e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="buy-location" className="text-xs">
              {t("marketplaceBuy.filter.locationPlaceholder")}
            </Label>
            <Input
              id="buy-location"
              type="search"
              value={filters.location}
              onChange={(e) => set("location", e.target.value)}
              placeholder={t("marketplaceBuy.filter.locationPlaceholder")}
            />
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
          {t("marketplaceBuy.filter.showFilters")}
        </Button>
        {active && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onChange(DEFAULT_BUYER_FILTERS)}
          >
            {t("marketplaceBuy.filter.clear")}
          </Button>
        )}
      </div>
    </div>
  );
}
