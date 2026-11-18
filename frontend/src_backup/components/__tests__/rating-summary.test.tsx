import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RatingSummaryCard } from "@/components/marketplace/rating-summary";

describe("RatingSummaryCard", () => {
  it("shows the average, review count and a five-row distribution", () => {
    render(
      <RatingSummaryCard
        summary={{
          average: 4.6,
          total: 5,
          distribution: { "1": 0, "2": 0, "3": 0, "4": 1, "5": 4 },
        }}
      />,
    );

    expect(screen.getByText("4.6")).toBeInTheDocument();
    expect(screen.getByText("5 reviews")).toBeInTheDocument();
    // Counts for 5★ (4) and 4★ (1); the rest are zero-filled.
    expect(screen.getAllByText("4")).toHaveLength(2); // "4★" label + its count
    expect(screen.getAllByText("1")).toHaveLength(2); // count for 4★ + "1★" label
    expect(screen.getAllByText("0")).toHaveLength(3);
  });

  it("zero-fills buckets missing from the JSON object (string keys)", () => {
    // The backend serializes object keys as strings; a bucket may be absent.
    render(
      <RatingSummaryCard
        summary={{ average: 4.8, total: 2, distribution: { "5": 2 } }}
      />,
    );

    expect(screen.getByText("4.8")).toBeInTheDocument();
    expect(screen.getByText("2 reviews")).toBeInTheDocument();
    // Stars 4→1 are absent from the payload and must read as zero.
    expect(screen.getAllByText("0")).toHaveLength(4);
    expect(screen.getAllByText("2")).toHaveLength(2); // "2★" label + count for 5★
  });
});
