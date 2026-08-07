import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CropListing, CropListingPage } from "@/types/marketplace";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  browseCrops: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

import { MarketplaceBuyPage } from "@/pages/marketplace-buy";

/** One listing with sensible defaults; tests override the fields they care about. */
function makeListing(overrides: Partial<CropListing> = {}): CropListing {
  return {
    id: 1,
    farmer_id: 1,
    crop_name: "Tomato",
    category: "vegetable",
    variety: "Desi",
    quantity: 50,
    unit: "kg",
    price: 40,
    description: "Farm fresh",
    images: ["/media/marketplace/tomato.png"],
    harvest_date: "2026-07-15",
    organic: true,
    location: "Nashik",
    availability: "available",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

const tomato = makeListing();
const onion = makeListing({
  id: 2,
  crop_name: "Onion",
  category: "vegetable",
  variety: null,
  price: 30,
  quantity: 20,
  organic: false,
  location: null,
});

function page(
  items: CropListing[],
  total: number,
  pageNum = 1,
  pages = 1,
): CropListingPage {
  return { items, total, page: pageNum, page_size: 10, pages };
}

function renderPage() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/marketplace/browse", element: <MarketplaceBuyPage /> },
      { path: "/marketplace/listings/:listingId", element: <div>detail</div> },
    ],
    { initialEntries: ["/marketplace/browse"] },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("MarketplaceBuyPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authMock.user = { id: 1, name: "Tester" };
    apiMock.browseCrops.mockResolvedValue(page([tomato, onion], 2));
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage();
    expect(
      await screen.findByText("Sign in to browse the marketplace."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });

  it("renders the result count and every listing card", async () => {
    renderPage();

    expect(await screen.findByText("2 listings")).toBeInTheDocument();
    expect(screen.getByText("Tomato")).toBeInTheDocument();
    expect(screen.getByText("Onion")).toBeInTheDocument();
    // Prices, quantities and the farmer's location are visible on the cards.
    expect(screen.getByText("40")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("Nashik")).toBeInTheDocument();
    // Cards link to their detail pages.
    const detailLinks = screen.getAllByRole("link", { name: "View details" });
    expect(detailLinks).toHaveLength(2);
    expect(detailLinks[0]).toHaveAttribute("href", "/marketplace/listings/1");
    expect(detailLinks[1]).toHaveAttribute("href", "/marketplace/listings/2");
  });

  it("searches server-side as the user types", async () => {
    renderPage();
    await screen.findByText("Tomato");

    await userEvent.type(
      screen.getByRole("searchbox", { name: "Search crops…" }),
      "onion",
    );

    expect(apiMock.browseCrops).toHaveBeenLastCalledWith(
      expect.objectContaining({ q: "onion", page: 1 }),
    );
  });

  it("filters by category via the select", async () => {
    renderPage();
    await screen.findByText("Tomato");

    await userEvent.selectOptions(screen.getByLabelText("Category"), "fruit");

    expect(apiMock.browseCrops).toHaveBeenLastCalledWith(
      expect.objectContaining({ category: "fruit", page: 1 }),
    );
  });

  it("sorts by price ascending", async () => {
    renderPage();
    await screen.findByText("Tomato");

    await userEvent.selectOptions(screen.getByLabelText("Sort by"), "price_asc");

    expect(apiMock.browseCrops).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: "price_asc", page: 1 }),
    );
  });

  it("pages forward and back with the server page number", async () => {
    apiMock.browseCrops.mockImplementation((params: { page?: number }) =>
      Promise.resolve(
        page([tomato], 12, params.page ?? 1, 2),
      ),
    );
    renderPage();
    await screen.findByText("12 listings");

    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(apiMock.browseCrops).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2 }),
    );

    await userEvent.click(screen.getByRole("button", { name: "Previous" }));
    expect(apiMock.browseCrops).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 1 }),
    );
  });

  it("shows the empty state when the market has no listings", async () => {
    apiMock.browseCrops.mockResolvedValue(page([], 0, 1, 0));
    renderPage();

    expect(
      await screen.findByText("No listings are on the market right now. Check back soon."),
    ).toBeInTheDocument();
  });

  it("shows a no-results state when filters exclude everything", async () => {
    apiMock.browseCrops.mockResolvedValue(page([], 0, 1, 0));
    renderPage();
    await screen.findByText("No listings are on the market right now. Check back soon.");

    await userEvent.type(
      screen.getByRole("searchbox", { name: "Search crops…" }),
      "zucchini",
    );

    expect(
      await screen.findByText("No listings match your filters. Try widening them."),
    ).toBeInTheDocument();
  });

  it("shows an error state with retry when listings fail to load", async () => {
    apiMock.browseCrops.mockRejectedValue(new Error("boom"));
    renderPage();

    expect(await screen.findByText("Couldn't load listings")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
