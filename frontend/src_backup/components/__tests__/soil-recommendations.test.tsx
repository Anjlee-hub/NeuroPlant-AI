import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  SoilRecommendationsPanel,
  SoilRecommendationsView,
} from "@/components/treatment/soil-recommendations";
import { api } from "@/lib/api";
import type { SoilRecommendation } from "@/types/soil";

vi.mock("@/lib/api", () => ({
  api: { getScanSoilRecommendations: vi.fn() },
}));

const mockRec: SoilRecommendation = {
  catalog_version: "v1",
  disease: {
    id: 1,
    name: "Early Blight",
    crop_id: 1,
    crop_name: "Tomato",
  },
  recommended_soil_type: "Deep, well-drained sandy loam",
  ph_range: "6.0 – 6.8",
  moisture_level: "Moderate and even; avoid waterlogging",
  drainage: "Excellent",
  organic_matter: "3–5%",
  npk: "Balanced NPK",
  micronutrients: ["Calcium", "Boron"],
  compost: "15–20 t/ha well-rotted FYM",
  mulching: "Black plastic or straw mulch",
  soil_health: {
    label: "good",
    score: 4.0,
    summary: "Based on the crop's usual soil preferences.",
  },
  soil_suitability: "Tomato grows best in well-drained sandy loam.",
  improvement_suggestions: ["Raise beds 20–25 cm", "Get a soil test first"],
  disease_soil_notes: "Early Blight survives in the soil on crop debris.",
  severity: "severe",
  severity_notes: ["Severe attack — restore soil balance before replanting."],
  confidence: 0.92,
  confidence_note: null,
};

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const getScanSoilRecommendations = api.getScanSoilRecommendations as ReturnType<
  typeof vi.fn
>;

describe("SoilRecommendationsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows a loading skeleton while the request is pending", async () => {
    let resolveFn!: (value: SoilRecommendation) => void;
    getScanSoilRecommendations.mockImplementation(
      () => new Promise<SoilRecommendation>((resolve) => (resolveFn = resolve)),
    );
    renderWithClient(<SoilRecommendationsPanel scanId={7} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    resolveFn(mockRec);
    expect(await screen.findByText("Soil Health & Recommendations")).toBeInTheDocument();
  });

  it("renders the empty state for a 404 (no curated plan)", async () => {
    getScanSoilRecommendations.mockRejectedValue({ status: 404 });
    renderWithClient(<SoilRecommendationsPanel scanId={7} />);
    expect(
      await screen.findByText("No soil plan available"),
    ).toBeInTheDocument();
  });

  it("renders an error state with a retry button for other failures", async () => {
    getScanSoilRecommendations.mockRejectedValue(new Error("network down"));
    renderWithClient(<SoilRecommendationsPanel scanId={7} />);
    expect(await screen.findByText("Couldn't load soil guidance")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Retry" }),
    ).toBeInTheDocument();
  });

  it("renders the full soil plan on success", async () => {
    getScanSoilRecommendations.mockResolvedValue(mockRec);
    renderWithClient(<SoilRecommendationsPanel scanId={7} />);
    expect(
      await screen.findByText("Soil Health & Recommendations"),
    ).toBeInTheDocument();
    expect(screen.getByText("Good")).toBeInTheDocument();
    expect(screen.getByText("4.0")).toBeInTheDocument();
  });
});

describe("SoilRecommendationsView", () => {
  it("shows the soil-health score, suitability and suggestions", () => {
    render(<SoilRecommendationsView recommendation={mockRec} />);
    expect(screen.getByText("Soil Health")).toBeInTheDocument();
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "4");
    expect(screen.getByText("Tomato grows best in well-drained sandy loam.")).toBeInTheDocument();
    expect(screen.getByText("Raise beds 20–25 cm")).toBeInTheDocument();
    expect(screen.getByText("Get a soil test first")).toBeInTheDocument();
  });

  it("surfaces the disease-aware and severity notes", () => {
    render(<SoilRecommendationsView recommendation={mockRec} />);
    expect(screen.getByText("Early Blight survives in the soil on crop debris.")).toBeInTheDocument();
    expect(
      screen.getByText("Severe attack — restore soil balance before replanting."),
    ).toBeInTheDocument();
  });

  it("shows a confidence warning when the scan's confidence is low", () => {
    render(
      <SoilRecommendationsView
        recommendation={{ ...mockRec, confidence_note: "Detection confidence is low." }}
      />,
    );
    expect(screen.getByText("Detection confidence is low.")).toBeInTheDocument();
  });

  it("renders guidance cards collapsed and expands them on click", async () => {
    const user = userEvent.setup();
    render(<SoilRecommendationsView recommendation={mockRec} />);

    const soilTypeButton = screen.getByRole("button", {
      name: /Recommended Soil Type/,
    });
    const regionId = soilTypeButton.getAttribute("aria-controls");
    const region = regionId
      ? (document.getElementById(regionId) as HTMLElement | null)
      : null;
    expect(soilTypeButton).toHaveAttribute("aria-expanded", "false");
    expect(region).toHaveClass("hidden");

    await user.click(soilTypeButton);
    expect(soilTypeButton).toHaveAttribute("aria-expanded", "true");
    expect(region).not.toHaveClass("hidden");
    expect(within(region!).getByText("Deep, well-drained sandy loam")).toBeInTheDocument();
  });

  it("renders micronutrients as chips inside their card", async () => {
    const user = userEvent.setup();
    render(<SoilRecommendationsView recommendation={mockRec} />);

    const micronutrientsButton = screen.getByRole("button", {
      name: /Micronutrients/,
    });
    await user.click(micronutrientsButton);

    const regionId = micronutrientsButton.getAttribute("aria-controls");
    const region = regionId
      ? (document.getElementById(regionId) as HTMLElement | null)
      : null;
    expect(region).not.toHaveClass("hidden");
    expect(within(region!).getByText("Calcium")).toBeInTheDocument();
    expect(within(region!).getByText("Boron")).toBeInTheDocument();
  });
});
