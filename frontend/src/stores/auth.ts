
import { create } from "zustand";

import {
  api,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "@/lib/api";
import type { RegisterInput, User } from "@/types/auth";

interface AuthState {
  user: User | null;
  loading: boolean;
  challenge: string | null;
  hydrated: boolean;

  register: (input: RegisterInput) => Promise<void>;
  login: (identifier: string, password: string) => Promise<"mfa" | "ok">;
  sendOtp: (phone: string) => Promise<string | null>;
  verifyOtp: (phone: string, code: string) => Promise<void>;
  verifyMfa: (code: string) => Promise<void>;
  logout: () => Promise<void>;
  hydrate: () => Promise<void>;
  updateUser: (patch: Partial<User>) => void;
}

async function loadUser(): Promise<User> {
  return api.me();
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  loading: false,
  challenge: null,
  hydrated: false,

  register: async (input) => {
    set({ loading: true });

    try {
      const tokens = await api.register(input);
      setTokens(tokens);

      const user = await loadUser();
      set({ user, challenge: null });
    } finally {
      set({ loading: false });
    }
  },

  login: async (identifier, password) => {
    set({ loading: true });

    try {
      const response = await api.login(identifier, password);

      if ("requires_mfa" in response) {
        set({ challenge: response.mfa_challenge });
        return "mfa";
      }

      setTokens(response);

      const user = await loadUser();
      set({ user, challenge: null });

      return "ok";
    } finally {
      set({ loading: false });
    }
  },

  sendOtp: async (phone) => {
    const response = await api.sendOtp(phone, "login");
    return response.debug_code;
  },

  verifyOtp: async (phone, code) => {
    set({ loading: true });

    try {
      const tokens = await api.verifyOtp(phone, "login", code);
      setTokens(tokens);

      const user = await loadUser();
      set({ user, challenge: null });
    } finally {
      set({ loading: false });
    }
  },

  verifyMfa: async (code) => {
    set({ loading: true });

    try {
      const challenge = get().challenge;

      if (!challenge) {
        throw new Error("No pending MFA challenge");
      }

      const tokens = await api.verifyMfa(challenge, code);
      setTokens(tokens);

      const user = await loadUser();
      set({ user, challenge: null });
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
        // Local logout must still complete if the refresh token has expired.
      }
    }

    setTokens(null);
    set({ user: null, challenge: null });
  },

  hydrate: async () => {
    if (!getAccessToken()) {
      set({ user: null, hydrated: true });
      return;
    }

    set({ loading: true });

    try {
      const user = await loadUser();
      set({ user });
    } catch {
      setTokens(null);
      set({ user: null });
    } finally {
      set({ loading: false, hydrated: true });
    }
  },

  updateUser: (patch) => {
    set((state) =>
      state.user
        ? { user: { ...state.user, ...patch } }
        : {},
    );
  },
}));
