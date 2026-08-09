import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CropListing, Product } from "@/types/marketplace";
import type { Favourite } from "@/types/trust";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  listFavourites: vi.fn(),
  removeFavourite: vi.fn(),
  errorMessage: (err: Error) => err.message,
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock, errorMessage: apiMock.errorMessage }));

import { MarketplaceFavoritesPage } from "@/pages/marketplace-favorites";

const listing: CropListing = {
  id: 3,
  farmer_id: 5,
  crop_name: "Tomato",
  category: "vegetable",
  variety: "Desi",
  quantity: 50,
  unit: "kg",
  price: 40,
  description: "Farm fresh.",
  images: ["/media/marketplace/tomato.png"],
  harvest_date: "2026-07-15",
  organic: true,
  location: "Nashik",
  availability: "available",
  created_at: "2026-07-01T09:00:00Z",
  updated_at: "2026-07-01T09:00:00Z",
};

const product: Product = {
  id: 9,
  seller_id: 8,
  name: "Urea 46%",
  category: "fertilizer",
  brand: "AgroCo",
  description: "Nitrogen fertiliser.",
  price: 350,
  unit: "kg",
  stock_quantity: 100,
  images: ["/media/marketplace/urea.png"],
  organic: false,
  manufacturer: "AgroCo",
  usage_instructions: null,
  availability: "in_stock",
  created_at: "2026-07-05T09:00:00Z",
  updated_at: "2026-07-05T09:00:00Z",
};

function favourite(overrides: Partial<Favourite>): Favourite {
  return { id: 1, created_at: "2026-07-06T10:00:00Z", listing, product: null, ...overrides };
}

function renderPage() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/marketplace/browse", element: <div>browse</div> },
      { path: "/marketplace/listings/:id", element: <div>listing detail</div> },
      { path: "/marketplace/products/:id", element: <div>product detail</div> },
      { path: "/marketplace/favorites", element: <MarketplaceFavoritesPage /> },
    ],
    { initialEntries: ["/marketplace/favorites"] },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("MarketplaceFavoritesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authMock.user = { id: 1, name: "Tester" };
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage();

    expect(
      await screen.findByText("Sign in to view your saved items"),
    ).toBeInTheDocument();
  });

  it("shows an empty state with a browse shortcut when nothing is saved", async () => {
    apiMock.listFavourites.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByText("No saved items yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Browse the marketplace" })).toHaveAttribute(
      "href",
      "/marketplace/browse",
    );
  });

  it("renders saved crop listings and products with the browse cards", async () => {
    apiMock.listFavourites.mockResolvedValue([
      favourite({ id: 1 }),
      favourite({ id: 2, listing: null, product }),
    ]);
    renderPage();

    expect(await screen.findByRole("heading", { name: "Tomato" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Urea 46%" })).toBeInTheDocument();
    // Each card links back to its own detail page.
    const detailLinks = screen.getAllByRole("link", { name: /View details/ });
    expect(detailLinks.map((link) => link.getAttribute("href"))).toEqual([
      "/marketplace/listings/3",
      "/marketplace/products/9",
    ]);
  });

  it("removes a saved item via the DELETE endpoint", async () => {
    apiMock.listFavourites.mockResolvedValue([
      favourite({ id: 1 }),
      favourite({ id: 2, listing: null, product }),
    ]);
    apiMock.removeFavourite.mockResolvedValue(undefined);
    renderPage();

    const removeButtons = await screen.findAllByRole("button", {
      name: "Remove from saved items",
    });
    await userEvent.click(removeButtons[0]);

    await vi.waitFor(() => expect(apiMock.removeFavourite).toHaveBeenCalledWith(1));
  });

  it("shows an error state with retry when loading fails", async () => {
    apiMock.listFavourites.mockRejectedValue(new Error("boom"));
    renderPage();

    expect(await screen.findByText("Couldn't load your saved items")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("scopes each remove button to its own favourite row", async () => {
    apiMock.listFavourites.mockResolvedValue([
      favourite({ id: 10, listing: null, product }),
      favourite({ id: 11, listing }),
    ]);
    renderPage();

    const listItems = await screen.findAllByRole("listitem");
    // Favourites render in array order, so the first card is the product one
    // and its remove button deletes that row (id 10), not the other.
    await userEvent.click(
      within(listItems[0]).getByRole("button", { name: "Remove from saved items" }),
    );

    await vi.waitFor(() => expect(apiMock.removeFavourite).toHaveBeenCalledWith(10));
  });
});
