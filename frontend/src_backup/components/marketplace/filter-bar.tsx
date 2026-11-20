import { Search } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type { CropAvailability, CropCategory } from "@/types/marketplace";
import { CROP_AVAILABILITY_OPTIONS } from "@/types/marketplace";

/**
 * Client-side filters for the farmer's own listings (M4 Task 2): text search
 * plus status / category / organic / listed-date. The dashboard owns the
 * state (so filters and the listing list share one source of truth) and the
 * FilterBar only reports changes. Filtering is applied over the farmer's own
 * list — the backend still owns every business rule.
 */

/** Date-window options for the "listed" filter (matched against created_at). */
export type ListingDateRange = "all" | "today" | "week" | "month";

export interface ListingFilters {
  /** Case-insensitive search over crop name / variety / description / location. */
  search: string;
  status: CropAvailability | "all";
  category: CropCategory | "all";
  organic: boolean;
  listed: ListingDateRange;
}

export const DEFAULT_LISTING_FILTERS: ListingFilters = {
  search: "",
  status: "all",
  category: "all",
  organic: false,
  listed: "all",
};

const CROP_CATEGORIES: CropCategory[] = [
  "vegetable",
  "fruit",
  "grain",
  "pulses",
  "spice",
  "other",
];

export function FilterBar({
  filters,
  onChange,
}: {
  filters: ListingFilters;
  onChange: (next: ListingFilters) => void;
}) {
  const { t } = useTranslation();

  const set = <K extends keyof ListingFilters>(key: K, value: ListingFilters[K]) =>
    onChange({ ...filters, [key]: value });

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <div className="relative sm:col-span-2">
        <Search
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <Input
          type="search"
          value={filters.search}
          onChange={(e) => set("search", e.target.value)}
          placeholder={t("marketplace.filter.searchPlaceholder")}
          className="pl-9"
          aria-label={t("marketplace.filter.searchPlaceholder")}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="mp-status" className="sr-only">
          {t("marketplace.filter.statusLabel")}
        </Label>
        <Select
          id="mp-status"
          value={filters.status}
          onChange={(e) => set("status", e.target.value as ListingFilters["status"])}
        >
          <option value="all">{t("marketplace.filter.statusAll")}</option>
          {CROP_AVAILABILITY_OPTIONS.map((status) => (
            <option key={status} value={status}>
              {t(`marketplace.availability.${status}`)}
            </option>
          ))}
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="mp-category" className="sr-only">
          {t("marketplace.filter.categoryLabel")}
        </Label>
        <Select
          id="mp-category"
          value={filters.category}
          onChange={(e) => set("category", e.target.value as ListingFilters["category"])}
        >
          <option value="all">{t("marketplace.filter.categoryAll")}</option>
          {CROP_CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {t(`marketplace.categories.${category}`)}
            </option>
          ))}
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="mp-listed" className="sr-only">
          {t("marketplace.filter.dateLabel")}
        </Label>
        <Select
          id="mp-listed"
          value={filters.listed}
          onChange={(e) => set("listed", e.target.value as ListingDateRange)}
        >
          <option value="all">{t("marketplace.filter.dateAll")}</option>
          <option value="today">{t("marketplace.filter.dateToday")}</option>
          <option value="week">{t("marketplace.filter.dateWeek")}</option>
          <option value="month">{t("marketplace.filter.dateMonth")}</option>
        </Select>
      </div>

      <div className="flex items-center gap-2 text-sm">
        <input
          id="mp-organic"
          type="checkbox"
          checked={filters.organic}
          onChange={(e) => set("organic", e.target.checked)}
          className="size-4 rounded border-input accent-brand-600"
        />
        <Label htmlFor="mp-organic" className="cursor-pointer">
          {t("marketplace.filter.organicOnly")}
        </Label>
      </div>
    </div>
  );
}
