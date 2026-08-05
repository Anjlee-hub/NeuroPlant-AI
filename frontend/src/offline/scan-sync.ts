import { api } from "@/lib/api";
import { addCompletedSync, type SyncEntry } from "@/offline/db";
import { registerSyncHandler } from "@/offline/sync";
import { useSyncUi } from "@/offline/sync-store";
import type { ScanSyncItem, ScanSyncOut } from "@/types/scan";

/** Queue type for offline crop scans — must match `enqueueSync("scan", …)`. */
export const SCAN_SYNC_TYPE = "scan";

/** Backend per-item error code for an already-synced scan (idempotency guard). */
export const CONFLICT_CODE = "duplicate_client_scan_id";

/** A queued offline scan — mirrors `ScanSyncItemIn`. */
export type ScanSyncPayload = ScanSyncItem;

/** Per-item failure from the server; message carries the machine code. */
export class ScanSyncItemError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(`${code}: ${message}`);
    this.name = "ScanSyncItemError";
    this.code = code;
  }
}

/**
 * Upload one queued scan to `POST /scans/sync` and reflect the outcome.
 *
 * The server owns reconciliation (created/replayed idempotency, validation,
 * per-item error codes) — this handler only translates its per-item results
 * into queue bookkeeping:
 *  - success: record the scan in the "recently synced" list (the queue entry
 *    itself is removed by `replay` once this resolves).
 *  - per-item failure: surface the message (and count the attempt) so the
 *    queue screen can show a retryable error / conflict badge.
 */
export async function syncScanEntry(entry: SyncEntry): Promise<void> {
  const payload = entry.payload as ScanSyncPayload;

  let result: ScanSyncOut;
  try {
    result = await api.syncScans([payload]);
  } catch (err) {
    // Network / transport failure: entry stays queued for retry.
    const message = err instanceof Error ? err.message : "Scan sync failed";
    useSyncUi.getState().recordFailed(message);
    throw err;
  }

  const item = result.results[0];
  if (!item || item.status === "failed") {
    const code = item?.error?.code ?? "sync_failed";
    const message = item?.error?.message ?? "Scan sync failed";
    useSyncUi.getState().recordFailed(message);
    throw new ScanSyncItemError(code, message);
  }

  if (item.status === "created") useSyncUi.getState().recordCreated();
  else useSyncUi.getState().recordReplayed();

  await addCompletedSync({
    clientScanId: payload.client_scan_id,
    diseaseName: item.scan?.disease_name ?? "",
    syncedAt: Date.now(),
  });
}

/** Register the "scan" handler so the auto-drain loop can replay it. */
export function registerScanSyncHandler(): void {
  registerSyncHandler(SCAN_SYNC_TYPE, syncScanEntry);
}
