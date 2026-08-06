import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DiseaseRecommendation } from "@/types/recommendation";
import type { RecoveryTracker } from "@/types/recovery";
import type { ScanExplain } from "@/types/scan";
import type { SoilRecommendation } from "@/types/soil";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  getScanRecoveryTracker: vi.fn(),
  getScanExplain: vi.fn(),
  getScanRecommendations: vi.fn(),
  getScanSoilRecommendations: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

import { ScanDoctorPage } from "@/pages/scan-doctor";

const tracker: RecoveryTracker = {
  scan: {
    id: 7,
    disease_name: "Early Blight",
    crop_id: 1,
    crop_name: "Tomato",
    part_type: "leaf",
    severity: "severe",
    stage: "early",
    confidence: 0.92,
    provider: "tflite",
    model_version: "1.0",
    created_at: "2026-08-06T09:00:00Z",
  },
  risk: "high",
  recovery_percentage: 0.4,
  status: "on_track",
  total_treatments: 1,
  timeline: [
    {
      id: 1,
      scan_id: 7,
      treatment_applied: "Neem oil spray",
      notes: "Sprayed both sides",
      progress: "improving",
      applied_at: "2026-08-06T09:30:00Z",
      created_at: "2026-08-06T09:30:00Z",
    },
  ],
  updated_at: "2026-08-06T09:30:00Z",
};

const explain: ScanExplain = {
  scan_id: 7,
  disease: {
    id: 1,
    name: "Early Blight",
    crop_id: 1,
    severity: "severe",
    stage: "early",
    symptoms: ["Brown lesions on lower leaves"],
  },
  confidence: { top: 0.92, level: "high", advice: "Confirm before spraying." },
  top5: [{ disease_name: "Early Blight", confidence: 0.92, disease_id: 1, crop_id: 1 }],
  heatmap: { provider: "gradcam", class_name: "leaf", time_ms: 45 },
  heatmap_url: "http://test/media/heat.png",
  overlay_url: "http://test/media/overlay.png",
  explanation: "The model focused on the dark lesions clustered on the lower leaves.",
  timing: { preprocessing_time_ms: 4, inference_time_ms: 20, processing_time_ms: 30, heatmap_time_ms: 45 },
  model: { provider: "tflite", model_name: "leafnet", model_version: "1.0", dataset_version: "v1" },
};

const treatment: DiseaseRecommendation = {
  catalog_version: "v1",
  disease: { id: 1, name: "Early Blight", crop_id: 1, crop_name: "Tomato" },
  overview: "A common fungal disease in humid weather.",
  cause: null,
  symptoms: [],
  severity: null,
  spread_mechanism: null,
  homemade_remedies: [
    {
      title: "Baking soda spray",
      category: "homemade-spray",
      ingredients: ["Baking soda", "Water"],
      instructions: "Mix and spray weekly.",
      frequency: "Weekly",
    },
  ],
  organic_remedies: [],
  chemical_recommendations: [],
  fertilizer: null,
  watering: null,
  sunlight: null,
  temperature: null,
  humidity: null,
  prevention_tips: [],
  recovery_timeline: null,
  isolation: null,
  monitoring_advice: [],
};

const soil: SoilRecommendation = {
  catalog_version: "v1",
  disease: { id: 1, name: "Early Blight", crop_id: 1, crop_name: "Tomato" },
  recommended_soil_type: "Deep, well-drained sandy loam",
  ph_range: "6.0 – 6.8",
  moisture_level: null,
  drainage: null,
  organic_matter: null,
  npk: null,
  micronutrients: [],
  compost: null,
  mulching: null,
  soil_health: { label: "good", score: 4.0, summary: "Suitable for this crop." },
  soil_suitability: "Tomato grows best in well-drained sandy loam.",
  improvement_suggestions: ["Add compost"],
  disease_soil_notes: null,
  severity: "severe",
  severity_notes: [],
  confidence: 0.92,
  confidence_note: null,
};

function renderPage() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/scans/:scanId", element: <div>detail</div> },
      { path: "/scans/:scanId/doctor", element: <ScanDoctorPage /> },
    ],
    { initialEntries: ["/scans/7/doctor"] },
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("ScanDoctorPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.print = vi.fn();
    apiMock.getScanRecoveryTracker.mockResolvedValue(tracker);
    apiMock.getScanExplain.mockResolvedValue(explain);
    apiMock.getScanRecommendations.mockResolvedValue(treatment);
    apiMock.getScanSoilRecommendations.mockResolvedValue(soil);
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage();
    expect(await screen.findByText("Sign in to view scan details.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });

  it("renders the full dashboard: overview, diagnosis, treatment, soil, recovery", async () => {
    authMock.user = { id: 1, name: "Tester" };
    renderPage();

    // The "Crop Doctor" title shows while the skeleton loads too, so wait for
    // tracker content before asserting on the resolved panels.
    expect(await screen.findByRole("heading", { name: "Crop Doctor" })).toBeInTheDocument();
    await screen.findByText("Neem oil spray");

    // Plant Overview (with the resolved crop name).
    expect(screen.getAllByText("Plant Overview").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tomato").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Early Blight").length).toBeGreaterThan(0);

    // AI Diagnosis (explanation + heatmap).
    expect(screen.getByRole("heading", { name: "AI Diagnosis" })).toBeInTheDocument();
    expect(
      screen.getByText("The model focused on the dark lesions clustered on the lower leaves."),
    ).toBeInTheDocument();

    // Treatment + soil panels render their own content.
    expect(screen.getAllByText(/Treatment Recommendations/).length).toBeGreaterThan(0);
    expect(await screen.findByText("Baking soda spray")).toBeInTheDocument();
    expect(screen.getAllByText(/Soil Recommendations/).length).toBeGreaterThan(0);
    expect(await screen.findByText("Add compost")).toBeInTheDocument();

    // Recovery tracker (heading + progress + timeline).
    expect(screen.getByRole("heading", { name: "Crop Recovery Tracker" })).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByText("Neem oil spray")).toBeInTheDocument();
  });

  it("downloads the PDF report via window.print", async () => {
    authMock.user = { id: 1, name: "Tester" };
    renderPage();
    await screen.findByRole("heading", { name: "Crop Doctor" });

    await userEvent.click(screen.getByRole("button", { name: "Download PDF report" }));
    expect(window.print).toHaveBeenCalledTimes(1);
  });

  it("shows an error state with retry when the tracker fails to load", async () => {
    authMock.user = { id: 1, name: "Tester" };
    apiMock.getScanRecoveryTracker.mockRejectedValue(new Error("boom"));
    renderPage();

    expect(await screen.findByText("Couldn't load this scan")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
