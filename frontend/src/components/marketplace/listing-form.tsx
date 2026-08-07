import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ListingImageUploader } from "@/components/marketplace/image-uploader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import type {
  CropAvailability,
  CropCategory,
  CropListing,
  CropListingInput,
  CropUnit,
} from "@/types/marketplace";
import { CROP_AVAILABILITY_OPTIONS } from "@/types/marketplace";

/**
 * Create / edit form for one crop listing (M4 Task 2). Owns every field the
 * backend accepts, validates the three required rules client-side (name,
 * positive quantity, non-negative price) so a save can't fail on obvious
 * input, and lets the ImageUploader own the photos. Submit calls the same
 * service the rest of the app uses — create or PATCH — and reports the saved
 * listing up so the page can navigate back.
 */

const CROP_CATEGORIES: CropCategory[] = [
  "vegetable",
  "fruit",
  "grain",
  "pulses",
  "spice",
  "other",
];

const UNITS: CropUnit[] = ["kg", "g", "qtl", "bag", "dozen", "piece", "l", "box", "bundle"];

const inputClass =
  "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

export function ListingForm({
  listing,
  onSaved,
  onCancel,
}: {
  /** Present in edit mode — initializes every field. */
  listing?: CropListing;
  onSaved: (listing: CropListing) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const editing = listing !== undefined;

  const [cropName, setCropName] = useState(listing?.crop_name ?? "");
  const [category, setCategory] = useState<CropCategory>(listing?.category ?? "vegetable");
  const [variety, setVariety] = useState(listing?.variety ?? "");
  const [quantity, setQuantity] = useState(listing ? String(listing.quantity) : "");
  const [unit, setUnit] = useState<CropUnit>(listing?.unit ?? "kg");
  const [price, setPrice] = useState(listing ? String(listing.price) : "");
  const [description, setDescription] = useState(listing?.description ?? "");
  const [location, setLocation] = useState(listing?.location ?? "");
  const [organic, setOrganic] = useState(listing?.organic ?? false);
  const [harvestDate, setHarvestDate] = useState(listing?.harvest_date?.slice(0, 10) ?? "");
  const [availability, setAvailability] = useState<CropAvailability>(
    listing?.availability ?? "available",
  );
  const [images, setImages] = useState<string[]>(listing?.images ?? []);

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    const name = cropName.trim();
    const qty = Number(quantity);
    const prc = Number(price);
    if (!name) {
      setSubmitError(t("marketplace.form.requiredFields"));
      return;
    }
    if (!Number.isFinite(qty) || qty <= 0) {
      setSubmitError(t("marketplace.form.requiredFields"));
      return;
    }
    if (!Number.isFinite(prc) || prc < 0) {
      setSubmitError(t("marketplace.form.requiredFields"));
      return;
    }

    const payload: CropListingInput = {
      crop_name: name,
      category,
      variety: variety.trim() || null,
      quantity: qty,
      unit,
      price: prc,
      description: description.trim() || null,
      location: location.trim() || null,
      organic,
      harvest_date: harvestDate || null,
      availability,
      images: images.length > 0 ? images : null,
    };

    setSaving(true);
    try {
      const saved = editing
        ? await api.updateCropListing(listing.id, payload)
        : await api.createCropListing(payload);
      onSaved(saved);
    } catch {
      setSubmitError(t("marketplace.form.error"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="lf-name">{t("marketplace.form.cropNameLabel")}</Label>
          <Input
            id="lf-name"
            value={cropName}
            onChange={(e) => setCropName(e.target.value)}
            placeholder={t("marketplace.form.cropNamePlaceholder")}
            required
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="lf-category">{t("marketplace.form.categoryLabel")}</Label>
          <Select
            id="lf-category"
            value={category}
            onChange={(e) => setCategory(e.target.value as CropCategory)}
          >
            {CROP_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {t(`marketplace.categories.${c}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="lf-variety">{t("marketplace.form.varietyLabel")}</Label>
          <Input
            id="lf-variety"
            value={variety}
            onChange={(e) => setVariety(e.target.value)}
            placeholder={t("marketplace.form.varietyPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="lf-quantity">{t("marketplace.form.quantityLabel")}</Label>
          <Input
            id="lf-quantity"
            type="number"
            min="0.01"
            step="any"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="lf-unit">{t("marketplace.form.unitLabel")}</Label>
          <Select id="lf-unit" value={unit} onChange={(e) => setUnit(e.target.value as CropUnit)}>
            {UNITS.map((u) => (
              <option key={u} value={u}>
                {t(`marketplace.units.${u}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="lf-price">{t("marketplace.form.priceLabel")}</Label>
          <Input
            id="lf-price"
            type="number"
            min="0"
            step="any"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder={t("marketplace.form.pricePlaceholder")}
            required
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="lf-harvest">{t("marketplace.form.harvestDateLabel")}</Label>
          <Input
            id="lf-harvest"
            type="date"
            value={harvestDate}
            onChange={(e) => setHarvestDate(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="lf-description">{t("marketplace.form.descriptionLabel")}</Label>
          <textarea
            id="lf-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t("marketplace.form.descriptionPlaceholder")}
            rows={3}
            className={`${inputClass} h-auto py-2`}
          />
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="lf-location">{t("marketplace.form.locationLabel")}</Label>
          <Input
            id="lf-location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder={t("marketplace.form.locationPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="lf-availability">{t("marketplace.form.availabilityLabel")}</Label>
          <Select
            id="lf-availability"
            value={availability}
            onChange={(e) => setAvailability(e.target.value as CropAvailability)}
          >
            {CROP_AVAILABILITY_OPTIONS.map((a) => (
              <option key={a} value={a}>
                {t(`marketplace.availability.${a}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex items-end gap-2 pb-2.5">
          <input
            id="lf-organic"
            type="checkbox"
            checked={organic}
            onChange={(e) => setOrganic(e.target.checked)}
            className="size-4 rounded border-input accent-brand-600"
          />
          <Label htmlFor="lf-organic" className="cursor-pointer">
            {t("marketplace.form.organicLabel")}
          </Label>
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label>{t("marketplace.form.imagesLabel")}</Label>
          <ListingImageUploader initialUrls={images} onChange={setImages} />
        </div>
      </div>

      {submitError && <p className="text-sm text-destructive">{submitError}</p>}

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="size-4 animate-spin" aria-hidden />}
          {saving ? t("marketplace.form.saving") : t("marketplace.form.save")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
          {t("marketplace.form.cancel")}
        </Button>
      </div>
    </form>
  );
}
