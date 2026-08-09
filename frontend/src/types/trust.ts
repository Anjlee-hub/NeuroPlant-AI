/**
 * Marketplace trust types (M4 Task 6) — mirrors the backend favourites +
 * reviews schemas (backend/app/schemas/favorites.py, reviews.py). The saved-items
 * and ratings layers sit on top of the marketplace, so a favourite targets a
 * crop listing *or* a product and a review's subject is the item's seller
 * (farmer / shop owner).
 *
 * Vocabularies and rules are validated server-side; these interfaces keep the
 * client honest without duplicating any business logic (the backend stays the
 * source of truth, per the reuse mandate).
 */

import type { CropListing, Product } from "@/types/marketplace";
import type { ConversationListingRef, ConversationProductRef } from "@/types/messages";

/** Rating scale + text bounds (mirrors backend RATING_MIN/MAX + limits). */
export const RATING_MIN = 1;
export const RATING_MAX = 5;
export const REVIEW_TITLE_MAX_LENGTH = 200;
export const REVIEW_CONTENT_MAX_LENGTH = 2000;

/** One saved item (a crop listing OR a product — never both). */
export interface Favourite {
  id: number;
  created_at: string;
  listing: CropListing | null;
  product: Product | null;
}

/** Button state for one item — `favorite_id` is the row DELETE needs. */
export interface FavouriteStatus {
  favorited: boolean;
  favorite_id: number | null;
  listing_id: number | null;
  product_id: number | null;
}

/**
 * Rating aggregate. `distribution` maps each star value to its count, present
 * for every scale value (zero-filled). JSON object keys always serialize as
 * strings, so the stars arrive as "1".."5" — consumers must read them with
 * `distribution[String(star)]`.
 */
export type RatingDistribution = Record<string, number>;

export interface RatingSummary {
  average: number;
  total: number;
  distribution: RatingDistribution;
}

/**
 * One review as returned by the API. The item a review is about is either a
 * crop listing (ConversationListingRef) or a product (ConversationProductRef)
 * — the backend types each field distinctly, and both are null once the item
 * has been deleted.
 */
export interface Review {
  id: number;
  reviewer_id: number;
  reviewer_name: string;
  seller_id: number;
  rating: number;
  title: string | null;
  content: string;
  created_at: string;
  updated_at: string;
  listing: ConversationListingRef | null;
  product: ConversationProductRef | null;
}

/**
 * Paginated reviews for one target (listing / product) or one seller.
 * `my_review` is the caller's own review of the item — only populated when a
 * single item is filtered — so the detail page knows whether to show "Write a
 * review" or "Edit your review" without a second request.
 */
export interface ReviewPage {
  items: Review[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  summary: RatingSummary;
  my_review: Review | null;
}

/** Payload for creating a review — exactly one target (server-enforced). */
export interface ReviewCreateInput {
  listing_id?: number;
  product_id?: number;
  rating: number;
  title?: string | null;
  content: string;
}

/** Partial payload for editing a review (only sent fields change). */
export interface ReviewUpdateInput {
  rating?: number;
  title?: string | null;
  content?: string;
}

/** Filters for `GET /marketplace/reviews` — exactly one scope, server-owned. */
export interface ReviewListParams {
  listing_id?: number;
  product_id?: number;
  seller_id?: number;
  page?: number;
  page_size?: number;
}
