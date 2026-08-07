import { ImagePlus, Loader2, X } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

/**
 * Multi-image upload for a crop listing (M4 Task 2).
 *
 * The uploader owns two lists: persisted URLs (already on the server, from a
 * saved listing's `images`) and local pending files (picked but not yet
 * uploaded). Validating a picked batch up front — count ≤ 8, JPEG/PNG/WebP,
 * ≤ 10 MB each — matches the backend's own limits, so a batch that passes
 * here won't be rejected as a whole by `POST /marketplace/crops/images`.
 *
 * Only persisted URLs are reported via `onChange`; pending files become URLs
 * when the farmer presses "Add photos", which uploads the whole batch at
 * once (mirroring the single multipart request the backend expects).
 */

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_IMAGES = 8;
const MAX_BYTES = 10 * 1024 * 1024; // 10 MB

interface PendingImage {
  id: number;
  file: File;
  preview: string;
}

export function ListingImageUploader({
  initialUrls = [],
  onChange,
}: {
  /** URLs already persisted (edit mode — a saved listing's `images`). */
  initialUrls?: string[];
  /** Called with the persisted URL list whenever it changes. */
  onChange: (urls: string[]) => void;
}) {
  const { t } = useTranslation();
  const [urls, setUrls] = useState<string[]>(initialUrls);
  const [pending, setPending] = useState<PendingImage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const nextId = useRef(0);

  const totalCount = urls.length + pending.length;
  const atLimit = totalCount >= MAX_IMAGES;

  const pickFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setError(null);

    const chosen = Array.from(files);
    if (totalCount + chosen.length > MAX_IMAGES) {
      setError(t("marketplace.upload.tooMany"));
      return;
    }
    const tooLarge = chosen.find((file) => file.size > MAX_BYTES);
    if (tooLarge) {
      setError(t("marketplace.upload.tooLarge"));
      return;
    }
    const badType = chosen.find((file) => !ACCEPTED_TYPES.includes(file.type));
    if (badType) {
      setError(t("marketplace.upload.invalidType"));
      return;
    }

    setPending((prev) => [
      ...prev,
      ...chosen.map((file) => ({
        id: nextId.current++,
        file,
        preview: URL.createObjectURL(file),
      })),
    ]);
  };

  const uploadPending = async () => {
    if (pending.length === 0 || uploading) return;
    setError(null);
    setUploading(true);
    try {
      const files = pending.map((p) => p.file);
      const { urls: uploaded } = await api.uploadListingImages(files);
      const next = [...urls, ...uploaded];
      setUrls(next);
      setPending((prev) => {
        for (const p of prev) URL.revokeObjectURL(p.preview);
        return [];
      });
      onChange(next);
    } catch {
      // Keep the pending batch so the farmer can retry a transient failure.
      setError(t("marketplace.upload.error"));
    } finally {
      setUploading(false);
    }
  };

  const removePersisted = (target: string) => {
    const next = urls.filter((url) => url !== target);
    setUrls(next);
    onChange(next);
  };

  const removePending = (target: PendingImage) => {
    URL.revokeObjectURL(target.preview);
    setPending((prev) => prev.filter((p) => p.id !== target.id));
  };

  return (
    <div>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
        {urls.map((url) => (
          <div
            key={url}
            className="group relative aspect-square overflow-hidden rounded-md border"
          >
            <img src={url} alt="" className="h-full w-full object-cover" />
            <button
              type="button"
              onClick={() => removePersisted(url)}
              className="absolute top-1 right-1 rounded-full bg-background/90 p-1 text-muted-foreground shadow-sm hover:text-destructive"
              aria-label={t("marketplace.upload.remove")}
            >
              <X className="size-3.5" />
            </button>
          </div>
        ))}
        {pending.map((p) => (
          <div
            key={p.id}
            className="group relative aspect-square overflow-hidden rounded-md border"
          >
            <img src={p.preview} alt="" className="h-full w-full object-cover" />
            <button
              type="button"
              onClick={() => removePending(p)}
              className="absolute top-1 right-1 rounded-full bg-background/90 p-1 text-muted-foreground shadow-sm hover:text-destructive"
              aria-label={t("marketplace.upload.remove")}
            >
              <X className="size-3.5" />
            </button>
          </div>
        ))}

        {!atLimit && (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="flex aspect-square flex-col items-center justify-center gap-1 rounded-md border border-dashed text-muted-foreground transition-colors hover:border-brand-600 hover:text-brand-600 disabled:opacity-50"
          >
            <ImagePlus className="size-5" aria-hidden />
            <span className="text-xs">{t("marketplace.upload.add")}</span>
          </button>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="hidden"
        onChange={(e) => {
          pickFiles(e.target.files);
          // Allow re-picking the same file after a failed validation.
          e.target.value = "";
        }}
        aria-label={t("marketplace.upload.add")}
      />

      {pending.length > 0 && (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="mt-3"
          onClick={() => void uploadPending()}
          disabled={uploading}
        >
          {uploading ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <ImagePlus className="size-4" aria-hidden />
          )}
          {uploading ? t("marketplace.upload.adding") : t("marketplace.upload.add")}
        </Button>
      )}

      <p className="mt-2 text-xs text-muted-foreground">{t("marketplace.upload.hint")}</p>
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  );
}
