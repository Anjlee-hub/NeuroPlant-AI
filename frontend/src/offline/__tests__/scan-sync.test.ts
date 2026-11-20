import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SyncEntry } from "@/offline/db";

const apiMock = vi.hoisted(() => ({ syncScans: vi.fn() }));
const dbMock = vi.hoisted(() => ({
  addCompletedSync: vi.fn(),
  replaceSyncPayload: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/offline/db", () => ({
  addCompletedSync: dbMock.addCompletedSync,
  replaceSyncPayload: dbMock.replaceSyncPayload,
}));

import {
  CONFLICT_CODE,
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

function okOutcome(
  status: "created" | "replayed",
  disease = "Late Blight",
  clientScanId = "11111111-1111-4111-8111-111111111111",
) {
  return {
    results: [
      {
        client_scan_id: clientScanId,
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
  dbMock.replaceSyncPayload.mockResolvedValue(true);
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

  it("persists a fresh ID before retrying a collision", async () => {
    const replacementId = "22222222-2222-4222-8222-222222222222";
    vi.spyOn(crypto, "randomUUID").mockReturnValue(replacementId);
    apiMock.syncScans
      .mockResolvedValueOnce({
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
      })
      .mockResolvedValueOnce(okOutcome("created", "Late Blight", replacementId));

    await syncScanEntry(makeEntry());

    expect(dbMock.replaceSyncPayload).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ client_scan_id: replacementId }),
    );
    expect(apiMock.syncScans).toHaveBeenNthCalledWith(
      2,
      [expect.objectContaining({ client_scan_id: replacementId })],
    );
    expect(dbMock.addCompletedSync).toHaveBeenCalledWith(
      expect.objectContaining({ clientScanId: replacementId }),
    );
    expect(useSyncUi.getState().created).toBe(1);
    expect(useSyncUi.getState().failed).toBe(0);
  });

  it("shares one recovery attempt for concurrent syncs of the same queue entry", async () => {
    const replacementId = "33333333-3333-4333-8333-333333333333";
    vi.spyOn(crypto, "randomUUID").mockReturnValue(replacementId);
    apiMock.syncScans
      .mockResolvedValueOnce({
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
      })
      .mockResolvedValueOnce(okOutcome("created", "Late Blight", replacementId));

    const entry = makeEntry();
    await Promise.all([syncScanEntry(entry), syncScanEntry(entry)]);

    expect(apiMock.syncScans).toHaveBeenCalledTimes(2);
    expect(dbMock.replaceSyncPayload).toHaveBeenCalledTimes(1);
    expect(dbMock.addCompletedSync).toHaveBeenCalledTimes(1);
  });

  it("does not retry a conflict if the replacement key cannot be saved", async () => {
    dbMock.replaceSyncPayload.mockResolvedValue(false);
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

    await expect(syncScanEntry(makeEntry())).rejects.toMatchObject({
      code: CONFLICT_CODE,
    });
    expect(apiMock.syncScans).toHaveBeenCalledTimes(1);
    expect(useSyncUi.getState().failed).toBe(1);
  });

  it("rethrows network failures so the queue marks the attempt", async () => {
    apiMock.syncScans.mockRejectedValue(new Error("Network error"));

    await expect(syncScanEntry(makeEntry())).rejects.toThrow("Network error");

    expect(useSyncUi.getState().failed).toBe(1);
    expect(useSyncUi.getState().lastError).toBe("Network error");
    expect(dbMock.addCompletedSync).not.toHaveBeenCalled();
  });
});
