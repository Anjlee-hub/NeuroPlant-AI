import { type DBSchema, type IDBPDatabase, openDB } from "idb";

/**
 * Local-first persistence layer (IndexedDB via `idb`).
 *
 * Stores:
 *  - `syncQueue`: offline mutations awaiting upload. Entries are appended on
 *    a failed/offline write and drained by `processSyncQueue()` when online.
 *    Keyed by auto-incrementing id, indexed by createdAt.
 *  - `kv`: lightweight key/value cache for read-through data (weather,
 *    prices, catalog) so the UI works offline.
 *
 * Feature stores (scans, draft orders, …) are added per milestone without
 * changing this module's contract — see `DB_VERSION` bump below.
 */

export interface SyncEntry {
  id?: number;
  type: string;
  payload: unknown;
  createdAt: number;
  attempts: number;
  lastError?: string;
}

export interface KvEntry {
  key: string;
  value: unknown;
  updatedAt: number;
}

/**
 * A scan that finished syncing. Successful entries are removed from
 * `syncQueue` as soon as the server acknowledges them, so this store keeps a
 * short-lived "recently synced" record for the queue screen. Cleared by the
 * user (Clear completed) or when the list grows — it is not authoritative.
 */
export interface CompletedSync {
  id?: number;
  clientScanId: string;
  diseaseName: string;
  syncedAt: number;
}

interface NeuroplantDB extends DBSchema {
  syncQueue: {
    key: number;
    value: SyncEntry;
    indexes: { "by-created": number };
  };
  kv: {
    key: string;
    value: KvEntry;
  };
  completedQueue: {
    key: number;
    value: CompletedSync;
  };
}

const DB_NAME = "neuroplant";
const DB_VERSION = 2;

let dbPromise: Promise<IDBPDatabase<NeuroplantDB>> | null = null;

function getDb(): Promise<IDBPDatabase<NeuroplantDB>> {
  if (!dbPromise) {
    dbPromise = openDB<NeuroplantDB>(DB_NAME, DB_VERSION, {
      upgrade(db, oldVersion) {
        if (oldVersion < 1) {
          const queue = db.createObjectStore("syncQueue", {
            keyPath: "id",
            autoIncrement: true,
          });
          queue.createIndex("by-created", "createdAt");
          db.createObjectStore("kv", { keyPath: "key" });
        }
        if (oldVersion < 2) {
          // Recently-synced scan records shown on the offline queue screen.
          db.createObjectStore("completedQueue", {
            keyPath: "id",
            autoIncrement: true,
          });
        }
      },
    });
  }
  return dbPromise;
}

/* ---------- Sync queue ---------- */

/** Queue an offline mutation. Resolves with the new entry id. */
export async function enqueueSync(
  type: string,
  payload: unknown,
): Promise<number> {
  const db = await getDb();
  return db.add("syncQueue", {
    type,
    payload,
    createdAt: Date.now(),
    attempts: 0,
  });
}

/** All pending entries, oldest first. */
export async function pendingSync(): Promise<SyncEntry[]> {
  const db = await getDb();
  return db.getAllFromIndex("syncQueue", "by-created");
}

/** Remove a drained entry. */
export async function removeSync(id: number): Promise<void> {
  const db = await getDb();
  await db.delete("syncQueue", id);
}

/** Record a failed attempt (drives retry backoff / drop-after-N). */
export async function markSyncFailed(
  id: number,
  error: string,
): Promise<number> {
  const db = await getDb();
  const tx = db.transaction("syncQueue", "readwrite");
  const entry = await tx.store.get(id);
  if (entry) {
    entry.attempts += 1;
    entry.lastError = error;
    await tx.store.put(entry);
  }
  await tx.done;
  return entry?.attempts ?? 0;
}

/* ---------- Recently-synced queue ---------- */

/** Cap on kept completion records — the queue screen only needs a short list. */
const MAX_COMPLETED = 100;

/** Record a scan that just synced successfully. Resolves with its id. */
export async function addCompletedSync(
  record: Omit<CompletedSync, "id">,
): Promise<number> {
  const db = await getDb();
  const id = await db.add("completedQueue", record);
  const all = await db.getAll("completedQueue");
  if (all.length > MAX_COMPLETED) {
    // Trim the oldest beyond the cap (all is id-ordered, so the head is oldest).
    const tx = db.transaction("completedQueue", "readwrite");
    for (const stale of all.slice(0, all.length - MAX_COMPLETED)) {
      if (stale.id !== undefined) await tx.store.delete(stale.id);
    }
    await tx.done;
  }
  return id;
}

/** Recently-synced scans, newest first. */
export async function completedSyncs(): Promise<CompletedSync[]> {
  const db = await getDb();
  const all = await db.getAll("completedQueue");
  return all.sort((a, b) => b.syncedAt - a.syncedAt);
}

/** Dismiss a single completed record. */
export async function removeCompletedSync(id: number): Promise<void> {
  const db = await getDb();
  await db.delete("completedQueue", id);
}

/** Empty the recently-synced list. */
export async function clearCompletedSyncs(): Promise<void> {
  const db = await getDb();
  await db.clear("completedQueue");
}

/* ---------- Key/value cache ---------- */

export async function setKv<T>(key: string, value: T): Promise<void> {
  const db = await getDb();
  await db.put("kv", { key, value, updatedAt: Date.now() });
}

export async function getKv<T>(key: string): Promise<T | undefined> {
  const db = await getDb();
  const row = await db.get("kv", key);
  return row?.value as T | undefined;
}

export async function clearKv(): Promise<void> {
  const db = await getDb();
  await db.clear("kv");
}
