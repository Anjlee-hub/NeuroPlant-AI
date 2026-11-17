import {
  enqueueSync,
  markSyncFailed,
  pendingSync,
  removeSync,
  type SyncEntry,
} from "@/offline/db";

/**
 * Offline sync queue. Mutations that fail while offline are enqueued in
 * IndexedDB and replayed here, in order, when connectivity returns.
 *
 * Handlers are registered per mutation type by the feature that owns them
 * (e.g. "scan" in M2, "order" in M6). Until a handler exists the entry is
 * dropped so an unknown type can never wedge the queue.
 */

export type SyncHandler = (entry: SyncEntry) => Promise<void>;

/** Retry budget before a persistently-failing entry is dropped. */
export const MAX_ATTEMPTS = 5;

const handlers = new Map<string, SyncHandler>();

export function registerSyncHandler(type: string, handler: SyncHandler): void {
  handlers.set(type, handler);
}

/** Attempt to upload a single entry; returns true when it can be dropped. */
async function replay(entry: SyncEntry): Promise<boolean> {
  const id = entry.id;
  if (id === undefined) return true;

  const handler = handlers.get(entry.type);
  if (!handler) return true; // Unknown type: drop rather than wedge.

  try {
    await handler(entry);
    await removeSync(id);
    return true;
  } catch (err) {
    const attempts = await markSyncFailed(
      id,
      err instanceof Error ? err.message : String(err),
    );
    // Give up on a persistently-failing entry so it can't block the queue.
    return attempts >= MAX_ATTEMPTS;
  }
}

/**
 * Drain the queue in insertion order. Safe to call repeatedly.
 * `onProgress` fires after each entry (count of entries already processed)
 * so the offline queue screen can render a progress bar.
 */
export async function processSyncQueue(
  onProgress?: (done: number) => void,
): Promise<void> {
  if (typeof navigator !== "undefined" && !navigator.onLine) return;
  const queue = await pendingSync();
  let done = 0;
  for (const entry of queue) {
    await replay(entry);
    done += 1;
    onProgress?.(done);
  }
}

/** Replay one queued entry by id — backs the queue screen's Retry action. */
export async function replayEntry(id: number): Promise<void> {
  const entry = (await pendingSync()).find((e) => e.id === id);
  if (entry) await replay(entry);
}

/** Convenience for offline-capable flows: enqueue (no-op when online). */
export async function queueOrRun(
  type: string,
  payload: unknown,
  run: () => Promise<void>,
): Promise<void> {
  if (typeof navigator !== "undefined" && navigator.onLine) {
    await run();
    return;
  }
  await enqueueSync(type, payload);
}

/**
 * Kick the loop on startup and whenever connectivity returns. Called once
 * from main.tsx (the service worker is registered separately by the PWA
 * plugin).
 */
export function startSyncLoop(): void {
  if (typeof window === "undefined") return;
  window.addEventListener("online", () => void processSyncQueue());
  void processSyncQueue();
}
