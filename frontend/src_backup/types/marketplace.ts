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

/** Public farmer summary attached to a listing's detail view.
 *
 * `rating` / `review_count` are the review-driven reputation summary (M4 Task 6)
 * — 0 / 0 until the farmer has reviews across their listings.
 */
export interface FarmerSummary {
  id: number;
  name: string;
  verified: boolean;
  rating: number;
  review_count: number;
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

/**
 * ── Seller Portal (M4 Task 4) ─────────────────────────────────────────────
 * Mirrors `ProductOut` / `SellerOut` / `ProductPageOut` (backend
 * app/schemas/marketplace.py). The seller surface is the shop profile + the
 * product catalog (add/edit/delete/archive, stock toggle, stats, media); the
 * public product market is browse/detail for any authenticated user.
 */

/** Product category vocabulary — `organic` is the M4 Task 4 additive value. */
export type ProductCategory =
  | "fertilizer"
  | "pesticide"
  | "seed"
  | "tool"
  | "organic";

/** Products share the marketplace unit vocabulary (mirrors `UNITS`). */
export type ProductUnit = CropUnit;

/** Product availability — `archived` retires a product without deleting it. */
export type ProductAvailability = "in_stock" | "out_of_stock" | "archived";

/** One agricultural input as returned by the API (`ProductOut`). */
export interface Product {
  id: number;
  seller_id: number;
  name: string;
  category: ProductCategory;
  brand: string | null;
  description: string | null;
  price: number;
  unit: ProductUnit;
  stock_quantity: number | null;
  images: string[] | null;
  organic: boolean;
  manufacturer: string | null;
  usage_instructions: string | null;
  availability: ProductAvailability;
  created_at: string;
  updated_at: string;
}

/** Payload for creating a product (all fields). */
export interface ProductInput {
  name: string;
  category: ProductCategory;
  brand?: string | null;
  description?: string | null;
  price: number;
  unit: ProductUnit;
  stock_quantity?: number | null;
  images?: string[] | null;
  organic?: boolean;
  manufacturer?: string | null;
  usage_instructions?: string | null;
  availability?: ProductAvailability;
}

/** Partial payload for editing a product (PATCH — only sent fields change). */
export type ProductUpdate = Partial<ProductInput>;

/** Dashboard summary counts for the seller's own catalog. */
export interface ProductStats {
  total: number;
  active: number;
  out_of_stock: number;
  archived: number;
}

/** The agricultural shop profile (`SellerOut`). */
export interface SellerProfile {
  user_id: number;
  owner_name: string;
  shop_name: string | null;
  address: string | null;
  phone: string | null;
  delivery_available: boolean;
  rating: number;
  verified: boolean;
  created_at: string;
  description: string | null;
  opening_hours: string | null;
  logo_url: string | null;
  banner_url: string | null;
  products: Product[];
}

/** Payload for registering / filling in the shop profile. */
export interface SellerRegisterInput {
  shop_name: string;
  address?: string | null;
  phone?: string | null;
  delivery_available?: boolean;
  description?: string | null;
  opening_hours?: string | null;
  logo_url?: string | null;
  banner_url?: string | null;
}

/** Partial payload for editing the shop profile (PATCH /shop/me). */
export type SellerUpdate = Partial<SellerRegisterInput>;

/** Compact shop identity attached to a product's public detail view. */
export interface ShopSummary {
  user_id: number;
  shop_name: string | null;
  verified: boolean;
  rating: number;
  delivery_available: boolean;
}

/** One product with its shop attached (the detail endpoint's payload). */
export interface ProductDetail extends Product {
  shop: ShopSummary;
}

/** Paginated public product-market response — mirrors `ProductPageOut`. */
export interface ProductPage {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** Products sort by the same keys as crop listings. */
export type ProductSort = CropListingSort;

/** Query parameters for the public product market (all optional). */
export interface ProductQuery {
  q?: string;
  category?: ProductCategory;
  organic?: boolean;
  availability?: ProductAvailability;
  min_price?: number;
  max_price?: number;
  brand?: string;
  sort?: ProductSort;
  page?: number;
  page_size?: number;
}

/** The seller-facing product category options for the add/edit form. */
export const PRODUCT_CATEGORY_OPTIONS: ProductCategory[] = [
  "fertilizer",
  "pesticide",
  "seed",
  "tool",
  "organic",
];

/** The seller-facing availability options for the stock toggle. */
export const PRODUCT_AVAILABILITY_OPTIONS: ProductAvailability[] = [
  "in_stock",
  "out_of_stock",
  "archived",
];
