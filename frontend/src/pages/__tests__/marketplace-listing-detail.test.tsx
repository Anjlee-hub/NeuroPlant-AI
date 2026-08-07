import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CropListingDetail } from "@/types/marketplace";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  getCropListing: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

import { MarketplaceListingDetailPage } from "@/pages/marketplace-listing-detail";

const FAVOURITES_KEY = "neuroplant.favourites";

/** One listing detail with sensible defaults; tests override fields. */
function makeDetail(overrides: Partial<CropListingDetail> = {}): CropListingDetail {
  return {
    id: 1,
    farmer_id: 1,
    crop_name: "Tomato",
    category: "vegetable",
    variety: "Desi",
    quantity: 50,
    unit: "kg",
    price: 40,
    description: "Farm fresh tomatoes from Nashik.",
    images: ["/media/marketplace/tomato.png", "/media/marketplace/tomato-2.png"],
    harvest_date: "2026-07-15",
    organic: true,
    location: "Nashik",
    availability: "available",
    created_at: "2026-07-01T09:00:00Z",
    updated_at: "2026-07-01T09:00:00Z",
    farmer: { id: 5, name: "Kisan Kumar", verified: true },
    ...overrides,
  };
}

function renderPage(id = 1) {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/marketplace/browse", element: <div>browse</div> },
      {
        path: "/marketplace/listings/:listingId",
        element: <MarketplaceListingDetailPage />,
      },
    ],
    { initialEntries: [`/marketplace/listings/${id}`] },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("MarketplaceListingDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    authMock.user = { id: 1, name: "Tester" };
    apiMock.getCropListing.mockResolvedValue(makeDetail());
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage();
    expect(
      await screen.findByText("Sign in to browse the marketplace."),
    ).toBeInTheDocument();
  });

  it("renders every field the buyer cares about", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Tomato" })).toBeInTheDocument();
    expect(screen.getByText("Desi")).toBeInTheDocument();
    expect(screen.getByText("50 kg")).toBeInTheDocument();
    expect(screen.getByText("Farm fresh tomatoes from Nashik.")).toBeInTheDocument();
    expect(screen.getByText("Nashik")).toBeInTheDocument();
    expect(screen.getByText("Kisan Kumar")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    // Labels for the metadata rows are shown.
    expect(screen.getByText("Harvest date")).toBeInTheDocument();
    expect(screen.getByText("Listed on")).toBeInTheDocument();
    expect(screen.getByText("Description")).toBeInTheDocument();
    expect(screen.getByText("Farmer")).toBeInTheDocument();
  });

  it("shows the main gallery image and steps through photos", async () => {
    renderPage();

    const main = await screen.findByRole("img", { name: "Photo of Tomato" });
    expect(main).toHaveAttribute("src", "/media/marketplace/tomato.png");

    await userEvent.click(screen.getByRole("button", { name: "Next photo" }));
    expect(main).toHaveAttribute("src", "/media/marketplace/tomato-2.png");

    // A thumbnail jumps straight to a photo.
    await userEvent.click(screen.getByRole("button", { name: "Thumbnail 1 of Tomato" }));
    expect(main).toHaveAttribute("src", "/media/marketplace/tomato.png");
  });

  it("opens the lightbox and closes it on Escape", async () => {
    renderPage();
    await screen.findByRole("img", { name: "Photo of Tomato" });

    await userEvent.click(screen.getByRole("button", { name: "Open photo" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("img", { name: "Photo of Tomato" })).toBeInTheDocument();

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows an honest placeholder when the listing has no photos", async () => {
    apiMock.getCropListing.mockResolvedValue(makeDetail({ images: null }));
    renderPage();

    expect(
      await screen.findByRole("img", { name: "No photos for this listing." }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open photo" })).not.toBeInTheDocument();
  });

  it("toggles the listing in and out of favourites", async () => {
    renderPage();
    const button = await screen.findByRole("button", { name: "Save to favourites" });

    await userEvent.click(button);
    expect(screen.getByRole("button", { name: "Remove from favourites" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(JSON.parse(localStorage.getItem(FAVOURITES_KEY) ?? "[]")).toEqual([1]);

    await userEvent.click(screen.getByRole("button", { name: "Remove from favourites" }));
    expect(screen.getByRole("button", { name: "Save to favourites" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(JSON.parse(localStorage.getItem(FAVOURITES_KEY) ?? "[]")).toEqual([]);
  });

  it("copies the listing link to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    renderPage();
    const href = window.location.href;

    await userEvent.click(await screen.findByRole("button", { name: "Copy link" }));

    await vi.waitFor(() => expect(writeText).toHaveBeenCalledWith(href));
    expect(screen.getByRole("button", { name: "Link copied" })).toBeInTheDocument();
  });

  it("reveals a messaging coming-soon note via the contact button", async () => {
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Contact farmer" }));

    expect(screen.getByText("Messaging is coming soon.")).toBeInTheDocument();
  });

  it("shows an error state with retry when the listing fails to load", async () => {
    apiMock.getCropListing.mockRejectedValue(new Error("boom"));
    renderPage();

    expect(await screen.findByText("Couldn't load listings")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
