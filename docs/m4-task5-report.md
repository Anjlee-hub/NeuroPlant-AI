# M4 Task 5 Report — Buyer–Seller Communication

**Milestone:** M4 (Marketplace & Farmer Community) · **Task:** 5 of ? · **Date:** 2026-08-08
**Branch:** `main` · **Status:** ✅ Complete · **Commit:** `feat(m4): buyer seller communication`

---

## 1. Summary

M4 Task 5 delivers the **buyer↔seller inquiry system**: a real "Contact Seller"
flow on both the farmer crop-listing detail and the agricultural-product detail,
backed by a dedicated conversation + message store, an inbox at
`/marketplace/messages`, a full thread UI at `/marketplace/messages/:conversationId`,
and an **inquiries section inside the seller portal** (`/marketplace/shop`).

The feature replaces the two M4 Task 3/4 "coming soon" placeholders with real
messaging while honouring the reuse mandate:

- **The backend is additive** — new `marketplace_conversations` and
  `marketplace_messages` tables, a new messaging service + endpoint module, with
  ownership, RBAC and validation all enforced server-side. No existing
  marketplace route was modified.
- **The frontend is a pure client** over the messaging APIs. Create-or-reuse,
  unread counting, mark-read, close, and thread lifecycle live in the backend;
  the UI only transports intents and renders responses.
- **No WebSockets / polling** — the API is request/response by design, and the
  architecture is future-ready for WS / push / email notifications (see §12).

---

## 2. Features Implemented

### Conversation + message model
- **Conversation** — buyer (user), seller (user), optional related `listing_id`
  or `product_id`, `status` (`active` / `closed`), `last_message_at`,
  `created_at` / `updated_at`. Threads are keyed by **buyer + seller + context**
  so a second "Contact Seller" click on the same item never stacks a duplicate.
- **Message** — sender, content (≤ 2000 chars), `created_at`, and a nullable
  `read_at` stamp (NULL until the *other side* reads it). No unnecessary
  sensitive data is stored or exposed.
- Table names are deliberately prefixed `marketplace_*` to stay distinct from
  the M3.1 assistant's `conversation_messages`.

### Contact Seller (marketplace integration)
- **Crop listing detail** (`/marketplace/listings/:id`) — "Contact farmer"
  starts a conversation against `listing_id` (seller = the listing's farmer).
- **Product detail** (`/marketplace/products/:id`) — "Contact seller" starts a
  conversation against `product_id` (seller = the shop owner).
- **Create-or-reuse** — the backend dedupes: a second contact on the same
  context returns the same thread with history intact, and a fresh contact on a
  *closed* thread reopens it (same id, history preserved). The button shows a
  loading label while the thread is created and navigates straight into it.

### Inbox + thread UI
- **`/marketplace/messages`** — every thread the caller participates in, newest
  activity first. Each row shows the other party (name + shop), the related
  crop/product, the last-message preview, the relative time, an **accessible
  unread badge**, and a "Closed" label on finished threads.
- **`/marketplace/messages/:conversationId`** — full history (own messages
  right / filled, other side left / outlined), Enter-to-send composer with a
  live 2000-char counter, **auto mark-read on open**, read receipts on sent
  messages, and a close control (with confirmation). Closed threads show an
  explanation and a locked composer.
- **Honest states everywhere** — loading skeletons, empty states, inline errors
  with retry, and a 404 card for unknown / non-participant threads (the
  enumeration guard).

### Seller portal integration
- **`/marketplace/shop`** gained an **Inquiries** section that lists only
  threads where the current user is the seller side, with a total unread pill
  and one row per inquiry linking into the full thread (reply, mark-read and
  close all live there). Isolation is server-side: a seller can only ever see
  conversations where they are the seller participant.

---

## 3. Backend APIs

New endpoint module `app/api/v1/endpoints/messaging.py` (all under
`/api/v1/marketplace/conversations`):

| Method | Path | Purpose |
|---|---|---|
| POST | `/marketplace/conversations` | Start (or reuse / reopen) a conversation; optional opening `message` (201) |
| GET | `/marketplace/conversations` | The caller's inbox (participant-scoped, newest first) |
| GET | `/marketplace/conversations/{id}` | One thread with full message history (participants only) |
| POST | `/marketplace/conversations/{id}/messages` | Append a message (201); 409 on a closed thread |
| POST | `/marketplace/conversations/{id}/read` | Stamp `read_at` on the other side's messages |
| POST | `/marketplace/conversations/{id}/close` | Close the thread (idempotent, 200); history stays visible |

Exactly one context is required per creation — `listing_id`, `product_id` or
`seller_id` (400 otherwise). Unknown references return 400 (never a leak);
self-contact (buyer messaging their own shop) is rejected with 400.

---

## 4. Security / Ownership Model

- **Authentication** — every endpoint requires `get_current_user`; any
  authenticated role (farmer / customer / seller / admin) may participate.
- **Ownership / IDOR guard** — a conversation is reachable *only* by its two
  participants. A non-participant gets **404** on detail / send / read / close —
  the platform's enumeration guard (same pattern as scans, recovery, calendar).
- **RBAC** — no role gates beyond authentication; sellers and buyers are both
  participants by design. The seller-scoped inbox filters on `seller_id` so a
  seller never sees conversations they don't own.
- **Input validation** — message `content` and the opening `message` are
  length-limited (1–2000) and whitespace-only content is rejected (422).
- **Rate limiting** — the existing token-bucket `RateLimiter` is applied to
  conversation create + message send via a `message_rate_limit` dependency
  (429 when over the configured per-minute budget). Reuses the scan limiter
  infrastructure — no new mechanism.
- **Privacy** — participant payloads expose only marketplace-visible fields
  (name, role, shop name, avatar); no phone / email is ever returned.

---

## 5. Database Changes

One additive Alembic migration, single head **`c2e4f6a8b0d2`**
(`revises b7d3f5a9c1e4`), `alembic upgrade head` verified against a fresh DB:

**`marketplace_conversations`**
- `id`, `buyer_id` (FK users, indexed), `seller_id` (FK users, indexed)
- `listing_id` (FK `crop_listings`, `SET NULL`, nullable) —
  `product_id` (FK `products`, `SET NULL`, nullable)
- `status` — varchar(20), default `active`, indexed
- `last_message_at` (nullable), `created_at` / `updated_at` (TimestampMixin)
- Index on `(conversation_id)` for the buyer-side lookup pattern

**`marketplace_messages`**
- `id`, `conversation_id` (FK, indexed), `sender_id` (FK users, indexed)
- `content` (Text), `read_at` (nullable), `created_at`
- Composite index `(conversation_id, created_at)` for ordered history reads

Deleting a listing or product nulls the conversation's reference (history keeps
the cached name/image refs from the payload).

---

## 6. Architecture

- **Service layer** — `MessagingService` owns every business rule: exactly-one
  context resolution (listing → its farmer, product → its shop), self-contact
  rejection, create-or-reuse via a null-safe dedup query, closed-thread reopen,
  viewer-relative unread counts, batch `last_message` + unread aggregation for
  the inbox (no per-thread round-trips), and preview truncation.
- **Read-model payloads** are viewer-relative: `unread_count` counts only
  messages from the *other* participant with `read_at IS NULL`; the caller's own
  messages never count as unread.
- **Frontend data flow** uses React Query with dedicated keys
  (`CONVERSATIONS_KEY` for the inbox, `CONVERSATION_KEY` for a thread). The
  Contact button invalidates the inbox and navigates to the thread; sends and
  closes invalidate / set the thread cache so the UI stays in sync with the
  server without polling.
- **Future-ready** — conversation/message rows carry everything a push or
  email gateway needs (participants, status, unread), so adding WebSocket /
  SSE / email later is a transport change, not a model change (see §12).

---

## 7. Frontend Pages / Components

| Route | Page | Components |
|---|---|---|
| `/marketplace/messages` | `messages-list.tsx` | `ConversationList`, `ConversationListItemCard` |
| `/marketplace/messages/:conversationId` | `messages-detail.tsx` | `MessageBubble`, `MessageComposer`, `ui/badge` |
| — (embedded in listing / product detail) | — | `ContactSellerButton` |
| `/marketplace/shop` (section) | `seller-dashboard.tsx` | `SellerInquiriesSection`, `ConversationList` |

- **API client** — `src/lib/api.ts` gained `createConversation`,
  `listConversations`, `getConversation`, `sendMessage`, `markConversationRead`,
  `closeConversation`.
- **Types** — `src/types/messages.ts` mirrors the backend schemas:
  `ConversationStatus`, `ConversationParticipant`, `ConversationListingRef`,
  `ConversationProductRef`, `Message`, `ConversationListItem`,
  `ConversationDetail`, `ConversationCreateInput`, `SendMessageInput`,
  `ReadResult`, and the shared `MESSAGE_MAX_LENGTH = 2000` constant.
- **Router + nav** — two new routes (`/marketplace/messages` and
  `/marketplace/messages/:conversationId`) wired in `router.tsx`; `header.tsx`
  gained a **Messages** nav entry (`Inbox` icon).
- **Accessibility** — unread counts are `role="status"` with `aria-label`s,
  message history is a `role="log"` with `aria-live="polite"`, the composer is
  labelled and Enter-to-send / Shift+Enter-newline, closed threads announce
  their state, and the lightbox-style close uses a plain confirm. All controls
  are keyboard- and screen-reader-accessible.
- **Responsive** — inbox rows and the thread stack on small screens; the
  composer row wraps so the counter stays visible.

---

## 8. i18n

English + Hindi, full parity. New `messages` namespace covers the inbox, thread,
composer, read/close actions, empty/error/closed states, the seller inquiries
section, and the `opening` loading label. `nav.messages` was added to both
locales. The now-dead `marketplaceBuy.actions.contactSoon` placeholder keys were
removed; existing `contactFarmer` / `contactSeller` labels are reused as the
button labels. Verified by the existing static `t()` key cross-check (en/hi
identical key structures).

---

## 9. Tests

**Backend** (`tests/test_messaging.py`, 15 tests): unauthenticated 401s across
all six endpoints; buyer-creates-product-conversation (refs, seller shop,
opening message, viewer-relative unread); duplicate-reuse with preserved
history; listing → listing-farmer; explicit `seller_id`; self-contact 400;
context-selection enforcement (both / none / unknown → 400); buyer-vs-buyer
IDOR 404; seller-vs-seller IDOR 404; missing conversation 404; participant-
scoped inbox; send/reply/mark-read flow (unread counts, `read_at` stamping,
own messages never stamped); message validation (empty / 2001 chars /
whitespace-only / over-length opening message → 422); closed-thread lifecycle
(409 on both sides, idempotent close, reopen reuses thread with history); newest-
activity-first inbox sort.

**Frontend** (`src/pages/__tests__/messages.test.tsx`, 13 tests): inbox auth
gate, other-party + product + preview + unread rendering, row links, closed
threads without unread, empty state, error + retry; detail auth gate, history
rendering, auto mark-read on open, send-from-composer, closed-thread locked
composer, close-after-confirm, not-found card. `marketplace-listing-detail.test.tsx`
was updated to assert the real Contact-farmer flow (create + navigate, inline
error) instead of the removed "coming soon" note, and `seller-portal.test.tsx`
gained the `listConversations` mock for the new inquiries section.

**Smoke journey** (`backend/scripts/m4_task5_smoke.py`, 30 checks, all passing
against a clean migrated DB): register seller → shop → product → register buyer →
create conversation (product context + opening message) → duplicate reuses the
same thread → seller inbox (unread + preview) → seller detail → seller reply →
buyer mark-read → close → messaging blocked (409) → reopen → message again →
RBAC/isolation guards (outsider buyer 404). Self-cleaning.

---

## 10. Quality-Gate Results

### Backend
| Gate | Result |
|---|---|
| `pytest` | **378 passed, 1 skipped** — 379 collected, 0 failures (15 new messaging tests) |
| `ruff check` | ✅ All checks passed |
| `ruff format --check` | ✅ Task-5 files formatted; pre-existing alembic/M3 files left untouched (ruff version drift, scoped out per prior task precedent) |
| `mypy app` | ✅ Success: no issues in source files |
| `pip check` | ✅ No broken requirements |

### Frontend
| Gate | Result |
|---|---|
| `vitest run` | ✅ **35 files / 229 tests passed** (13 new messaging tests + 2 new contact-flow tests) |
| `tsc -b --noEmit` | ✅ Clean |
| `eslint . --max-warnings=0` | ✅ 0 warnings |
| `vite build` (production) | ✅ Built — 2403 modules, PWA `sw.js` + `manifest.webmanifest`, 11 precache entries |

---

## 11. Known Limitations

- **No push / real-time delivery** — the inbox and thread refresh on mount and
  after mutations, not on a timer or socket. Two browsers open on the same
  thread will not see each other's messages until a reload (see §12).
- **No message editing / deletion** — history is append-only, by design.
- **Unread is coarse** — the backend counts per conversation, not per message,
  so a long thread always shows "N unread" until the reader opens it.
- **No media in messages** — text only (per spec).
- **Dev DB had smoke-test rows cleaned up** after verification; a fresh
  `alembic upgrade head` DB is the supported baseline.

---

## 12. Future Real-Time / Notification Architecture

Messaging was built so a real-time layer can be added **as a transport change,
not a model change**:

- **WebSockets / SSE** — a `GET /marketplace/conversations/events` (SSE) or
  `/ws/marketplace/conversations` stream could push `last_message_at` bumps and
  new-message rows to the two participants. The reader-relative unread logic
  already lives server-side, so a "refresh on event" is all the client needs.
- **Email / push notifications** — the conversation rows carry both participant
  ids and a `status`; a background worker can email the seller on a new inquiry
  (`unread_count` for that seller is already computed by the same query). `read_at`
  gives the "left on read" signal for a later reminder.
- **Ordered history index** — the `(conversation_id, created_at)` composite
  index makes both REST history reads and any streaming replay cheap.
- **Rate limiting** — the existing `message_rate_limit` dependency can be
  reused verbatim by any future push endpoint.
