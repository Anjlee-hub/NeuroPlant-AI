import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SyncEntry } from "@/offline/db";

const apiMock = vi.hoisted(() => ({ syncScans: vi.fn() }));
const dbMock = vi.hoisted(() => ({ addCompletedSync: vi.fn() }));

vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/offline/db", () => ({ addCompletedSync: dbMock.addCompletedSync }));

import {
  CONFLICT_CODE,
  ScanSyncItemError,
  syncScanEntry,
} from "@/offline/scan-sync";
import { useSyncUi } from "@/offline/sync-store";

function makeEntry(overrides: Partial<SyncEntry> = {}): SyncEntry {
  return {
    id: 1,
    type: "scan",
    createdAt: 1_750_000_000_000,
    attempts: 0,
    payload: {
      client_scan_id: "11111111-1111-4111-8111-111111111111",
      images: [{ data: "aGVsbG8=", content_type: "image/jpeg" }],
      crop_id: 1,
      part_type: "leaf",
    },
    ...overrides,
  };
}

function okOutcome(status: "created" | "replayed", disease = "Late Blight") {
  return {
    results: [
      {
        client_scan_id: "11111111-1111-4111-8111-111111111111",
        status,
        scan: { id: 1, disease_name: disease },
        error: null,
      },
    ],
    total: 1,
    created: status === "created" ? 1 : 0,
    replayed: status === "replayed" ? 1 : 0,
    failed: 0,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  dbMock.addCompletedSync.mockResolvedValue(1);
  useSyncUi.setState({
    active: false,
    done: 0,
    total: 0,
    created: 0,
    replayed: 0,
    failed: 0,
    lastError: null,
    version: 0,
  });
});

describe("syncScanEntry", () => {
  it("records a created scan in the recently-synced list", async () => {
    apiMock.syncScans.mockResolvedValue(okOutcome("created"));

    await syncScanEntry(makeEntry());

    expect(apiMock.syncScans).toHaveBeenCalledWith([
      expect.objectContaining({ client_scan_id: "11111111-1111-4111-8111-111111111111" }),
    ]);
    expect(dbMock.addCompletedSync).toHaveBeenCalledWith({
      clientScanId: "11111111-1111-4111-8111-111111111111",
      diseaseName: "Late Blight",
      syncedAt: expect.any(Number),
    });
    expect(useSyncUi.getState().created).toBe(1);
    expect(useSyncUi.getState().replayed).toBe(0);
    expect(useSyncUi.getState().failed).toBe(0);
  });

  it("counts a replayed (already-synced) scan as success", async () => {
    apiMock.syncScans.mockResolvedValue(okOutcome("replayed"));

    await syncScanEntry(makeEntry());

    expect(useSyncUi.getState().created).toBe(0);
    expect(useSyncUi.getState().replayed).toBe(1);
    expect(useSyncUi.getState().failed).toBe(0);
  });

  it("throws a typed conflict error and records the failure", async () => {
    apiMock.syncScans.mockResolvedValue({
      results: [
        {
          client_scan_id: "11111111-1111-4111-8111-111111111111",
          status: "failed",
          scan: null,
          error: {
            code: CONFLICT_CODE,
            message: "already synced by another user",
          },
        },
      ],
      total: 1,
      created: 0,
      replayed: 0,
      failed: 1,
    });

    let thrown: unknown;
    try {
      await syncScanEntry(makeEntry());
    } catch (err) {
      thrown = err;
    }
    expect(thrown).toBeInstanceOf(ScanSyncItemError);
    expect(thrown).toMatchObject({ code: CONFLICT_CODE });

    expect(useSyncUi.getState().failed).toBe(1);
    expect(useSyncUi.getState().lastError).toBe("already synced by another user");
    expect(dbMock.addCompletedSync).not.toHaveBeenCalled();
  });

  it("rethrows network failures so the queue marks the attempt", async () => {
    apiMock.syncScans.mockRejectedValue(new Error("Network error"));

    await expect(syncScanEntry(makeEntry())).rejects.toThrow("Network error");

    expect(useSyncUi.getState().failed).toBe(1);
    expect(useSyncUi.getState().lastError).toBe("Network error");
    expect(dbMock.addCompletedSync).not.toHaveBeenCalled();
  });
});
