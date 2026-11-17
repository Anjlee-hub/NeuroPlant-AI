/**
 * Mirrors the backend auth/user schemas (app/schemas/auth.py, user.py).
 */

export type UserRole = "farmer" | "customer" | "expert" | "seller";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

/** Returned by /auth/login when the user has MFA enabled. */
export interface MfaChallengeResponse {
  requires_mfa: true;
  mfa_challenge: string;
}

export interface OtpSendResponse {
  message: string;
  /** Plain code surfaced only in development (DEBUG=true). */
  debug_code: string | null;
}

export interface MfaSetupResponse {
  secret: string;
  otpauth_uri: string;
  qr_url: string;
}

export interface MfaCodesResponse {
  backup_codes: string[];
}

export interface User {
  id: number;
  role: UserRole;
  phone: string;
  email: string | null;
  name: string;
  avatar_url: string | null;
  lang: string;
  verified: boolean;
  created_at: string;
}

export interface RegisterInput {
  phone: string;
  name: string;
  role: UserRole;
  password?: string;
  email?: string;
}
