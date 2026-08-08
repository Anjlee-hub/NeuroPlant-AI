/**
 * Marketplace messaging types (M4 Task 5) — mirrors the backend messaging
 * schemas (backend/app/schemas/messaging.py). The buyer↔seller inquiry system:
 * one conversation per buyer+seller(+listing/product) thread, messages carry a
 * NULL-until-read marker, and every payload is viewer-relative (unread_count
 * is how many *other-side* messages the caller hasn't read).
 *
 * Vocabularies are validated server-side; these unions keep the client honest
 * without duplicating any business rules (the backend stays the source of
 * truth, per the reuse mandate).
 */

/** Backend `MESSAGE_MAX_LENGTH` — the composer enforces it client-side too. */
export const MESSAGE_MAX_LENGTH = 2000;

/** Thread lifecycle — closed threads reject new messages. */
export type ConversationStatus = "active" | "closed";

/** One side of a thread — only marketplace-visible fields are exposed. */
export interface ConversationParticipant {
  id: number;
  name: string;
  role: string;
  shop_name: string | null;
  avatar_url: string | null;
}

/** The crop listing a conversation is about (when it has one). */
export interface ConversationListingRef {
  id: number;
  crop_name: string;
  image: string | null;
}

/** The product a conversation is about (when it has one). */
export interface ConversationProductRef {
  id: number;
  name: string;
  image: string | null;
}

/** One message in a thread. */
export interface Message {
  id: number;
  conversation_id: number;
  sender_id: number;
  sender_name: string;
  content: string;
  created_at: string;
  read_at: string | null;
}

/** One inbox row — viewer-relative unread count and last-message preview. */
export interface ConversationListItem {
  id: number;
  status: ConversationStatus;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
  last_message_preview: string | null;
  last_message_sender_id: number | null;
  unread_count: number;
  buyer: ConversationParticipant;
  seller: ConversationParticipant;
  listing: ConversationListingRef | null;
  product: ConversationProductRef | null;
}

/** The full thread: shared fields plus the message history. */
export interface ConversationDetail
  extends Omit<ConversationListItem, "last_message_preview" | "last_message_sender_id"> {
  messages: Message[];
}

/** POST /marketplace/conversations — exactly one context is required. */
export interface ConversationCreateInput {
  seller_id?: number | null;
  listing_id?: number | null;
  product_id?: number | null;
  message?: string | null;
}

/** POST /marketplace/conversations/{id}/messages — one turn. */
export interface SendMessageInput {
  content: string;
}

/** POST /marketplace/conversations/{id}/read — remaining unread for the caller. */
export interface ReadResult {
  conversation_id: number;
  unread_count: number;
}
