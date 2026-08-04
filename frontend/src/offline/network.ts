import { create } from "zustand";

interface NetworkState {
  isOnline: boolean;
  setOnline: (online: boolean) => void;
}

/**
 * Connectivity state, kept in sync with the browser's online/offline
 * events. Drives the offline indicator and gates the sync queue drain.
 */
export const useNetwork = create<NetworkState>((set) => ({
  isOnline: typeof navigator === "undefined" ? true : navigator.onLine,
  setOnline: (isOnline) => set({ isOnline }),
}));

if (typeof window !== "undefined") {
  const { setOnline } = useNetwork.getState();
  window.addEventListener("online", () => setOnline(true));
  window.addEventListener("offline", () => setOnline(false));
}
