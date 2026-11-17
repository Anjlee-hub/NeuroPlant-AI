import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  Product,
  ProductDetail,
  ProductStats,
  SellerProfile,
} from "@/types/marketplace";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  getMyShop: vi.fn(),
  updateShop: vi.fn(),
  myProducts: vi.fn(),
  getProductStats: vi.fn(),
  createProduct: vi.fn(),
  updateProduct: vi.fn(),
  deleteProduct: vi.fn(),
  browseProducts: vi.fn(),
  getProduct: vi.fn(),
  listConversations: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

import { ProductMarketBrowsePage } from "@/pages/product-market-browse";
import { ProductMarketDetailPage } from "@/pages/product-market-detail";
import { SellerDashboardPage } from "@/pages/seller-dashboard";

/** One product with sensible defaults; tests override the fields they care about. */
function makeProduct(overrides: Partial<Product> = {}): Product {
  return {
    id: 1,
    seller_id: 1,
    name: "Neem oil spray",
    category: "pesticide",
    brand: "BioAgri",
    description: "Cold-pressed neem oil for pest control.",
    price: 250,
    unit: "l",
    stock_quantity: 40,
    images: ["/media/marketplace/neem.png"],
    organic: true,
    manufacturer: "BioAgri Labs",
    usage_instructions: "Mix 2 ml per litre of water.",
    availability: "in_stock",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

const neem = makeProduct();
const urea = makeProduct({
  id: 2,
  name: "Urea 46%",
  category: "fertilizer",
  brand: "CropCare",
  price: 320,
  organic: false,
  availability: "out_of_stock",
});

const stats: ProductStats = { total: 9, active: 5, out_of_stock: 3, archived: 1 };

const shop: SellerProfile = {
  user_id: 1,
  owner_name: "Ravi",
  shop_name: "Green Agri Supplies",
  address: "Main Bazaar, Ludhiana",
  phone: "+91 12345 67890",
  delivery_available: true,
  rating: 4.5,
  verified: true,
  created_at: new Date().toISOString(),
  description: "Farm inputs since 2010.",
  opening_hours: "Mon–Sat 9:00–19:00",
  logo_url: null,
  banner_url: null,
  products: [neem, urea],
};

function renderPage(route: string) {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/marketplace/shop", element: <SellerDashboardPage /> },
      { path: "/marketplace/products", element: <ProductMarketBrowsePage /> },
      { path: "/marketplace/products/:id", element: <ProductMarketDetailPage /> },
    ],
    { initialEntries: [route] },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("SellerDashboardPage (/marketplace/shop)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getMyShop.mockResolvedValue(shop);
    apiMock.myProducts.mockResolvedValue([neem, urea]);
    apiMock.getProductStats.mockResolvedValue(stats);
    apiMock.updateProduct.mockResolvedValue(neem);
    apiMock.deleteProduct.mockResolvedValue(undefined);
    apiMock.updateShop.mockResolvedValue(shop);
    apiMock.listConversations.mockResolvedValue([]);
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage("/marketplace/shop");
    expect(
      await screen.findByText("Sign in to manage your shop."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/login",
    );
  });

  it("renders the shop profile, stats, and every product card", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    renderPage("/marketplace/shop");

    // Shop profile form is initialized from the seller's profile.
    expect(await screen.findByLabelText("Shop name")).toHaveValue("Green Agri Supplies");

    // Stats counts come through (values chosen to not collide with prices).
    expect(screen.getByText("9")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();

    // Both products render with their details.
    expect(screen.getByText("Neem oil spray")).toBeInTheDocument();
    expect(screen.getByText("Urea 46%")).toBeInTheDocument();
    expect(screen.getByText("250")).toBeInTheDocument();
    expect(screen.getByText("320")).toBeInTheDocument();
  });

  it("shows an empty state with an add CTA when there are no products", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    apiMock.myProducts.mockResolvedValue([]);
    apiMock.getProductStats.mockResolvedValue({ total: 0, active: 0, out_of_stock: 0, archived: 0 });
    renderPage("/marketplace/shop");

    expect(
      await screen.findByText("No products yet. Add your first product to start selling."),
    ).toBeInTheDocument();
    // The CTA appears once in the header and once in the empty-state card.
    expect(screen.getAllByRole("button", { name: "Add product" }).length).toBeGreaterThan(0);
  });

  it("narrows the list with the search box", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    renderPage("/marketplace/shop");
    await screen.findByText("Neem oil spray");

    await userEvent.type(
      screen.getByRole("searchbox", { name: "Search your products…" }),
      "urea",
    );

    expect(screen.getByText("Urea 46%")).toBeInTheDocument();
    expect(screen.queryByText("Neem oil spray")).not.toBeInTheDocument();
  });

  it("marks an in-stock product as out of stock via PATCH", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    renderPage("/marketplace/shop");
    const card = (await screen.findByText("Neem oil spray")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Mark out of stock" }));

    await waitFor(() =>
      expect(apiMock.updateProduct).toHaveBeenCalledWith(neem.id, {
        availability: "out_of_stock",
      }),
    );
  });

  it("archives a product after confirming", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage("/marketplace/shop");
    const card = (await screen.findByText("Neem oil spray")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Archive" }));

    await waitFor(() =>
      expect(apiMock.updateProduct).toHaveBeenCalledWith(neem.id, {
        availability: "archived",
      }),
    );
    expect(confirmSpy).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("does not archive when the confirm is cancelled", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderPage("/marketplace/shop");
    const card = (await screen.findByText("Neem oil spray")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Archive" }));

    expect(apiMock.updateProduct).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("deletes a product after confirming", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage("/marketplace/shop");
    const card = (await screen.findByText("Neem oil spray")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(apiMock.deleteProduct).toHaveBeenCalledWith(neem.id));
    confirmSpy.mockRestore();
  });

  it("does not delete when the confirm is cancelled", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderPage("/marketplace/shop");
    const card = (await screen.findByText("Neem oil spray")).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Delete" }));

    expect(apiMock.deleteProduct).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("shows an error state with retry when the shop fails to load", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    apiMock.getMyShop.mockRejectedValue(new Error("boom"));
    renderPage("/marketplace/shop");

    expect(await screen.findByText("Couldn't load your shop")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

describe("ProductMarketBrowsePage (/marketplace/products)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.browseProducts.mockResolvedValue({
      items: [neem, urea],
      total: 2,
      page: 1,
      page_size: 12,
      pages: 1,
    });
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage("/marketplace/products");
    expect(
      await screen.findByText("Sign in to browse agricultural products."),
    ).toBeInTheDocument();
  });

  it("renders every product in the browse grid", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    renderPage("/marketplace/products");

    expect(await screen.findByText("Neem oil spray")).toBeInTheDocument();
    expect(screen.getByText("Urea 46%")).toBeInTheDocument();
    expect(screen.getByText("2 products")).toBeInTheDocument();
  });

  it("passes search terms to the server-side browse query", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    renderPage("/marketplace/products");
    await screen.findByText("Neem oil spray");

    await userEvent.type(
      screen.getByRole("searchbox", { name: "Search products…" }),
      "urea",
    );

    await waitFor(() =>
      expect(apiMock.browseProducts).toHaveBeenCalledWith(
        expect.objectContaining({ q: "urea", page: 1, page_size: 12 }),
      ),
    );
  });

  it("shows a no-results state when the market is empty", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    apiMock.browseProducts.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      pages: 1,
    });
    renderPage("/marketplace/products");

    expect(
      await screen.findByText("No products match your filters. Try widening them."),
    ).toBeInTheDocument();
  });
});

describe("ProductMarketDetailPage (/marketplace/products/:id)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getProduct.mockResolvedValue({
      ...neem,
      shop: {
        user_id: 1,
        shop_name: "Green Agri Supplies",
        verified: true,
        rating: 4.5,
        delivery_available: true,
      },
    } satisfies ProductDetail);
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage("/marketplace/products/1");
    expect(
      await screen.findByText("Sign in to browse agricultural products."),
    ).toBeInTheDocument();
  });

  it("renders the product fields and its seller shop", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    renderPage("/marketplace/products/1");

    expect(await screen.findByText("Neem oil spray")).toBeInTheDocument();
    // The shop name appears in the detail row and the seller block card.
    expect(screen.getAllByText("Green Agri Supplies").length).toBeGreaterThan(0);
    // Every seller-entered field is shown.
    expect(screen.getByText("Cold-pressed neem oil for pest control.")).toBeInTheDocument();
    expect(screen.getByText("BioAgri Labs")).toBeInTheDocument();
    expect(screen.getByText("Mix 2 ml per litre of water.")).toBeInTheDocument();
    // Back navigation.
    expect(
      screen.getByRole("link", { name: "Back to products" }),
    ).toHaveAttribute("href", "/marketplace/products");
  });

  it("shows an error state for an invalid id", async () => {
    authMock.user = { id: 1, name: "Ravi" };
    renderPage("/marketplace/products/not-a-number");

    expect(await screen.findByText("Couldn't load products")).toBeInTheDocument();
  });
});
