import { api } from "@/lib/api";
import {
  addCompletedSync,
  replaceSyncPayload,
  type SyncEntry,
} from "@/offline/db";
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

const inFlightSyncs = new Map<number, Promise<void>>();

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
export function syncScanEntry(entry: SyncEntry): Promise<void> {
  const queueEntryId = entry.id;
  if (queueEntryId === undefined) return syncScanEntryOnce(entry);

  const pending = inFlightSyncs.get(queueEntryId);
  if (pending) return pending;

  const sync = syncScanEntryOnce(entry).finally(() => {
    if (inFlightSyncs.get(queueEntryId) === sync) inFlightSyncs.delete(queueEntryId);
  });
  inFlightSyncs.set(queueEntryId, sync);
  return sync;
}

async function syncScanEntryOnce(entry: SyncEntry): Promise<void> {
  let payload = entry.payload as ScanSyncPayload;

  const send = async (item: ScanSyncPayload): Promise<ScanSyncOut> => {
    try {
      return await api.syncScans([item]);
    } catch (err) {
      // Network / transport failure: entry stays queued for retry.
      const message = err instanceof Error ? err.message : "Scan sync failed";
      useSyncUi.getState().recordFailed(message);
      throw err;
    }
  };

  let result = await send(payload);
  let item = result.results[0];
  if (item?.status === "failed" && item.error?.code === CONFLICT_CODE) {
    if (entry.id === undefined) {
      const message = "Cannot safely retry a scan without its queue entry ID";
      useSyncUi.getState().recordFailed(message);
      throw new ScanSyncItemError(CONFLICT_CODE, message);
    }
    const replacement: ScanSyncPayload = {
      ...payload,
      client_scan_id: crypto.randomUUID(),
    };
    if (!(await replaceSyncPayload(entry.id, replacement))) {
      const message = "The queued scan was removed before its ID could be refreshed";
      useSyncUi.getState().recordFailed(message);
      throw new ScanSyncItemError(CONFLICT_CODE, message);
    }
    payload = replacement;
    result = await send(payload);
    item = result.results[0];
  }
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
