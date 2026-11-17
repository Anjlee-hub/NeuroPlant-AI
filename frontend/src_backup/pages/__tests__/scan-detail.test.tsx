import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Scan, ScanExplain } from "@/types/scan";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  getScan: vi.fn(),
  getScanExplain: vi.fn(),
  listCrops: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

import { ScanDetailPage } from "@/pages/scan-detail";

function makeScan(): Scan {
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
    heatmap_path: "1/heatmaps/o.png",
    media_items: [
      {
        source_type: "upload",
        path: "1/scans/a.jpg",
        url: "/media/1/scans/a.jpg",
        part_type: "leaf",
        width: 224,
        height: 224,
        content_type: "image/jpeg",
      },
    ],
    sync_status: "synced",
    synced_at: "2026-08-04T09:14:52",
    rankings: [{ disease_name: "Late Blight", confidence: 0.92, disease_id: 1, crop_id: 1 }],
    ai_metadata: null,
    created_at: "2026-08-04T09:14:52",
  };
}

function makeExplain(overrides: Partial<ScanExplain> = {}): ScanExplain {
  return {
    scan_id: 1,
    disease: {
      id: 1,
      name: "Late Blight",
      crop_id: 1,
      severity: "moderate",
      stage: "early",
      symptoms: [],
    },
    confidence: {
      top: 0.92,
      level: "high",
      advice: "High-confidence result — the pattern is a strong match for this disease.",
    },
    top5: [
      { disease_name: "Late Blight", confidence: 0.92, disease_id: 1, crop_id: 1 },
      { disease_name: "Early Blight", confidence: 0.04, disease_id: 1, crop_id: 1 },
    ],
    heatmap: { provider: "baseline", class_name: "Late Blight", time_ms: 18.2 },
    heatmap_url: "/media/1/heatmaps/h.png",
    overlay_url: "/media/1/heatmaps/o.png",
    explanation:
      "This photo was classified as Late Blight with 92% confidence. The heatmap overlay marks the image regions the model focused on.",
    timing: {
      preprocessing_time_ms: 12.4,
      inference_time_ms: 8.1,
      processing_time_ms: 31.9,
      heatmap_time_ms: 18.2,
    },
    model: {
      provider: "baseline",
      model_name: "rule-baseline",
      model_version: "baseline-v1",
      dataset_version: "v1",
    },
    ...overrides,
  };
}

function renderDetail() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login-page</div> },
      { path: "/scans", element: <div>history-page</div> },
      { path: "/scans/:scanId", element: <ScanDetailPage /> },
    ],
    { initialEntries: ["/scans/1"] },
  );
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router, queryClient };
}

describe("ScanDetailPage", () => {
  beforeEach(() => {
    authMock.user = { id: 1, name: "Farmer" };
    vi.clearAllMocks();
    apiMock.listCrops.mockResolvedValue([
      { id: 1, name: "Tomato", common_name: null },
      { id: 2, name: "Rice", common_name: "Paddy" },
    ]);
  });

  it("shows a loading skeleton, then the scan details", async () => {
    apiMock.getScan.mockResolvedValue(makeScan());
    apiMock.getScanExplain.mockResolvedValue(makeExplain());

    renderDetail();

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(await screen.findByText("High confidence")).toBeInTheDocument();
    expect(screen.getByText("Tomato")).toBeInTheDocument(); // crop_id resolved via catalog
    expect(screen.getByText("baseline-v1")).toBeInTheDocument(); // model version
    expect(screen.getByText("v1")).toBeInTheDocument(); // dataset version
    expect(screen.getByText("What the AI saw")).toBeInTheDocument();
    expect(screen.getByText("Top predictions")).toBeInTheDocument();
  });

  it("shows an error state and refetches on retry", async () => {
    const user = userEvent.setup();
    apiMock.getScan
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValue(makeScan());
    apiMock.getScanExplain.mockResolvedValue(makeExplain());

    renderDetail();

    expect(await screen.findByText("Couldn't load this scan")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("High confidence")).toBeInTheDocument();
  });

  it("prompts to sign in when not authenticated", () => {
    authMock.user = null;

    renderDetail();

    expect(screen.getByText("Sign in to view scan details.")).toBeInTheDocument();
    expect(apiMock.getScan).not.toHaveBeenCalled();
    expect(apiMock.getScanExplain).not.toHaveBeenCalled();
  });

  it("copies the prediction to the clipboard", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    apiMock.getScan.mockResolvedValue(makeScan());
    apiMock.getScanExplain.mockResolvedValue(makeExplain());

    renderDetail();
    await screen.findByText("High confidence");

    await user.click(screen.getByRole("button", { name: "Copy prediction" }));

    expect(writeText).toHaveBeenCalledWith(
      expect.stringContaining("Late Blight"),
    );
    expect(await screen.findByText("Copied!")).toBeInTheDocument();
  });

  it("offers a downloadable heatmap", async () => {
    apiMock.getScan.mockResolvedValue(makeScan());
    apiMock.getScanExplain.mockResolvedValue(makeExplain());

    renderDetail();

    const link = await screen.findByRole("link", { name: "Download heatmap" });
    expect(link).toHaveAttribute("download", "scan-1-heatmap.png");
    expect(link).toHaveAttribute("href", "/media/1/heatmaps/o.png");
  });

  it("zooms into the uploaded image and closes on the close button", async () => {
    const user = userEvent.setup();
    apiMock.getScan.mockResolvedValue(makeScan());
    apiMock.getScanExplain.mockResolvedValue(makeExplain());

    renderDetail();
    await screen.findByText("High confidence");

    await user.click(screen.getByRole("button", { name: "Zoom image" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows a future-ready share placeholder", async () => {
    const user = userEvent.setup();
    apiMock.getScan.mockResolvedValue(makeScan());
    apiMock.getScanExplain.mockResolvedValue(makeExplain());

    renderDetail();
    await screen.findByText("High confidence");

    await user.click(screen.getByRole("button", { name: "Share" }));
    expect(screen.getByText("Sharing is coming soon.")).toBeInTheDocument();
  });

  it("shows a placeholder when no heatmap exists", async () => {
    apiMock.getScan.mockResolvedValue(makeScan());
    apiMock.getScanExplain.mockResolvedValue(
      makeExplain({ heatmap: null, heatmap_url: null, overlay_url: null }),
    );

    renderDetail();

    expect(await screen.findByText("No heatmap available")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Download heatmap" })).not.toBeInTheDocument();
  });

  it("shows a low-confidence recommendation", async () => {
    apiMock.getScan.mockResolvedValue(makeScan());
    apiMock.getScanExplain.mockResolvedValue(
      makeExplain({
        confidence: {
          top: 0.42,
          level: "low",
          advice: "Low-confidence result — please verify with an expert.",
        },
      }),
    );

    renderDetail();

    expect(
      await screen.findByText("Low confidence — verify before treating"),
    ).toBeInTheDocument();
  });
});
