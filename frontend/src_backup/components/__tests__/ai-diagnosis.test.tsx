import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AiDiagnosis } from "@/components/doctor/ai-diagnosis";
import type { ScanExplain } from "@/types/scan";

const explain: ScanExplain = {
  scan_id: 7,
  disease: {
    id: 1,
    name: "Early Blight",
    crop_id: 1,
    severity: "severe",
    stage: "early",
    symptoms: ["Brown lesions on lower leaves", "Yellow halos around spots"],
  },
  confidence: { top: 0.92, level: "high", advice: "Confirm the diagnosis before spraying." },
  top5: [
    { disease_name: "Early Blight", confidence: 0.92, disease_id: 1, crop_id: 1 },
    { disease_name: "Late Blight", confidence: 0.05, disease_id: 2, crop_id: 1 },
  ],
  heatmap: { provider: "gradcam", class_name: "leaf", time_ms: 45 },
  heatmap_url: "http://test/media/heat.png",
  overlay_url: "http://test/media/overlay.png",
  explanation: "The model focused on the dark lesions clustered on the lower leaves.",
  timing: { preprocessing_time_ms: 4, inference_time_ms: 20, processing_time_ms: 30, heatmap_time_ms: 45 },
  model: { provider: "tflite", model_name: "leafnet", model_version: "1.0", dataset_version: "v1" },
};

describe("AiDiagnosis", () => {
  it("renders a graceful fallback when explainability data is missing", () => {
    render(<AiDiagnosis explain={null} />);
    expect(screen.getByText("AI Diagnosis")).toBeInTheDocument();
  });

  it("shows the explanation and what the AI observed", () => {
    render(<AiDiagnosis explain={explain} />);

    expect(
      screen.getByText("The model focused on the dark lesions clustered on the lower leaves."),
    ).toBeInTheDocument();
    expect(screen.getByText("What the AI Observed")).toBeInTheDocument();
    expect(screen.getByText("Brown lesions on lower leaves")).toBeInTheDocument();
    expect(screen.getByText("Yellow halos around spots")).toBeInTheDocument();
  });

  it("renders the heatmap overlay with its provider timing", () => {
    render(<AiDiagnosis explain={explain} />);

    const heatmap = screen.getByRole("img", { name: "Heatmap" });
    expect(heatmap).toHaveAttribute("src", "http://test/media/overlay.png");
    expect(screen.getByText(/gradcam/)).toBeInTheDocument();
  });

  it("ranks the top predictions with confidence bars", () => {
    render(<AiDiagnosis explain={explain} />);

    expect(screen.getByText("Top Predictions")).toBeInTheDocument();
    expect(screen.getByText("Late Blight")).toBeInTheDocument();
    expect(screen.getByText("5%")).toBeInTheDocument();
  });

  it("notes when no symptoms were recorded", () => {
    render(<AiDiagnosis explain={{ ...explain, disease: { ...explain.disease, symptoms: [] } }} />);
    expect(screen.getByText("No specific symptoms recorded")).toBeInTheDocument();
  });
});
