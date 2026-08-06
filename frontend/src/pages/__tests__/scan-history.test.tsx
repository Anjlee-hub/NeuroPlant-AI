import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Scan } from "@/types/scan";

// Mutable mocks so tests can drive auth + API outcomes per case.
const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  listScans: vi.fn(),
  listCrops: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

import { ScanHistoryPage } from "@/pages/scan-history";

function makeScan(overrides: Partial<Scan> = {}): Scan {
  return {
    id: 1,
    client_scan_id: "11111111-1111-4111-8111-111111111111",
    crop_id: 1,
    part_type: "leaf",
    disease_id: 1,
    disease_name: "Late Blight",
    confidence: 0.92,
    severity: "moderate",
    stage: "early",
    provider: "baseline",
    model_name: "rule-baseline",
    model_version: "baseline-v1",
    dataset_version: "v1",
    preprocessing_time_ms: 12.4,
    inference_time_ms: 8.1,
    processing_time_ms: 31.9,
    image_path: "1/scans/a.jpg",
    processed_image_path: "1/processed/a.jpg",
    heatmap_path: null,
    media_items: [],
    sync_status: "synced",
    synced_at: "2026-08-04T09:14:52",
    rankings: [],
    ai_metadata: null,
    created_at: "2026-08-04T09:14:52",
    ...overrides,
  };
}

function renderScans() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login-page</div> },
      { path: "/detect", element: <div>detect-page</div> },
      { path: "/scans", element: <ScanHistoryPage /> },
      { path: "/scans/:scanId", element: <div>detail-page</div> },
    ],
    { initialEntries: ["/scans"] },
  );
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router, queryClient };
}

const emptyList = {
  items: [] as Scan[],
  total: 0,
  page: 1,
  page_size: 12,
  has_next: false,
};

describe("ScanHistoryPage", () => {
  beforeEach(() => {
    authMock.user = { id: 1, name: "Farmer" };
    vi.clearAllMocks();
    apiMock.listScans.mockResolvedValue(emptyList);
    apiMock.listCrops.mockResolvedValue([
      { id: 1, name: "Tomato", common_name: null },
      { id: 2, name: "Rice", common_name: "Paddy" },
    ]);
  });

  it("shows loading skeletons, then the scan list", async () => {
    apiMock.listScans.mockResolvedValue({
      items: [makeScan()],
      total: 1,
      page: 1,
      page_size: 12,
      has_next: false,
    });

    renderScans();

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(await screen.findByText("Late Blight")).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
    // The filter selects render the same words as <option>s — scope to the badge divs.
    expect(screen.getByText("Synced", { selector: "div" })).toBeInTheDocument();
    expect(screen.getByText("Moderate", { selector: "div" })).toBeInTheDocument();
    expect(screen.getByText("1 scan")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 1")).toBeInTheDocument();
  });

  it("shows the empty state when there are no scans", async () => {
    renderScans();

    expect(await screen.findByText("No scans yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Scan a crop" })).toBeInTheDocument();
  });

  it("shows an error state and refetches on retry", async () => {
    const user = userEvent.setup();
    apiMock.listScans
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValue({
        items: [makeScan()],
        total: 1,
        page: 1,
        page_size: 12,
        has_next: false,
      });

    renderScans();

    expect(await screen.findByText("Couldn't load your scans")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Late Blight")).toBeInTheDocument();
  });

  it("prompts to sign in when not authenticated", () => {
    authMock.user = null;

    renderScans();

    expect(screen.getByText("Sign in to view your scan history.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
    expect(apiMock.listScans).not.toHaveBeenCalled();
  });

  it("navigates to the detail page when a scan is clicked", async () => {
    const user = userEvent.setup();
    apiMock.listScans.mockResolvedValue({
      items: [makeScan()],
      total: 1,
      page: 1,
      page_size: 12,
      has_next: false,
    });

    const { router } = renderScans();

    await user.click(await screen.findByText("Late Blight"));
    expect(router.state.location.pathname).toBe("/scans/1");
  });

  it("applies a severity filter to the API query", async () => {
    const user = userEvent.setup();
    apiMock.listScans.mockResolvedValue({
      items: [makeScan()],
      total: 1,
      page: 1,
      page_size: 12,
      has_next: false,
    });

    renderScans();
    await screen.findByText("Late Blight");

    await user.selectOptions(screen.getByLabelText("Severity"), "moderate");

    await vi.waitFor(() => {
      expect(apiMock.listScans).toHaveBeenLastCalledWith(
        expect.objectContaining({ severity: "moderate", page: 1 }),
      );
    });
  });

  it("requests the next page and disables buttons at the edges", async () => {
    const user = userEvent.setup();
    apiMock.listScans.mockResolvedValue({
      items: [makeScan(), makeScan({ id: 2, disease_name: "Early Blight" })],
      total: 40,
      page: 1,
      page_size: 12,
      has_next: true,
    });

    renderScans();
    await screen.findByText("Late Blight");

    const next = screen.getByRole("button", { name: "Next" });
    const prev = screen.getByRole("button", { name: "Previous" });
    expect(prev).toBeDisabled();
    expect(next).toBeEnabled();

    await user.click(next);
    // Generous timeout: refetch latency varies under full-suite worker load.
    await vi.waitFor(
      () => {
        expect(apiMock.listScans).toHaveBeenLastCalledWith(
          expect.objectContaining({ page: 2 }),
        );
      },
      { timeout: 5000 },
    );
  });
});
