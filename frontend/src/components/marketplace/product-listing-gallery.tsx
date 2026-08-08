import { ChevronLeft, ChevronRight, ImageOff, ZoomIn } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Lightbox } from "@/components/marketplace/lightbox";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Photo gallery for the public product market detail page (M4 Task 4): a main
 * image with prev/next arrows, a thumbnail strip for direct jumps, and a
 * full-screen lightbox. The no-photo case renders an honest placeholder instead
 * of an empty frame. Thumbnails carry the photo's accessible name; the main
 * image opens the lightbox on click.
 */
export function ProductListingGallery({
  images,
  name,
}: {
  images: string[];
  name: string;
}) {
  const { t } = useTranslation();
  const [index, setIndex] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  if (images.length === 0) {
    return (
      <div
        className="flex aspect-square w-full items-center justify-center rounded-lg border bg-muted text-muted-foreground"
        role="img"
        aria-label={t("productMarket.detail.noImages")}
      >
        <ImageOff className="size-12" aria-hidden />
        <span className="sr-only">{t("productMarket.detail.noImages")}</span>
      </div>
    );
  }

  const total = images.length;
  const current = images[index];
  const prev = (index - 1 + total) % total;
  const next = (index + 1) % total;

  return (
    <div className="flex flex-col gap-3">
      {/* Main image + lightbox trigger. */}
      <div className="relative">
        <img
          src={current}
          alt={t("productMarket.gallery.mainImage", { name })}
          className="aspect-square w-full rounded-lg border object-cover"
        />
        <Button
          variant="outline"
          size="sm"
          className="absolute bottom-3 right-3 bg-background/80 backdrop-blur"
          onClick={() => setLightboxOpen(true)}
          aria-haspopup="dialog"
          aria-label={t("productMarket.gallery.openLightbox")}
        >
          <ZoomIn className="size-4" aria-hidden />
          {t("productMarket.gallery.openLightbox")}
        </Button>

        {total > 1 && (
          <>
            <Button
              variant="outline"
              size="icon"
              className="absolute left-2 top-1/2 -translate-y-1/2 bg-background/80 backdrop-blur"
              aria-label={t("productMarket.gallery.prev")}
              onClick={() => setIndex(prev)}
            >
              <ChevronLeft className="size-5" aria-hidden />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-background/80 backdrop-blur"
              aria-label={t("productMarket.gallery.next")}
              onClick={() => setIndex(next)}
            >
              <ChevronRight className="size-5" aria-hidden />
            </Button>
          </>
        )}
      </div>

      {/* Thumbnail strip — one button per photo. */}
      {total > 1 && (
        <div
          className="flex gap-2 overflow-x-auto pb-1"
          role="group"
          aria-label={t("productMarket.gallery.thumbnails", { name })}
        >
          {images.map((src, i) => (
            <button
              key={src + i}
              type="button"
              aria-label={t("productMarket.gallery.thumbnail", { name, n: i + 1 })}
              aria-current={i === index ? "true" : undefined}
              aria-pressed={i === index}
              className={cn(
                "size-16 shrink-0 overflow-hidden rounded-md border bg-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                i === index
                  ? "border-brand-600 ring-1 ring-brand-600 dark:border-brand-400 dark:ring-brand-400"
                  : "border-input opacity-70 hover:opacity-100",
              )}
              onClick={() => setIndex(i)}
            >
              <img
                src={src}
                alt=""
                className="h-full w-full object-cover"
                loading="lazy"
              />
            </button>
          ))}
        </div>
      )}

      {lightboxOpen && (
        <Lightbox
          images={images}
          index={index}
          name={name}
          onClose={() => setLightboxOpen(false)}
          onIndexChange={setIndex}
        />
      )}
    </div>
  );
}