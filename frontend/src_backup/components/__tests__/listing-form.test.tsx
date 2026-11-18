import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CropListing } from "@/types/marketplace";

const apiMock = vi.hoisted(() => ({
  createCropListing: vi.fn(),
  updateCropListing: vi.fn(),
  uploadListingImages: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMock }));

import { ListingForm } from "@/components/marketplace/listing-form";

const listing: CropListing = {
  id: 7,
  farmer_id: 1,
  crop_name: "Tomato",
  category: "vegetable",
  variety: "Desi",
  quantity: 50,
  unit: "kg",
  price: 40,
  description: "Farm fresh",
  images: ["/media/marketplace/tomato.png"],
  harvest_date: null,
  organic: true,
  location: "Nashik",
  availability: "available",
  created_at: "2026-08-01T10:00:00Z",
  updated_at: "2026-08-01T10:00:00Z",
};

const saved = { ...listing };

describe("ListingForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.createCropListing.mockResolvedValue(saved);
    apiMock.updateCropListing.mockResolvedValue(saved);
  });

  it("creates a listing with every entered field", async () => {
    const onSaved = vi.fn();
    render(<ListingForm onSaved={onSaved} onCancel={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Crop name"), "Tomato");
    await userEvent.type(screen.getByLabelText("Quantity"), "50");
    await userEvent.type(screen.getByLabelText("Price per unit"), "40");
    await userEvent.type(screen.getByLabelText("Location (optional)"), "Nashik");

    await userEvent.click(screen.getByRole("button", { name: "Save listing" }));

    await waitFor(() =>
      expect(apiMock.createCropListing).toHaveBeenCalledWith({
        crop_name: "Tomato",
        category: "vegetable",
        variety: null,
        quantity: 50,
        unit: "kg",
        price: 40,
        description: null,
        location: "Nashik",
        organic: false,
        harvest_date: null,
        availability: "available",
        images: null,
      }),
    );
    expect(onSaved).toHaveBeenCalledWith(saved);
  });

  it("seeds every field from the listing in edit mode and PATCHes on submit", async () => {
    const onSaved = vi.fn();
    render(<ListingForm listing={listing} onSaved={onSaved} onCancel={vi.fn()} />);

    // Seeded values are visible in the form.
    expect(screen.getByLabelText("Crop name")).toHaveValue("Tomato");
    expect(screen.getByLabelText("Variety (optional)")).toHaveValue("Desi");
    expect(screen.getByLabelText("Quantity")).toHaveValue(50);
    expect(screen.getByLabelText("Price per unit")).toHaveValue(40);
    expect(screen.getByLabelText("Location (optional)")).toHaveValue("Nashik");
    expect(screen.getByLabelText("Organic produce")).toBeChecked();

    await userEvent.click(screen.getByRole("button", { name: "Save listing" }));

    await waitFor(() =>
      expect(apiMock.updateCropListing).toHaveBeenCalledWith(7, {
        crop_name: "Tomato",
        category: "vegetable",
        variety: "Desi",
        quantity: 50,
        unit: "kg",
        price: 40,
        description: "Farm fresh",
        location: "Nashik",
        organic: true,
        harvest_date: null,
        availability: "available",
        images: ["/media/marketplace/tomato.png"],
      }),
    );
    expect(onSaved).toHaveBeenCalledWith(saved);
  });

  it("blocks submit when the required fields are empty", async () => {
    render(<ListingForm onSaved={vi.fn()} onCancel={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: "Save listing" }));

    expect(screen.getByText("Please fill in the required fields.")).toBeInTheDocument();
    expect(apiMock.createCropListing).not.toHaveBeenCalled();
  });

  it("reports a server error instead of navigating away", async () => {
    apiMock.createCropListing.mockRejectedValue(new Error("boom"));
    const onSaved = vi.fn();
    render(<ListingForm onSaved={onSaved} onCancel={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Crop name"), "Tomato");
    await userEvent.type(screen.getByLabelText("Quantity"), "10");
    await userEvent.type(screen.getByLabelText("Price per unit"), "25");
    await userEvent.click(screen.getByRole("button", { name: "Save listing" }));

    expect(
      await screen.findByText("Couldn't save the listing. Please try again."),
    ).toBeInTheDocument();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("fires cancel without saving", async () => {
    const onCancel = vi.fn();
    render(<ListingForm onSaved={vi.fn()} onCancel={onCancel} />);
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalled();
    expect(apiMock.createCropListing).not.toHaveBeenCalled();
  });
});
