import type {
  MfaChallengeResponse,
  MfaCodesResponse,
  MfaSetupResponse,
  OtpSendResponse,
  RegisterInput,
  TokenResponse,
  User,
} from "@/types/auth";
import type {
  CalendarCrop,
  CalendarTask,
  CalendarTaskUpdate,
  CustomTaskInput,
  CropCalendar,
  FarmerCalendar,
  ScheduleInput,
} from "@/types/calendar";
import type {
  AssistantReply,
  AssistantRequest,
  ConversationHistory,
} from "@/types/assistant";
import type { DiseaseRecommendation } from "@/types/recommendation";
import type { RecoveryLog, RecoveryLogInput, RecoveryTracker } from "@/types/recovery";
import type { SoilRecommendation } from "@/types/soil";
import type {
  CropOption,
  Scan,
  ScanExplain,
  ScanList,
  ScanListParams,
  ScanPartType,
  ScanSyncItem,
  ScanSyncOut,
} from "@/types/scan";
import type {
  CropListing,
  CropListingDetail,
  CropListingInput,
  CropListingPage,
  CropListingQuery,
  CropListingStats,
  CropListingUpdate,
  ListingImagesResult,
} from "@/types/marketplace";

/** Editable profile fields (mirrors `UserUpdate` — name is the main one). */
export interface ProfileUpdateInput {
  name?: string;
  lang?: string;
  address?: string;
  lat?: number;
  lng?: number;
}

/** Payload for the multipart `POST /scans` upload. */
export interface ScanUploadInput {
  files: File[];
  clientScanId: string;
  cropId?: number | null;
  partType?: ScanPartType | null;
  deviceId?: string;
}

/**
 * Thin typed client for the FastAPI backend. Responses are the domain
 * models directly (no envelope); errors arrive as
 * `{ "error": { "message" } }` (mapped domain exceptions) or FastAPI
 * `{ "detail" }` (validation). Dev-only: vite proxies `/api` to :8000.
 */

const API_BASE = "/api/v1";

const ACCESS_KEY = "neuroplant.access";
const REFRESH_KEY = "neuroplant.refresh";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Extract a human-readable message from any thrown value. */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError || err instanceof Error) return err.message;
  return "Request failed";
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: TokenResponse | null): void {
  if (tokens) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  } else {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean;
}

/**
 * Single-flight access-token refresh. One 401 triggers one refresh; concurrent
 * callers share the same in-flight promise so the refresh endpoint is never
 * hammered. On failure the stored tokens are dropped (the next auth check
 * shows the user logged out) and null is returned.
 */
let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        const text = await res.text();
        const body = text ? (JSON.parse(text) as Record<string, unknown>) : null;
        if (!res.ok) {
          const detail = typeof body?.detail === "string" ? body.detail : undefined;
          throw new ApiError(res.status, detail ?? `Refresh failed (${res.status})`);
        }
        setTokens(body as unknown as TokenResponse);
        return getAccessToken();
      } catch {
        // Refresh token expired/revoked — local cleanup still proceeds.
        setTokens(null);
        return null;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
  retried = false,
): Promise<T> {
  const headers: Record<string, string> = {};
  // FormData gets a browser-set multipart boundary — never set Content-Type.
  if (options.body !== undefined && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const token = options.auth ? getAccessToken() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body:
      options.body instanceof FormData
        ? options.body
        : options.body !== undefined
          ? JSON.stringify(options.body)
          : undefined,
  });

  const text = await res.text();
  const body = text ? (JSON.parse(text) as Record<string, unknown>) : null;

  if (!res.ok) {
    // Expired access token → refresh once, then retry the original request.
    if (res.status === 401 && options.auth && !retried) {
      const newToken = await refreshAccessToken();
      if (newToken) return request<T>(path, options, true);
    }
    const error = body?.error as { message?: string } | undefined;
    const detail = typeof body?.detail === "string" ? body.detail : undefined;
    throw new ApiError(
      res.status,
      error?.message ?? detail ?? `Request failed (${res.status})`,
    );
  }

  return body as T;
}

export const api = {
  // ── Auth ──────────────────────────────────────────────────────────────
  register: (payload: RegisterInput) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: payload }),
  login: (identifier: string, password: string) =>
    request<TokenResponse | MfaChallengeResponse>("/auth/login", {
      method: "POST",
      body: { identifier, password },
    }),
  sendOtp: (phone: string, purpose: "login" | "register") =>
    request<OtpSendResponse>("/auth/otp/send", {
      method: "POST",
      body: { phone, purpose },
    }),
  verifyOtp: (phone: string, purpose: "login" | "register", code: string) =>
    request<TokenResponse>("/auth/otp/verify", {
      method: "POST",
      body: { phone, purpose, code },
    }),
  verifyMfa: (challenge: string, code: string) =>
    request<TokenResponse>("/auth/mfa/verify", {
      method: "POST",
      body: { challenge, code },
    }),
  logout: (refreshToken: string) =>
    request<void>("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),
  me: () => request<User>("/auth/me", { auth: true }),
  mfaSetup: () =>
    request<MfaSetupResponse>("/auth/mfa/setup", { method: "POST", auth: true }),
  mfaConfirm: (code: string) =>
    request<MfaCodesResponse>("/auth/mfa/confirm", {
      method: "POST",
      body: { code },
      auth: true,
    }),

  // ── Scans (M2 Task 7) ────────────────────────────────────────────────
  listScans: (params: ScanListParams = {}) => {
    const qs = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        qs.set(key, String(value));
      }
    }
    const query = qs.toString();
    return request<ScanList>(`/scans${query ? `?${query}` : ""}`, { auth: true });
  },
  getScan: (scanId: number) => request<Scan>(`/scans/${scanId}`, { auth: true }),
  getScanExplain: (scanId: number) =>
    request<ScanExplain>(`/scans/${scanId}/explain`, { auth: true }),
  /** Treatment care plan for a scan's predicted disease (M3 T2). */
  getScanRecommendations: (scanId: number) =>
    request<DiseaseRecommendation>(`/scans/${scanId}/recommendations`, { auth: true }),
  /** Disease-aware soil plan for a scan's predicted disease (M3 T3). */
  getScanSoilRecommendations: (scanId: number) =>
    request<SoilRecommendation>(`/scans/${scanId}/soil-recommendations`, { auth: true }),
  /** Full crop recovery tracker for a scan (M3 T4): percentage/status/risk + timeline. */
  getScanRecoveryTracker: (scanId: number) =>
    request<RecoveryTracker>(`/scans/${scanId}/recovery`, { auth: true }),
  /** Record one treatment action against the scan. */
  addRecoveryLog: (scanId: number, payload: RecoveryLogInput) =>
    request<RecoveryLog>(`/scans/${scanId}/recovery/logs`, {
      method: "POST",
      body: payload,
      auth: true,
    }),
  /** Edit one of the scan's treatment logs (partial — only sent fields change). */
  updateRecoveryLog: (scanId: number, logId: number, payload: Partial<RecoveryLogInput>) =>
    request<RecoveryLog>(`/scans/${scanId}/recovery/logs/${logId}`, {
      method: "PATCH",
      body: payload,
      auth: true,
    }),
  /** Remove one of the scan's treatment logs. */
  deleteRecoveryLog: (scanId: number, logId: number) =>
    request<void>(`/scans/${scanId}/recovery/logs/${logId}`, {
      method: "DELETE",
      auth: true,
    }),
  listCrops: () => request<CropOption[]>("/catalog/crops", { auth: true }),
  // ── Farmer Calendar (M3 T5) ──────────────────────────────────────────
  /** Catalog crops with growth-stage templates (crop picker). */
  listCalendarCrops: () => request<CalendarCrop[]>("/calendar/crops", { auth: true }),
  /** Start (or refresh) a schedule for one crop. */
  scheduleCrop: (cropId: number, payload: ScheduleInput = {}) =>
    request<CropCalendar>(`/calendar/crops/${cropId}/schedule`, {
      method: "POST",
      body: payload,
      auth: true,
    }),
  /** The Farmer Calendar dashboard: schedules + bucket counts. */
  getFarmerCalendar: () => request<FarmerCalendar>("/calendar", { auth: true }),
  /** Add a farmer-typed note / to-do to a schedule. */
  addCalendarTask: (payload: CustomTaskInput) =>
    request<CalendarTask>("/calendar/tasks", {
      method: "POST",
      body: payload,
      auth: true,
    }),
  /** Complete / snooze / re-title / re-date / note one task (partial). */
  updateCalendarTask: (taskId: number, payload: CalendarTaskUpdate) =>
    request<CalendarTask>(`/calendar/tasks/${taskId}`, {
      method: "PATCH",
      body: payload,
      auth: true,
    }),
  /** Remove a task from the schedule. */
  deleteCalendarTask: (taskId: number) =>
    request<void>(`/calendar/tasks/${taskId}`, {
      method: "DELETE",
      auth: true,
    }),
  // ── Voice AI Assistant (M3 T6 → M3.1 conversational) ──────────────────
  /** Route a free-text question (English/Hindi) to the conversational assistant. */
  askAssistant: (payload: AssistantRequest) =>
    request<AssistantReply>("/assistant", { method: "POST", body: payload, auth: true }),
  /** Restore the user's chat transcript, oldest first (page-load restore). */
  getAssistantConversation: () =>
    request<ConversationHistory>("/assistant/conversation", { auth: true }),
  /** Clear the user's entire chat transcript (clear-chat). */
  clearAssistantConversation: () =>
    request<void>("/assistant/conversation", { method: "DELETE", auth: true }),
  // Offline reconciliation: upload the queued scans in one JSON batch. The
  // server owns idempotency (created/replayed per client_scan_id) — this
  // just transports the queue.
  syncScans: (items: ScanSyncItem[]) =>
    request<ScanSyncOut>("/scans/sync", { method: "POST", body: items, auth: true }),

  // ── Buyer Marketplace (M4 Task 3) ─────────────────────────────────────
  /** Browse/search/filter the live storefront — server-side pagination. */
  browseCrops: (params: CropListingQuery = {}) => {
    const qs = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        qs.set(key, String(value));
      }
    }
    const query = qs.toString();
    return request<CropListingPage>(`/marketplace/crops${query ? `?${query}` : ""}`, {
      auth: true,
    });
  },

  // ── Farmer Marketplace (M4 Task 2) ────────────────────────────────────
  /** The farmer's own listings (newest first) — dashboard table/cards. */
  myCropListings: () => request<CropListing[]>("/marketplace/crops/mine", { auth: true }),
  /** Dashboard counts over the farmer's own listings. */
  getCropListingStats: () =>
    request<CropListingStats>("/marketplace/crops/stats", { auth: true }),
  /** One listing with its farmer attached (detail view). */
  getCropListing: (listingId: number) =>
    request<CropListingDetail>(`/marketplace/crops/${listingId}`, { auth: true }),
  /** Offer produce for sale. */
  createCropListing: (payload: CropListingInput) =>
    request<CropListing>("/marketplace/crops", {
      method: "POST",
      body: payload,
      auth: true,
    }),
  /** Partial edit of one of the farmer's own listings. */
  updateCropListing: (listingId: number, payload: CropListingUpdate) =>
    request<CropListing>(`/marketplace/crops/${listingId}`, {
      method: "PATCH",
      body: payload,
      auth: true,
    }),
  /** Remove one of the farmer's own listings. */
  deleteCropListing: (listingId: number) =>
    request<void>(`/marketplace/crops/${listingId}`, { method: "DELETE", auth: true }),
  /** Upload listing photos (multipart) → storage URLs for the images field. */
  uploadListingImages: (files: File[]) => {
    const fd = new FormData();
    for (const file of files) fd.append("files", file);
    return request<ListingImagesResult>("/marketplace/crops/images", {
      method: "POST",
      body: fd,
      auth: true,
    });
  },

  // ── M2.1 — live scan upload + profile ────────────────────────────────
  /** Multipart upload → runs the same pipeline as the offline sync path. */
  uploadScan: (input: ScanUploadInput) => {
    const fd = new FormData();
    for (const file of input.files) fd.append("files", file);
    fd.append("client_scan_id", input.clientScanId);
    if (input.cropId != null) fd.append("crop_id", String(input.cropId));
    if (input.partType) fd.append("part_type", input.partType);
    if (input.deviceId) fd.append("device_id", input.deviceId);
    return request<Scan>("/scans", { method: "POST", body: fd, auth: true });
  },
  updateProfile: (payload: ProfileUpdateInput) =>
    request<User>("/users/me", { method: "PATCH", body: payload, auth: true }),
};
