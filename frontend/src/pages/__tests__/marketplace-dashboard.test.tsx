import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, Navigate, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Header } from "@/components/layout/header";
import { ThemeProvider } from "@/app/theme-provider";
import type { CropListing, CropListingStats } from "@/types/marketplace";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  myCropListings: vi.fn(),
  getCropListingStats: vi.fn(),
  updateCropListing: vi.fn(),
  deleteCropListing: vi.fn(),
  listConversations: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: (selector?: (state: {
    user: typeof authMock.user;
    loading: boolean;
    logout: () => void;
  }) => unknown) => {
    const state = { user: authMock.user, loading: false, logout: vi.fn() };
    return selector ? selector(state) : state;
  },
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

import {
  MarketplaceDashboardPage,
  MarketplaceHubPage,
} from "@/pages/marketplace-dashboard";

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
    harvest_date: null,
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

const stats: CropListingStats = { total: 9, active: 5, sold: 3, archived: 1 };

function renderPage() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/marketplace", element: <MarketplaceDashboardPage /> },
    ],
    { initialEntries: ["/marketplace"] },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("MarketplaceHubPage", () => {
  it("keeps Marketplace as the only marketplace item in the main sidebar", () => {
    const router = createMemoryRouter(
      [
        {
          path: "*",
          element: <Header collapsed={false} onToggleSidebar={() => {}} />,
        },
      ],
      { initialEntries: ["/marketplace/browse"] },
    );

    render(
      <ThemeProvider>
        <RouterProvider router={router} />
      </ThemeProvider>,
    );

    const mainNavigation = within(
      screen.getByRole("navigation", { name: "Main navigation" }),
    );
    expect(
      mainNavigation.getAllByRole("link", { name: "Marketplace" }),
    ).toHaveLength(1);
    for (const removedEntry of [
      "Buy",
      "My Shop",
      "Plant Protection & Farm Inputs",
      "Messages",
      "Saved items",
      "My reviews",
    ]) {
      expect(
        mainNavigation.queryByRole("link", { name: removedEntry }),
      ).not.toBeInTheDocument();
    }
  });

  it("defaults to crop browsing and switches between the unified sections", async () => {
    const user = userEvent.setup();
    authMock.user = { id: 1, name: "Tester" };
    const router = createMemoryRouter(
      [
        {
          path: "/marketplace",
          element: <MarketplaceHubPage />,
          children: [
            {
              index: true,
              element: <Navigate to="/marketplace/browse" replace />,
            },
            { path: "browse", element: <div>Browse Crops section</div> },
            { path: "listings", element: <div>My Listings section</div> },
            { path: "shop", element: <div>My Shop section</div> },
            { path: "products", element: <div>Plant Protection & Farm Inputs section</div> },
            { path: "messages", element: <div>Messages section</div> },
          ],
        },
      ],
      { initialEntries: ["/marketplace"] },
    );

    apiMock.listConversations.mockResolvedValue([{ unread_count: 3 }]);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Browse Crops section")).toBeInTheDocument();
    const sections = within(
      screen.getByRole("navigation", { name: "Marketplace sections" }),
    );
    const links = sections.getAllByRole("link");
    expect(links).toHaveLength(6);
    expect(links.map((link) => link.textContent?.trim())).toEqual([
      "My Shop",
      "Browse Crops",
      "Plant Protection & Farm Inputs",
      expect.stringContaining("Messages"),
      "Saved items",
      "My reviews",
    ]);
    expect(await screen.findByLabelText("3 unread messages")).toBeInTheDocument();
    expect(sections.getByRole("link", { name: /Messages/ })).toHaveAttribute(
      "href",
      "/marketplace/messages",
    );
    expect(sections.getByRole("link", { name: "Saved items" })).toHaveAttribute(
      "href",
      "/marketplace/favorites",
    );

    const shopLink = sections.getByRole("link", { name: "My Shop" });
    await user.click(shopLink);
    expect(await screen.findByText("My Shop section")).toBeInTheDocument();
    expect(shopLink).toHaveAttribute("aria-current", "page");
  });
});

describe("MarketplaceDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.myCropListings.mockResolvedValue([tomato, onion]);
    apiMock.getCropListingStats.mockResolvedValue(stats);
    apiMock.updateCropListing.mockResolvedValue(tomato);
    apiMock.deleteCropListing.mockResolvedValue(undefined);
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage();
    expect(
      await screen.findByText("Sign in to manage your crop listings."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });

  it("renders the stats counts and every listing card", async () => {
    authMock.user = { id: 1, name: "Tester" };
    renderPage();

    // Stats counts come through (values are chosen to not collide with prices/quantities).
    expect(await screen.findByText("Tomato")).toBeInTheDocument();
    expect(screen.getByText("9")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();

    // Both listings render with their details.
    expect(screen.getByText("Onion")).toBeInTheDocument();
    expect(screen.getByText("40")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("Nashik")).toBeInTheDocument();
  });

  it("shows a fallback if a listing image cannot be loaded", async () => {
    authMock.user = { id: 1, name: "Tester" };
    renderPage();

    const image = await screen.findByRole("img", { name: "Tomato" });
    fireEvent.error(image);

    expect(screen.getByRole("img", { name: "Tomato" }).tagName).toBe("DIV");
  });

  it("shows an empty state with a create CTA when there are no listings", async () => {
    authMock.user = { id: 1, name: "Tester" };
    apiMock.myCropListings.mockResolvedValue([]);
    apiMock.getCropListingStats.mockResolvedValue({ total: 0, active: 0, sold: 0, archived: 0 });
    renderPage();

    expect(
      await screen.findByText("No listings yet. Create your first listing to start selling."),
    ).toBeInTheDocument();
    // The CTA appears once in the header and once in the empty-state card.
    expect(screen.getAllByRole("button", { name: "New listing" }).length).toBeGreaterThan(0);
  });

  it("narrows the list with the search box", async () => {
    authMock.user = { id: 1, name: "Tester" };
    renderPage();
    await screen.findByText("Tomato");

    await userEvent.type(
      screen.getByRole("searchbox", { name: "Search your listings…" }),
      "onion",
    );

    expect(screen.getByText("Onion")).toBeInTheDocument();
    expect(screen.queryByText("Tomato")).not.toBeInTheDocument();
  });

  it("filters by status", async () => {
    authMock.user = { id: 1, name: "Tester" };
    apiMock.myCropListings.mockResolvedValue([
      makeListing({ id: 1, crop_name: "Tomato" }),
      makeListing({ id: 2, crop_name: "Potato", availability: "sold_out", variety: null }),
    ]);
    renderPage();
    await screen.findByText("Tomato");

    await userEvent.selectOptions(
      screen.getByLabelText("Status"),
      screen.getByRole("option", { name: "Sold out" }),
    );

    expect(screen.getByText("Potato")).toBeInTheDocument();
    expect(screen.queryByText("Tomato")).not.toBeInTheDocument();
  });

  it("marks an available listing as sold via PATCH", async () => {
    authMock.user = { id: 1, name: "Tester" };
    renderPage();
    const card = (await screen.findByText("Tomato")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Mark as sold" }));

    await waitFor(() =>
      expect(apiMock.updateCropListing).toHaveBeenCalledWith(tomato.id, {
        availability: "sold_out",
      }),
    );
  });

  it("marks a sold-out listing as available", async () => {
    authMock.user = { id: 1, name: "Tester" };
    apiMock.myCropListings.mockResolvedValue([
      makeListing({ id: 1, crop_name: "Tomato", availability: "sold_out" }),
    ]);
    renderPage();
    const card = (await screen.findByText("Tomato")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Mark as available" }));

    await waitFor(() =>
      expect(apiMock.updateCropListing).toHaveBeenCalledWith(tomato.id, {
        availability: "available",
      }),
    );
  });

  it("archives a listing after confirming", async () => {
    authMock.user = { id: 1, name: "Tester" };
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage();
    const card = (await screen.findByText("Tomato")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Archive" }));

    await waitFor(() =>
      expect(apiMock.updateCropListing).toHaveBeenCalledWith(tomato.id, {
        availability: "archived",
      }),
    );
    expect(confirmSpy).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("does not archive when the confirm is cancelled", async () => {
    authMock.user = { id: 1, name: "Tester" };
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderPage();
    const card = (await screen.findByText("Tomato")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Archive" }));

    expect(apiMock.updateCropListing).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("deletes a listing after confirming", async () => {
    authMock.user = { id: 1, name: "Tester" };
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage();
    const card = (await screen.findByText("Tomato")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(apiMock.deleteCropListing).toHaveBeenCalledWith(tomato.id));
    confirmSpy.mockRestore();
  });

  it("does not delete when the confirm is cancelled", async () => {
    authMock.user = { id: 1, name: "Tester" };
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderPage();
    const card = (await screen.findByText("Tomato")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Delete" }));

    expect(apiMock.deleteCropListing).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("shows an error state with retry when listings fail to load", async () => {
    authMock.user = { id: 1, name: "Tester" };
    apiMock.myCropListings.mockRejectedValue(new Error("boom"));
    renderPage();

    expect(await screen.findByText("Couldn't load your listings")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
