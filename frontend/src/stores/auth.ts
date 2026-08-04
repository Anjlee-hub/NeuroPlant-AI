import { create } from "zustand";

import { api, getAccessToken, getRefreshToken, setTokens } from "@/lib/api";
import type { RegisterInput, User } from "@/types/auth";

interface AuthState {
  /** Authenticated user; null when logged out or session not yet hydrated. */
  user: User | null;
  /** True during any in-flight auth call (form buttons show spinners). */
  loading: boolean;
  /** Pending MFA challenge handed back by /auth/login. */
  challenge: string | null;

  register: (input: RegisterInput) => Promise<void>;
  login: (identifier: string, password: string) => Promise<"mfa" | "ok">;
  sendOtp: (phone: string) => Promise<string | null>;
  verifyOtp: (phone: string, code: string) => Promise<void>;
  verifyMfa: (code: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Restore a stored session on app boot. */
  hydrate: () => Promise<void>;
}

async function loadUser(): Promise<User> {
  return api.me();
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  loading: false,
  challenge: null,

  register: async (input) => {
    set({ loading: true });
    try {
      const tokens = await api.register(input);
      setTokens(tokens);
      set({ user: await loadUser() });
    } finally {
      set({ loading: false });
    }
  },

  login: async (identifier, password) => {
    set({ loading: true });
    try {
      const res = await api.login(identifier, password);
      if ("requires_mfa" in res) {
        set({ challenge: res.mfa_challenge });
        return "mfa";
      }
      setTokens(res);
      set({ user: await loadUser(), challenge: null });
      return "ok";
    } finally {
      set({ loading: false });
    }
  },

  sendOtp: async (phone) => {
    const res = await api.sendOtp(phone, "login");
    return res.debug_code;
  },

  verifyOtp: async (phone, code) => {
    set({ loading: true });
    try {
      const tokens = await api.verifyOtp(phone, "login", code);
      setTokens(tokens);
      set({ user: await loadUser() });
    } finally {
      set({ loading: false });
    }
  },

  verifyMfa: async (code) => {
    set({ loading: true });
    try {
      const challenge = get().challenge;
      if (!challenge) throw new Error("No pending MFA challenge");
      const tokens = await api.verifyMfa(challenge, code);
      setTokens(tokens);
      set({ user: await loadUser(), challenge: null });
    } finally {
      set({ loading: false });
    }
  },

  logout: async () => {
    const refresh = getRefreshToken();
    if (refresh) {
      try {
        await api.logout(refresh);
      } catch {
        // Token may already be rotated/expired — local cleanup still proceeds.
      }
    }
    setTokens(null);
    set({ user: null, challenge: null });
  },

  hydrate: async () => {
    if (!getAccessToken()) return;
    set({ loading: true });
    try {
      set({ user: await loadUser() });
    } catch {
      // Expired/revoked token — drop the stored session.
      setTokens(null);
      set({ user: null });
    } finally {
      set({ loading: false });
    }
  },
}));
