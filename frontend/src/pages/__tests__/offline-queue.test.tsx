import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { act } from "react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CompletedSync, SyncEntry } from "@/offline/db";
import { useNetwork } from "@/offline/network";
import { CONFLICT_CODE } from "@/offline/scan-sync";
import { useSyncUi } from "@/offline/sync-store";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({ listCrops: vi.fn() }));

// The db mock is a real in-memory queue so action + refresh flows behave
// like IndexedDB would; syncMock references it (evaluated lazily at runtime).
const dbMock = vi.hoisted(() => {
  const queue: SyncEntry[] = [];
  const done: CompletedSync[] = [];
  return {
    pendingSync: vi.fn(async () => [...queue]),
    completedSyncs: vi.fn(async () => [...done]),
    removeSync: vi.fn(async (id: number) => {
      const i = queue.findIndex((entry) => entry.id === id);
      if (i >= 0) queue.splice(i, 1);
    }),
    removeCompletedSync: vi.fn(async (id: number) => {
      const i = done.findIndex((record) => record.id === id);
      if (i >= 0) done.splice(i, 1);
    }),
    clearCompletedSyncs: vi.fn(async () => {
      done.length = 0;
    }),
    addCompletedSync: vi.fn(async () => 1),
    queue,
    done,
  };
});

const syncMock = vi.hoisted(() => ({
  processSyncQueue: vi.fn(async () => {
    dbMock.queue.length = 0;
  }),
  replayEntry: vi.fn(async (id: number) => {
    const i = dbMock.queue.findIndex((entry) => entry.id === id);
    if (i >= 0) dbMock.queue.splice(i, 1);
  }),
  registerSyncHandler: vi.fn(),
  MAX_ATTEMPTS: 5,
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({
  api: apiMock,
  errorMessage: (err: unknown) =>
    err instanceof Error ? err.message : "Request failed",
}));
vi.mock("@/offline/db", () => dbMock);
vi.mock("@/offline/sync", () => syncMock);

import { OfflineQueuePage } from "@/pages/offline-queue";

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

function renderQueue() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login-page</div> },
      { path: "/detect", element: <div>detect-page</div> },
      { path: "/offline", element: <OfflineQueuePage /> },
    ],
    { initialEntries: ["/offline"] },
  );
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router, queryClient };
}

describe("OfflineQueuePage", () => {
  beforeEach(() => {
    authMock.user = { id: 1, name: "Farmer" };
    vi.clearAllMocks();
    apiMock.listCrops.mockResolvedValue([
      { id: 1, name: "Tomato", common_name: null },
      { id: 2, name: "Rice", common_name: "Paddy" },
    ]);
    dbMock.queue.length = 0;
    dbMock.done.length = 0;
    useNetwork.setState({ isOnline: true });
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

  it("prompts to sign in when not authenticated", () => {
    authMock.user = null;

    renderQueue();

    expect(screen.getByText("Sign in to view your offline queue.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
    expect(apiMock.listCrops).not.toHaveBeenCalled();
  });

  it("shows the empty state when nothing is queued", async () => {
    renderQueue();

    expect(await screen.findByText("No offline scans queued")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Scan a crop" })).toHaveAttribute(
      "href",
      "/detect",
    );
  });

  it("lists a pending scan with thumbnail, crop, timestamp and status", async () => {
    dbMock.queue.push(makeEntry());

    renderQueue();

    const img = await screen.findByRole("img", { name: "Queued scan image" });
    expect(img).toHaveAttribute("src", "data:image/jpeg;base64,aGVsbG8=");
    expect(await screen.findByText("Tomato")).toBeInTheDocument(); // crop via catalog
    expect(screen.getByText("Pending", { selector: "div" })).toBeInTheDocument();
    expect(screen.getByText("1 pending scan")).toBeInTheDocument();
  });

  it("shows a failed entry with its retry count and error message", async () => {
    dbMock.queue.push(
      makeEntry({ attempts: 2, lastError: "server: image too large" }),
    );

    renderQueue();

    expect(await screen.findByText("Failed", { selector: "div" })).toBeInTheDocument();
    expect(screen.getByText("2 failed attempts")).toBeInTheDocument();
    expect(screen.getByText("Error: server: image too large")).toBeInTheDocument();
  });

  it("flags a duplicate-client-scan conflict distinctly", async () => {
    dbMock.queue.push(
      makeEntry({ attempts: 1, lastError: `${CONFLICT_CODE}: already synced` }),
    );

    renderQueue();

    expect(
      await screen.findByText("Conflict — this scan was already synced on another device."),
    ).toBeInTheDocument();
  });

  it("retries a failed entry and reloads the queue", async () => {
    const user = userEvent.setup();
    dbMock.queue.push(makeEntry({ attempts: 1, lastError: "boom" }));

    renderQueue();
    await screen.findByText("Failed", { selector: "div" });

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(syncMock.replayEntry).toHaveBeenCalledWith(1);
    await vi.waitFor(() =>
      expect(screen.queryByText("Failed", { selector: "div" })).not.toBeInTheDocument(),
    );
    expect(screen.queryByText("Tomato")).not.toBeInTheDocument();
  });

  it("cancels a pending scan and reloads the queue", async () => {
    const user = userEvent.setup();
    dbMock.queue.push(makeEntry());

    renderQueue();
    await screen.findByText("Tomato");

    await user.click(screen.getByRole("button", { name: "Cancel this queued scan" }));

    expect(dbMock.removeSync).toHaveBeenCalledWith(1);
    await vi.waitFor(() =>
      expect(screen.queryByText("Tomato")).not.toBeInTheDocument(),
    );
  });

  it("syncs the whole queue and reports the outcome", async () => {
    const user = userEvent.setup();
    dbMock.queue.push(makeEntry());
    dbMock.queue.push(
      makeEntry({
        id: 2,
        payload: {
          client_scan_id: "22222222-2222-4222-8222-222222222222",
          images: [{ data: "aGVsbG8=", content_type: "image/jpeg" }],
          crop_id: 1,
          part_type: "leaf",
        },
      }),
    );

    renderQueue();
    await screen.findByText("2 pending scans");

    await user.click(screen.getByRole("button", { name: "Sync all" }));

    await vi.waitFor(() => expect(syncMock.processSyncQueue).toHaveBeenCalled());
    // The scan handler is mocked out here — simulate its per-item outcomes.
    useSyncUi.getState().recordCreated();
    useSyncUi.getState().recordReplayed();

    expect(
      await screen.findByText(/Sync complete — 1 new, 1 existing, 0 failed/),
    ).toBeInTheDocument();
    expect(screen.queryByText("2 pending scans")).not.toBeInTheDocument();
  });

  it("shows a progress bar while a drain is active", async () => {
    act(() => useSyncUi.getState().begin(2));

    renderQueue();

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    expect(screen.getByText("Syncing scans…")).toBeInTheDocument();
    expect(screen.getByText("0 / 2")).toBeInTheDocument();

    act(() => useSyncUi.getState().tick());
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
  });

  it("shows the offline banner and disables sync while offline", async () => {
    useNetwork.setState({ isOnline: false });
    dbMock.queue.push(makeEntry());

    renderQueue();

    expect(await screen.findByText(/You're offline/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sync all" })).toBeDisabled();
  });

  it("lists recently-synced scans and clears the completed queue", async () => {
    const user = userEvent.setup();
    dbMock.done.push({
      id: 7,
      clientScanId: "11111111-1111-4111-8111-111111111111",
      diseaseName: "Late Blight",
      syncedAt: 1_750_000_000_000,
    });

    renderQueue();
    expect(await screen.findByText("Late Blight")).toBeInTheDocument();
    expect(screen.getByText("Synced", { selector: "div" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear completed" }));

    expect(dbMock.clearCompletedSyncs).toHaveBeenCalled();
    await vi.waitFor(() =>
      expect(screen.queryByText("Late Blight")).not.toBeInTheDocument(),
    );
  });

  it("removes a single completed record", async () => {
    const user = userEvent.setup();
    dbMock.done.push({
      id: 7,
      clientScanId: "11111111-1111-4111-8111-111111111111",
      diseaseName: "Late Blight",
      syncedAt: 1_750_000_000_000,
    });

    renderQueue();
    await screen.findByText("Late Blight");

    await user.click(screen.getByRole("button", { name: "Remove from completed" }));

    expect(dbMock.removeCompletedSync).toHaveBeenCalledWith(7);
    await vi.waitFor(() =>
      expect(screen.queryByText("Late Blight")).not.toBeInTheDocument(),
    );
  });

  it("shows an error state when loading fails and recovers on retry", async () => {
    const user = userEvent.setup();
    dbMock.pendingSync.mockRejectedValueOnce(new Error("idb boom"));

    renderQueue();

    expect(await screen.findByText("Couldn't load the queue")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("No offline scans queued")).toBeInTheDocument();
  });
});
