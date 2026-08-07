import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";

/**
 * Full-screen photo viewer for the listing gallery (M4 Task 3). Fixed overlay
 * with a dark backdrop; closes on Escape or backdrop click, steps with the
 * arrow keys or the prev/next buttons. Focus is moved onto the close button on
 * open (and kept inside via the Escape handler) so keyboard users aren't lost
 * behind the overlay. Only rendered while open — the gallery owns the toggle.
 */
export function Lightbox({
  images,
  index,
  name,
  onClose,
  onIndexChange,
}: {
  images: string[];
  /** Index of the photo currently shown (0-based). */
  index: number;
  /** Listing name — used for the image's accessible name. */
  name: string;
  onClose: () => void;
  onIndexChange: (next: number) => void;
}) {
  const { t } = useTranslation();
  const closeRef = useRef<HTMLButtonElement>(null);
  const total = images.length;
  const prev = (index - 1 + total) % total;
  const next = (index + 1) % total;

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft") onIndexChange(prev);
      else if (e.key === "ArrowRight") onIndexChange(next);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, onIndexChange, prev, next]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t("marketplaceBuy.gallery.mainImage", { name })}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <Button
        ref={closeRef}
        variant="ghost"
        size="icon"
        aria-label={t("marketplaceBuy.gallery.closeLightbox")}
        className="absolute top-4 right-4 text-white hover:bg-white/10 hover:text-white"
        onClick={onClose}
      >
        <X className="size-6" />
      </Button>

      {total > 1 && (
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("marketplaceBuy.gallery.prev")}
          className="absolute left-2 top-1/2 -translate-y-1/2 text-white hover:bg-white/10 hover:text-white sm:left-4"
          onClick={() => onIndexChange(prev)}
        >
          <ChevronLeft className="size-8" />
        </Button>
      )}

      <img
        src={images[index]}
        alt={t("marketplaceBuy.gallery.mainImage", { name })}
        className="max-h-full max-w-full rounded-md object-contain"
      />

      {total > 1 && (
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("marketplaceBuy.gallery.next")}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-white hover:bg-white/10 hover:text-white sm:right-4"
          onClick={() => onIndexChange(next)}
        >
          <ChevronRight className="size-8" />
        </Button>
      )}

      {total > 1 && (
        <p className="absolute bottom-4 left-1/2 -translate-x-1/2 text-sm text-white/80">
          {index + 1} / {total}
        </p>
      )}
    </div>
  );
}
