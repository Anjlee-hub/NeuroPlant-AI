import type {
  MfaChallengeResponse,
  MfaCodesResponse,
  MfaSetupResponse,
  OtpSendResponse,
  RegisterInput,
  TokenResponse,
  User,
} from "@/types/auth";

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

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const token = options.auth ? getAccessToken() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  const text = await res.text();
  const body = text ? (JSON.parse(text) as Record<string, unknown>) : null;

  if (!res.ok) {
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
};
