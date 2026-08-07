/**
 * Farmer marketplace types — mirrors the backend `CropListingOut` /
 * `CropListingStatsOut` / payloads (see backend/app/schemas/marketplace.py).
 * The farmer-facing surface (M4 Task 2) is the crop-listing dashboard:
 * create / edit / delete / mark-sold / mark-available / archive own listings,
 * upload photos, and read dashboard counts. Browse/search belong to customers
 * and are read-only here.
 *
 * Vocabularies are validated server-side; these unions keep the client honest
 * without duplicating any business rules (the backend stays the source of
 * truth, per the reuse mandate).
 */

/** Crop category vocabulary (mirrors `CROP_CATEGORIES`). */
export type CropCategory = "vegetable" | "fruit" | "grain" | "pulses" | "spice" | "other";

/** Quantity/price unit vocabulary (mirrors `UNITS`). */
export type CropUnit = "kg" | "g" | "qtl" | "bag" | "dozen" | "piece" | "l" | "box" | "bundle";

/** Listing availability — `archived` is the M4 Task 2 additive extension. */
export type CropAvailability = "available" | "limited" | "sold_out" | "archived";

/** One crop listing as returned by the API. */
export interface CropListing {
  id: number;
  farmer_id: number;
  crop_name: string;
  category: CropCategory;
  variety: string | null;
  quantity: number;
  unit: CropUnit;
  price: number;
  description: string | null;
  images: string[] | null;
  harvest_date: string | null;
  organic: boolean;
  location: string | null;
  availability: CropAvailability;
  created_at: string;
  updated_at: string;
}

/** Payload for creating a listing (all fields). */
export interface CropListingInput {
  crop_name: string;
  category: CropCategory;
  variety?: string | null;
  quantity: number;
  unit: CropUnit;
  price: number;
  description?: string | null;
  images?: string[] | null;
  harvest_date?: string | null;
  organic?: boolean;
  location?: string | null;
  availability?: CropAvailability;
}

/** Partial payload for editing a listing (PATCH — only sent fields change). */
export type CropListingUpdate = Partial<CropListingInput>;

/** Dashboard summary counts for the farmer's own listings (M4 Task 2). */
export interface CropListingStats {
  total: number;
  active: number;
  sold: number;
  archived: number;
}

/** Response of the multi-image upload endpoint — storage-relative media URLs. */
export interface ListingImagesResult {
  urls: string[];
}

/** Public farmer summary attached to a listing's detail view. */
export interface FarmerSummary {
  id: number;
  name: string;
  verified: boolean;
}

/** One listing with its farmer attached (the detail endpoint's payload). */
export interface CropListingDetail extends CropListing {
  farmer: FarmerSummary;
}

/** Paginated browse response — mirrors `CropListingPageOut`. */
export interface CropListingPage {
  items: CropListing[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** Sort keys the browse/search endpoints accept (Task 3 adds `oldest`). */
export type CropListingSort = "newest" | "oldest" | "price_asc" | "price_desc";

/** Query parameters for browse/search (all optional; server-owned rules). */
export interface CropListingQuery {
  q?: string;
  category?: CropCategory;
  organic?: boolean;
  availability?: CropAvailability;
  min_price?: number;
  max_price?: number;
  location?: string;
  /** Inclusive lower bound on harvest date (YYYY-MM-DD). */
  harvest_from?: string;
  /** Inclusive upper bound on harvest date (YYYY-MM-DD). */
  harvest_to?: string;
  sort?: CropListingSort;
  page?: number;
  page_size?: number;
}

/** The farmer-facing availability label set for the dashboard status bucket. */
export const CROP_AVAILABILITY_OPTIONS: CropAvailability[] = [
  "available",
  "limited",
  "sold_out",
  "archived",
];
