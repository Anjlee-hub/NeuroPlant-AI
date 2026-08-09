import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { api, errorMessage } from "@/lib/api";
import type { FavouriteStatus } from "@/types/trust";

/**
 * Server-backed favourites (M4 Task 6) — the localStorage hook is gone. Saved
 * state comes from `GET /marketplace/favorites/status`, toggling is a POST /
 * DELETE against `/marketplace/favorites`, and both mutations update
 * optimistically (the heart flips instantly) then invalidate the status and the
 * collection so the favourites page and every button agree.
 *
 * The button component never talks to the network directly — it calls
 * `useFavouriteStatus`, which owns status loading, add/remove mutations, and
 * the error string.
 */

/** Query key for the caller's full favourites collection (the /favourites page). */
export const FAVOURITES_KEY = ["favourites"] as const;

/** Query key for one item's saved-state (button state). */
function statusKey(target: { listingId?: number; productId?: number }) {
  return ["favourite-status", target.listingId ?? null, target.productId ?? null] as const;
}

export interface UseFavouriteStatus {
  /** Whether the target is saved (false until the status has loaded). */
  isFavourited: boolean;
  /** True while the initial saved-state is loading. */
  isStatusLoading: boolean;
  /** True if the saved-state query failed — the button shows an error. */
  isStatusError: boolean;
  /** True while an add/remove mutation is in flight. */
  isMutating: boolean;
  /** Toggle the item in or out of the caller's favourites. */
  toggle: () => void;
  /** Latest add/remove failure message, or null. */
  error: string | null;
}

/**
 * Saved-state + toggle for a single item (a crop listing or a product — exactly
 * one of `listingId` / `productId`). Optimistic updates mean a click flips the
 * heart before the server confirms; on failure the queries are invalidated so
 * the real state is refetched and the error is surfaced for the button to show.
 */
export function useFavouriteStatus(target: {
  listingId?: number;
  productId?: number;
}): UseFavouriteStatus {
  const queryClient = useQueryClient();
  const key = statusKey(target);

  const statusQuery = useQuery({
    queryKey: key,
    queryFn: () =>
      api.favouriteStatus({
        listing_id: target.listingId,
        product_id: target.productId,
      }),
    enabled: target.listingId != null || target.productId != null,
  });

  const invalidate = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: key });
    void queryClient.invalidateQueries({ queryKey: FAVOURITES_KEY });
  }, [queryClient, key]);

  const add = useMutation({
    mutationFn: () =>
      api.addFavourite({
        listing_id: target.listingId,
        product_id: target.productId,
      }),
    onMutate: () => {
      queryClient.setQueryData<FavouriteStatus>(key, (prev) => ({
        favorited: true,
        favorite_id: prev?.favorite_id ?? null,
        listing_id: prev?.listing_id ?? target.listingId ?? null,
        product_id: prev?.product_id ?? target.productId ?? null,
      }));
    },
    onError: invalidate,
    onSettled: invalidate,
  });

  const remove = useMutation({
    mutationFn: (favouriteId: number) => api.removeFavourite(favouriteId),
    onMutate: () => {
      queryClient.setQueryData<FavouriteStatus>(key, (prev) => ({
        favorited: false,
        favorite_id: null,
        listing_id: prev?.listing_id ?? target.listingId ?? null,
        product_id: prev?.product_id ?? target.productId ?? null,
      }));
    },
    onError: invalidate,
    onSettled: invalidate,
  });

  const isMutating = add.isPending || remove.isPending;
  const status = statusQuery.data;
  const error =
    add.isError || remove.isError ? errorMessage(add.error ?? remove.error) : null;

  const toggle = useCallback(() => {
    if (isMutating) return;
    if (status?.favorited) {
      if (status.favorite_id != null) remove.mutate(status.favorite_id);
    } else {
      add.mutate();
    }
  }, [add, remove, status, isMutating]);

  return {
    isFavourited: status?.favorited ?? false,
    isStatusLoading: statusQuery.isPending,
    isStatusError: statusQuery.isError,
    isMutating,
    toggle,
    error,
  };
}
