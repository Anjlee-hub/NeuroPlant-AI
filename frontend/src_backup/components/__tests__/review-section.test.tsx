import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Review, ReviewPage } from "@/types/trust";

const apiMock = vi.hoisted(() => ({
  listReviews: vi.fn(),
  createReview: vi.fn(),
  updateReview: vi.fn(),
  deleteReview: vi.fn(),
  errorMessage: (err: Error) => err.message,
}));

vi.mock("@/lib/api", () => ({ api: apiMock, errorMessage: apiMock.errorMessage }));

import { ReviewSection } from "@/components/marketplace/review-section";

function makeReview(overrides: Partial<Review> = {}): Review {
  return {
    id: 11,
    reviewer_id: 2,
    reviewer_name: "Anita",
    seller_id: 5,
    rating: 5,
    title: "Very fresh",
    content: "The tomatoes were crisp and sweet.",
    created_at: "2026-07-20T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    listing: { id: 3, crop_name: "Tomato", image: null },
    product: null,
    ...overrides,
  };
}

function makePage(overrides: Partial<ReviewPage> = {}): ReviewPage {
  return {
    items: [makeReview()],
    total: 1,
    page: 1,
    page_size: 5,
    pages: 1,
    summary: {
      average: 5,
      total: 1,
      distribution: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 1 },
    },
    my_review: null,
    ...overrides,
  };
}

function renderSection(listingId?: number, productId?: number) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ReviewSection listingId={listingId} productId={productId} />
    </QueryClientProvider>,
  );
}

describe("ReviewSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.listReviews.mockResolvedValue(makePage());
    apiMock.createReview.mockResolvedValue(makeReview());
    apiMock.updateReview.mockResolvedValue(makeReview());
    apiMock.deleteReview.mockResolvedValue(undefined);
  });

  it("loads reviews and the rating summary for the item", async () => {
    renderSection(1);

    expect(await screen.findByText("Anita")).toBeInTheDocument();
    expect(screen.getByText("Very fresh")).toBeInTheDocument();
    expect(screen.getByText("The tomatoes were crisp and sweet.")).toBeInTheDocument();
    expect(screen.getByText("1 review")).toBeInTheDocument();
    expect(apiMock.listReviews).toHaveBeenCalledWith({
      listing_id: 1,
      product_id: undefined,
      page: 1,
    });
  });

  it("targets a product review with product_id", async () => {
    renderSection(undefined, 9);

    expect(await screen.findByText("Anita")).toBeInTheDocument();
    expect(apiMock.listReviews).toHaveBeenCalledWith({
      listing_id: undefined,
      product_id: 9,
      page: 1,
    });
  });

  it("shows the caller's review in its own card, not duplicated in the list", async () => {
    const mine = makeReview({ id: 11, reviewer_name: "Tester" });
    apiMock.listReviews.mockResolvedValue(
      makePage({ items: [mine], my_review: mine, total: 1, pages: 1 }),
    );
    renderSection(1);

    expect(await screen.findByText("Your review")).toBeInTheDocument();
    // The caller's review renders exactly once (the list below excludes it)…
    expect(screen.getAllByText("Tester")).toHaveLength(1);
    // …and the write button is replaced by the edit/delete actions.
    expect(screen.queryByRole("button", { name: "Write a review" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("posts a new review with the form values", async () => {
    renderSection(1);

    await userEvent.click(await screen.findByRole("button", { name: "Write a review" }));

    await userEvent.type(screen.getByLabelText("Title"), "Worth it");
    await userEvent.type(screen.getByLabelText("Your review"), "Good quality at the price.");
    await userEvent.click(screen.getByRole("button", { name: "Post review" }));

    await vi.waitFor(() => {
      expect(apiMock.createReview).toHaveBeenCalledWith(
        expect.objectContaining({
          listing_id: 1,
          rating: 5,
          title: "Worth it",
          content: "Good quality at the price.",
        }),
      );
    });
  });

  it("blocks an empty review locally without calling the API", async () => {
    renderSection(1);

    await userEvent.click(await screen.findByRole("button", { name: "Write a review" }));
    await userEvent.click(screen.getByRole("button", { name: "Post review" }));

    expect(
      await screen.findByText("Please write a short review before posting."),
    ).toBeInTheDocument();
    expect(apiMock.createReview).not.toHaveBeenCalled();
  });

  it("edits the caller's review inline", async () => {
    const mine = makeReview({ id: 11, reviewer_name: "Tester" });
    apiMock.listReviews.mockResolvedValue(
      makePage({ items: [mine], my_review: mine, total: 1, pages: 1 }),
    );
    renderSection(1);

    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));

    // Editing swaps the "Your review" card for the form (no article remains).
    const content = screen.getByLabelText("Your review");
    await userEvent.clear(content);
    await userEvent.type(content, "Even better than the first batch.");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await vi.waitFor(() => {
      expect(apiMock.updateReview).toHaveBeenCalledWith(
        11,
        expect.objectContaining({
          rating: 5,
          title: "Very fresh",
          content: "Even better than the first batch.",
        }),
      );
    });
  });

  it("deletes the caller's review", async () => {
    const mine = makeReview({ id: 11, reviewer_name: "Tester" });
    apiMock.listReviews.mockResolvedValue(
      makePage({ items: [mine], my_review: mine, total: 1, pages: 1 }),
    );
    renderSection(1);

    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));

    await vi.waitFor(() => expect(apiMock.deleteReview).toHaveBeenCalledWith(11));
  });

  it("pages through the reviews", async () => {
    apiMock.listReviews.mockResolvedValue(makePage({ pages: 3, total: 11 }));
    renderSection(1);

    await userEvent.click(await screen.findByRole("button", { name: "Next" }));

    await vi.waitFor(() => {
      expect(apiMock.listReviews).toHaveBeenCalledWith({
        listing_id: 1,
        product_id: undefined,
        page: 2,
      });
    });
  });
});
