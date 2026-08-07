import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useFavourites } from "@/lib/favourites";

const STORAGE_KEY = "neuroplant.favourites";

describe("useFavourites", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("starts with no favourites", () => {
    const { result } = renderHook(() => useFavourites());
    expect(result.current.ids).toEqual([]);
    expect(result.current.isFavourite(1)).toBe(false);
  });

  it("toggles a listing in and out, persisting to localStorage", () => {
    const { result } = renderHook(() => useFavourites());

    act(() => result.current.toggle(1));
    expect(result.current.isFavourite(1)).toBe(true);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]")).toEqual([1]);

    act(() => result.current.toggle(1));
    expect(result.current.isFavourite(1)).toBe(false);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]")).toEqual([]);
  });

  it("keeps multiple favourites and supports more than one", () => {
    const { result } = renderHook(() => useFavourites());

    act(() => result.current.toggle(3));
    act(() => result.current.toggle(7));

    expect(result.current.ids).toEqual([3, 7]);
    expect(result.current.isFavourite(7)).toBe(true);
  });

  it("rehydrates from existing storage on mount", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([7, 3]));
    const { result } = renderHook(() => useFavourites());
    expect(result.current.ids).toEqual([7, 3]);
    expect(result.current.isFavourite(3)).toBe(true);
  });

  it("ignores corrupt storage and starts empty", () => {
    localStorage.setItem(STORAGE_KEY, "not-json");
    const { result } = renderHook(() => useFavourites());
    expect(result.current.ids).toEqual([]);
  });
});
