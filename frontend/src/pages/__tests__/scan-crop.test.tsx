import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Scan, ScanExplain } from "@/types/scan";

// Mutable mocks so tests can drive auth + API outcomes per case.
const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  listCrops: vi.fn(),
  uploadScan: vi.fn(),
  getScanExplain: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({
  api: apiMock,
  errorMessage: (err: unknown) =>
    err instanceof Error ? err.message : "Request failed",
}));

import { ScanCropPage } from "@/pages/scan-crop";

const crops = [{ id: 1, name: "Maize", common_name: null }];

function makeScan(overrides: Partial<Scan> = {}): Scan {
  return {
    id: 11,
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
    preprocessing_time_ms: 12,
    inference_time_ms: 8,
    processing_time_ms: 31,
    image_path: "1/scans/a.jpg",
    processed_image_path: null,
    heatmap_path: null,
    media_items: [],
    sync_status: "synced",
    synced_at: null,
    rankings: [],
    ai_metadata: null,
    created_at: "2026-08-05T10:00:00",
    ...overrides,
  };
}

const explain: ScanExplain = {
  scan_id: 11,
  disease: { id: 1, name: "Late Blight", crop_id: 1, severity: "moderate", stage: "early", symptoms: [] },
  confidence: { top: 0.92, level: "high", advice: "Confident diagnosis — treat now." },
  top5: [{ disease_name: "Late Blight", confidence: 0.92, disease_id: 1, crop_id: 1 }],
  heatmap: { provider: "baseline", class_name: "Late Blight", time_ms: 15 },
  heatmap_url: null,
  overlay_url: "/media/1/heatmaps/overlay.png",
  explanation: "The AI focused on the leaf spots.",
  timing: { preprocessing_time_ms: 10, inference_time_ms: 8, processing_time_ms: 5, heatmap_time_ms: 15 },
  model: { provider: "baseline", model_name: "baseline", model_version: "v1", dataset_version: "v1" },
};

function renderCrop() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login-page</div> },
      { path: "/detect", element: <ScanCropPage /> },
      { path: "/scans", element: <div>history-page</div> },
      { path: "/scans/:scanId", element: <div>detail-page</div> },
    ],
    { initialEntries: ["/detect"] },
  );
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

describe("ScanCropPage", () => {
  beforeEach(() => {
    authMock.user = { id: 1, name: "Farmer" };
    vi.clearAllMocks();
    apiMock.listCrops.mockResolvedValue(crops);
    vi.spyOn(crypto, "randomUUID").mockReturnValue(
      "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    );
  });

  it("requires sign-in when logged out", () => {
    authMock.user = null;
    renderCrop();
    expect(
      screen.getByText("Sign in to scan a crop."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/login",
    );
  });

  it("renders the upload form with photo, crop and part controls", () => {
    renderCrop();
    expect(
      screen.getByRole("button", { name: "Upload photo" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Use camera" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Crop")).toBeInTheDocument();
    expect(screen.getByLabelText("Plant part")).toBeInTheDocument();
    // No photo selected → analyze is disabled.
    expect(screen.getByRole("button", { name: "Analyze photo" })).toBeDisabled();
  });

  it("submits the selected photo and shows the diagnosis result", async () => {
    const user = userEvent.setup();
    renderCrop();
    apiMock.uploadScan.mockResolvedValue(makeScan());
    apiMock.getScanExplain.mockResolvedValue(explain);

    // Pick a file via the hidden upload input.
    const input = screen.getByTestId("scan-upload-input");
    const file = new File(["jpeg-bytes"], "leaf.jpg", { type: "image/jpeg" });
    fireEvent.change(input, { target: { files: [file] } });

    // Wait for the async crops query so the option values exist to select.
    await screen.findByRole("option", { name: "Maize" });
    await user.selectOptions(screen.getByLabelText("Crop"), "1");
    await user.selectOptions(screen.getByLabelText("Plant part"), "leaf");
    await user.click(screen.getByRole("button", { name: "Analyze photo" }));

    // Result phase.
    expect(await screen.findByRole("heading", { name: "Late Blight" })).toBeInTheDocument();
    // 92% appears on both the ConfidenceBadge and the top-5 ranking row.
    expect(screen.getAllByText("92%").length).toBeGreaterThan(0);
    expect(screen.getByText("Moderate")).toBeInTheDocument();
    expect(screen.getByText("Saved to your scan history.")).toBeInTheDocument();
    // Upload carried the right payload.
    expect(apiMock.uploadScan).toHaveBeenCalledWith(
      expect.objectContaining({
        clientScanId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        cropId: 1,
        partType: "leaf",
      }),
    );
    // Explain payload (explanation + ranking + heatmap link) rendered.
    expect(await screen.findByText("The AI focused on the leaf spots.")).toBeInTheDocument();
    expect(screen.getByText("Confident diagnosis — treat now.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View full report" })).toHaveAttribute(
      "href",
      "/scans/11",
    );
    expect(screen.getByRole("link", { name: "View scan history" })).toHaveAttribute(
      "href",
      "/scans",
    );
  });

  it("surfaces a readable error when the upload fails", async () => {
    const user = userEvent.setup();
    renderCrop();
    apiMock.uploadScan.mockRejectedValue(new Error("bad image"));

    const input = screen.getByTestId("scan-upload-input");
    fireEvent.change(input, {
      target: {
        files: [new File(["x"], "leaf.jpg", { type: "image/jpeg" })],
      },
    });
    await user.click(screen.getByRole("button", { name: "Analyze photo" }));

    expect(await screen.findByText("Couldn't analyze the photo")).toBeInTheDocument();
    expect(screen.getByText("bad image")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
