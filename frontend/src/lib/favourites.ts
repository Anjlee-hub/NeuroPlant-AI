import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "neuroplant.favourites";

function readIds(): number[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (Array.isArray(parsed)) {
      return parsed.filter((n): n is number => typeof n === "number");
    }
    return [];
  } catch {
    return [];
  }
}

function writeIds(ids: number[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Storage can be unavailable (private mode / blocked) — favourites then
    // just live for the tab's lifetime; nothing else to do.
  }
}

/**
 * localStorage-backed favourites for the buyer marketplace (M4 Task 3). This is
 * intentionally architecture-ready with NO backend: the hook owns the listing-id
 * set, keeps it in sync across tabs via the `storage` event, and exposes a plain
 * toggle. A future task can swap the storage layer for a `POST
 * /favourites/:listingId` call without touching the button components — they
 * only ever call `isFavourite` / `toggle`.
 */
export function useFavourites(): {
  ids: number[];
  isFavourite: (id: number) => boolean;
  toggle: (id: number) => void;
} {
  const [ids, setIds] = useState<number[]>(() => readIds());

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key !== STORAGE_KEY) return;
      setIds(readIds());
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const toggle = useCallback((id: number) => {
    setIds((prev) => {
      const next = prev.includes(id)
        ? prev.filter((x) => x !== id)
        : [...prev, id];
      writeIds(next);
      return next;
    });
  }, []);

  return {
    ids,
    isFavourite: (id) => ids.includes(id),
    toggle,
  };
}
