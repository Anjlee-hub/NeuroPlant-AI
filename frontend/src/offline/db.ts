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
}

const DB_NAME = "neuroplant";
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase<NeuroplantDB>> | null = null;

function getDb(): Promise<IDBPDatabase<NeuroplantDB>> {
  if (!dbPromise) {
    dbPromise = openDB<NeuroplantDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        const queue = db.createObjectStore("syncQueue", {
          keyPath: "id",
          autoIncrement: true,
        });
        queue.createIndex("by-created", "createdAt");
        db.createObjectStore("kv", { keyPath: "key" });
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
