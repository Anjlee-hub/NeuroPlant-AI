import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PlantOverview } from "@/components/doctor/plant-overview";
import type { RecoveryScan } from "@/types/recovery";

const scan: RecoveryScan = {
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
};

describe("PlantOverview", () => {
  it("renders the crop, part, disease and AI provenance", () => {
    render(<PlantOverview scan={scan} risk="high" />);

    expect(screen.getByText("Plant Overview")).toBeInTheDocument();
    expect(screen.getByText("Tomato")).toBeInTheDocument();
    expect(screen.getByText("Leaf")).toBeInTheDocument();
    expect(screen.getByText("Early Blight")).toBeInTheDocument();
    expect(screen.getByText("tflite")).toBeInTheDocument();
    expect(screen.getByText("1.0")).toBeInTheDocument();
  });

  it("shows the confidence, severity and risk badges", () => {
    render(<PlantOverview scan={scan} risk="high" />);

    expect(screen.getByText("92%")).toBeInTheDocument();
    expect(screen.getByText("Severe")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("renders the computed risk level from its own prop", () => {
    render(<PlantOverview scan={{ ...scan, severity: "low" }} risk="medium" />);
    expect(screen.getByText("Medium")).toBeInTheDocument();
    expect(screen.getByText("Low")).toBeInTheDocument();
  });

  it("falls back to a dash for unset fields", () => {
    render(
      <PlantOverview
        scan={{ ...scan, crop_name: null, part_type: null, model_version: null }}
        risk="low"
      />,
    );
    // crop + part + model all fall back to the "not set" dash.
    expect(screen.getAllByText("—")).toHaveLength(3);
  });
});
