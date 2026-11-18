import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMock = vi.hoisted(() => ({
  favouriteStatus: vi.fn(),
  addFavourite: vi.fn(),
  removeFavourite: vi.fn(),
  errorMessage: (err: Error) => err.message,
}));

vi.mock("@/lib/api", () => ({ api: apiMock, errorMessage: apiMock.errorMessage }));

import { useFavouriteStatus } from "@/lib/favourites";

const UNSAVED = {
  favorited: false,
  favorite_id: null,
  listing_id: 1,
  product_id: null,
};

/** A fresh QueryClient per test so cached status can't leak between tests. */
function wrapperFor() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe("useFavouriteStatus (server-backed, M4 Task 6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.favouriteStatus.mockResolvedValue({ ...UNSAVED });
    apiMock.addFavourite.mockResolvedValue({});
    apiMock.removeFavourite.mockResolvedValue(undefined);
  });

  it("starts not favourited and resolves once the status loads", async () => {
    const { result } = renderHook(() => useFavouriteStatus({ listingId: 1 }), {
      wrapper: wrapperFor(),
    });

    expect(result.current.isFavourited).toBe(false);
    expect(result.current.isStatusLoading).toBe(true);

    await waitFor(() => expect(result.current.isStatusLoading).toBe(false));
    expect(result.current.isFavourited).toBe(false);
    expect(result.current.isStatusError).toBe(false);
  });

  it("reflects a saved item once the status loads", async () => {
    apiMock.favouriteStatus.mockResolvedValue({
      favorited: true,
      favorite_id: 7,
      listing_id: 1,
      product_id: null,
    });
    const { result } = renderHook(() => useFavouriteStatus({ listingId: 1 }), {
      wrapper: wrapperFor(),
    });

    await waitFor(() => expect(result.current.isStatusLoading).toBe(false));
    expect(result.current.isFavourited).toBe(true);
  });

  it("asks the server for the item's own status (listing vs product)", () => {
    renderHook(() => useFavouriteStatus({ productId: 9 }), {
      wrapper: wrapperFor(),
    });

    expect(apiMock.favouriteStatus).toHaveBeenCalledWith({
      listing_id: undefined,
      product_id: 9,
    });
  });

  it("adds the item when toggled from unsaved", async () => {
    const { result } = renderHook(() => useFavouriteStatus({ listingId: 1 }), {
      wrapper: wrapperFor(),
    });
    await waitFor(() => expect(result.current.isStatusLoading).toBe(false));

    act(() => result.current.toggle());

    await waitFor(() => {
      expect(apiMock.addFavourite).toHaveBeenCalledWith({
        listing_id: 1,
        product_id: undefined,
      });
    });
  });

  it("removes the item (by its favourite row id) when toggled from saved", async () => {
    apiMock.favouriteStatus.mockResolvedValue({
      favorited: true,
      favorite_id: 7,
      listing_id: 1,
      product_id: null,
    });
    const { result } = renderHook(() => useFavouriteStatus({ listingId: 1 }), {
      wrapper: wrapperFor(),
    });
    await waitFor(() => expect(result.current.isStatusLoading).toBe(false));

    act(() => result.current.toggle());

    await waitFor(() => expect(apiMock.removeFavourite).toHaveBeenCalledWith(7));
  });

  it("flips the button optimistically before the server confirms", async () => {
    // A pending POST keeps the mutation in flight so we can observe the
    // optimistic state before anything settles.
    apiMock.addFavourite.mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useFavouriteStatus({ listingId: 1 }), {
      wrapper: wrapperFor(),
    });
    await waitFor(() => expect(result.current.isStatusLoading).toBe(false));

    act(() => result.current.toggle());

    await waitFor(() => expect(result.current.isFavourited).toBe(true));
    expect(result.current.isMutating).toBe(true);
  });

  it("reports an error when the status query fails", async () => {
    apiMock.favouriteStatus.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useFavouriteStatus({ listingId: 1 }), {
      wrapper: wrapperFor(),
    });

    await waitFor(() => expect(result.current.isStatusError).toBe(true));
    expect(result.current.isFavourited).toBe(false);
  });

  it("surfaces the toggle failure message", async () => {
    apiMock.addFavourite.mockRejectedValue(new Error("Couldn't save"));
    const { result } = renderHook(() => useFavouriteStatus({ listingId: 1 }), {
      wrapper: wrapperFor(),
    });
    await waitFor(() => expect(result.current.isStatusLoading).toBe(false));

    act(() => result.current.toggle());

    await waitFor(() => expect(result.current.error).toBe("Couldn't save"));
  });

  it("ignores a second toggle while the first is still in flight", async () => {
    apiMock.addFavourite.mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useFavouriteStatus({ listingId: 1 }), {
      wrapper: wrapperFor(),
    });
    await waitFor(() => expect(result.current.isStatusLoading).toBe(false));

    act(() => result.current.toggle());
    await waitFor(() => expect(result.current.isMutating).toBe(true));

    act(() => result.current.toggle());
    await waitFor(() => expect(apiMock.addFavourite).toHaveBeenCalledTimes(1));
  });
});
