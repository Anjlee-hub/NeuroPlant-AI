import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  ConfidenceBadge,
  SeverityBadge,
  SyncBadge,
  confidenceVariant,
  severityVariant,
  syncVariant,
} from "@/components/ui/status-badges";

describe("status badge variant helpers", () => {
  it("maps confidence bands to variants", () => {
    expect(confidenceVariant(0.9)).toBe("success");
    expect(confidenceVariant(0.85)).toBe("success"); // high boundary inclusive
    expect(confidenceVariant(0.7)).toBe("secondary");
    expect(confidenceVariant(0.6)).toBe("secondary"); // medium boundary inclusive
    expect(confidenceVariant(0.4)).toBe("destructive");
  });

  it("maps severity levels to variants", () => {
    expect(severityVariant("low")).toBe("success");
    expect(severityVariant("moderate")).toBe("secondary");
    expect(severityVariant("severe")).toBe("destructive");
  });

  it("maps sync statuses to variants", () => {
    expect(syncVariant("synced")).toBe("success");
    expect(syncVariant("pending")).toBe("outline");
    expect(syncVariant("failed")).toBe("destructive");
  });
});

describe("status badge components", () => {
  it("renders a formatted confidence badge", () => {
    render(<ConfidenceBadge value={0.92} />);
    expect(screen.getByText("92%")).toBeInTheDocument();
  });

  it("passes a hint tooltip through to the badge", () => {
    render(<ConfidenceBadge value={0.92} hint="Confidence" />);
    expect(screen.getByText("92%")).toHaveAttribute("title", "Confidence");
  });

  it("renders localized severity and sync labels", () => {
    render(<SeverityBadge severity="moderate" />);
    expect(screen.getByText("Moderate")).toBeInTheDocument();
    render(<SyncBadge status="pending" />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });
});
