import { create } from "zustand";

/**
 * Live state of offline-scan syncs, written by the scan sync handler and read
 * by the offline queue screen. Kept separate from the IndexedDB queue so the
 * screen can animate a progress bar and surface the last drain's outcome
 * without polling the database.
 */

export interface SyncUiState {
  /** True while a drain is running (drives the progress bar). */
  active: boolean;
  /** Progress of the current drain. */
  done: number;
  total: number;
  /** Outcome totals of the current (or last) drain. */
  created: number;
  replayed: number;
  failed: number;
  /** Human-readable message from the last failed item or network error. */
  lastError: string | null;
  /**
   * Bumped on every outcome so a subscriber (the offline queue screen) can
   * reload the IndexedDB queue after a drain that it didn't start itself.
   */
  version: number;

  /** Start a drain; resets the previous outcome. */
  begin: (total: number) => void;
  /** Mark one entry of the current drain as processed. */
  tick: () => void;
  /** End the current drain (progress bar stops). */
  finish: () => void;
  recordCreated: () => void;
  recordReplayed: () => void;
  recordFailed: (message: string) => void;
}

export const useSyncUi = create<SyncUiState>((set) => ({
  active: false,
  done: 0,
  total: 0,
  created: 0,
  replayed: 0,
  failed: 0,
  lastError: null,
  version: 0,

  begin: (total) =>
    set({
      active: true,
      done: 0,
      total,
      created: 0,
      replayed: 0,
      failed: 0,
      lastError: null,
    }),
  tick: () => set((state) => ({ done: state.done + 1 })),
  finish: () => set({ active: false }),
  recordCreated: () =>
    set((state) => ({ created: state.created + 1, version: state.version + 1 })),
  recordReplayed: () =>
    set((state) => ({ replayed: state.replayed + 1, version: state.version + 1 })),
  recordFailed: (message) =>
    set((state) => ({
      failed: state.failed + 1,
      lastError: message,
      version: state.version + 1,
    })),
}));
