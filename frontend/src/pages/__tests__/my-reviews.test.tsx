import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Review } from "@/types/trust";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  listMyReviews: vi.fn(),
  updateReview: vi.fn(),
  deleteReview: vi.fn(),
  errorMessage: (err: Error) => err.message,
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock, errorMessage: apiMock.errorMessage }));

import { MyReviewsPage } from "@/pages/my-reviews";

function makeReview(overrides: Partial<Review> = {}): Review {
  return {
    id: 11,
    reviewer_id: 1,
    reviewer_name: "Tester",
    seller_id: 5,
    rating: 5,
    title: "Great tomatoes",
    content: "Really fresh and tasty.",
    created_at: "2026-07-20T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    listing: { id: 3, crop_name: "Tomato", image: null },
    product: null,
    ...overrides,
  };
}

function renderPage() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/marketplace/browse", element: <div>browse</div> },
      { path: "/marketplace/listings/:id", element: <div>listing detail</div> },
      { path: "/marketplace/products/:id", element: <div>product detail</div> },
      { path: "/marketplace/my-reviews", element: <MyReviewsPage /> },
    ],
    { initialEntries: ["/marketplace/my-reviews"] },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("MyReviewsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authMock.user = { id: 1, name: "Tester" };
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage();

    expect(await screen.findByText("Sign in to view your reviews")).toBeInTheDocument();
  });

  it("shows an empty state with a browse shortcut when there are no reviews", async () => {
    apiMock.listMyReviews.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByText("You haven't written any reviews yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Browse the marketplace" })).toHaveAttribute(
      "href",
      "/marketplace/browse",
    );
  });

  it("lists every review with a link back to the item it rates", async () => {
    apiMock.listMyReviews.mockResolvedValue([
      makeReview({ id: 11, listing: { id: 3, crop_name: "Tomato", image: null } }),
      makeReview({
        id: 12,
        listing: null,
        product: { id: 9, name: "Urea 46%", image: null },
        content: "Works well on my field.",
      }),
    ]);
    renderPage();

    expect(await screen.findByText("Really fresh and tasty.")).toBeInTheDocument();
    expect(screen.getByText("Works well on my field.")).toBeInTheDocument();

    const tomatoLink = screen.getByRole("link", { name: /Tomato/ });
    expect(tomatoLink).toHaveAttribute("href", "/marketplace/listings/3");

    const ureaLink = screen.getByRole("link", { name: /Urea 46%/ });
    expect(ureaLink).toHaveAttribute("href", "/marketplace/products/9");
  });

  it("shows a deleted-item marker when the rated item is gone", async () => {
    apiMock.listMyReviews.mockResolvedValue([
      makeReview({ listing: null, product: null }),
    ]);
    renderPage();

    expect(
      await screen.findByText("This item is no longer available"),
    ).toBeInTheDocument();
  });

  it("deletes a review via the DELETE endpoint", async () => {
    apiMock.listMyReviews.mockResolvedValue([makeReview()]);
    apiMock.deleteReview.mockResolvedValue(undefined);
    renderPage();

    await userEvent.click(
      await screen.findByRole("button", { name: "Delete" }),
    );

    await vi.waitFor(() => expect(apiMock.deleteReview).toHaveBeenCalledWith(11));
  });

  it("edits a review inline and submits the changed fields", async () => {
    apiMock.listMyReviews.mockResolvedValue([makeReview()]);
    apiMock.updateReview.mockResolvedValue(makeReview());
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));

    // Editing swaps the review card for the pre-filled form (no article remains).
    const content = screen.getByLabelText("Your review");
    await userEvent.clear(content);
    await userEvent.type(content, "Better than expected.");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await vi.waitFor(() => {
      expect(apiMock.updateReview).toHaveBeenCalledWith(11, {
        rating: 5,
        title: "Great tomatoes",
        content: "Better than expected.",
      });
    });
  });
});
