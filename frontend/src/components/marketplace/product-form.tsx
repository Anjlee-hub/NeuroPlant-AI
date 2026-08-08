import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ListingImageUploader } from "@/components/marketplace/image-uploader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type {
  Product,
  ProductInput,
  ProductAvailability,
  ProductCategory,
  ProductUnit,
} from "@/types/marketplace";
import { PRODUCT_CATEGORY_OPTIONS, PRODUCT_AVAILABILITY_OPTIONS } from "@/types/marketplace";

/**
 * Create / edit form for one agricultural product (M4 Task 4).
 * Mirrors ListingForm pattern but with seller-specific fields:
 * - category from PRODUCT_CATEGORY_OPTIONS (fertilizer/pesticide/seed/tool/organic)
 * - availability from PRODUCT_AVAILABILITY_OPTIONS (in_stock/out_of_stock/archived)
 * - brand, stock_quantity, organic, manufacturer, usage_instructions
 * - Reuses ListingImageUploader for image handling
 */
const UNITS: ProductUnit[] = ["kg", "g", "qtl", "bag", "dozen", "piece", "l", "box", "bundle"];

const inputClass =
  "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

export function ProductForm({
  product,
  onSaved,
  onCancel,
}: {
  /** Present in edit mode — initializes every field. */
  product?: Product;
  onSaved: (product: Product) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const editing = product !== undefined;

  const [name, setName] = useState(product?.name ?? "");
  const [category, setCategory] = useState<ProductCategory>(product?.category ?? "fertilizer");
  const [brand, setBrand] = useState(product?.brand ?? "");
  const [description, setDescription] = useState(product?.description ?? "");
  const [price, setPrice] = useState(product ? String(product.price) : "");
  const [unit, setUnit] = useState<ProductUnit>(product?.unit ?? "kg");
  const [stockQuantity, setStockQuantity] = useState(product?.stock_quantity != null ? String(product.stock_quantity) : "");
  const [images, setImages] = useState<string[]>(product?.images ?? []);
  const [organic, setOrganic] = useState(product?.organic ?? false);
  const [manufacturer, setManufacturer] = useState(product?.manufacturer ?? "");
  const [usageInstructions, setUsageInstructions] = useState(product?.usage_instructions ?? "");
  const [availability, setAvailability] = useState<ProductAvailability>(
    product?.availability ?? "in_stock",
  );

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    const productName = name.trim();
    const prc = Number(price);
    const stock = stockQuantity.trim() ? Number(stockQuantity) : null;

    if (!productName) {
      setSubmitError(t("sellerPortal.form.requiredFields"));
      return;
    }
    if (!Number.isFinite(prc) || prc < 0) {
      setSubmitError(t("sellerPortal.form.requiredFields"));
      return;
    }
    if (stock !== null && (!Number.isFinite(stock) || stock < 0)) {
      setSubmitError(t("sellerPortal.form.requiredFields"));
      return;
    }

    const payload: ProductInput = {
      name: productName,
      category,
      brand: brand.trim() || null,
      description: description.trim() || null,
      price: prc,
      unit,
      stock_quantity: stock,
      images: images.length > 0 ? images : null,
      organic,
      manufacturer: manufacturer.trim() || null,
      usage_instructions: usageInstructions.trim() || null,
      availability,
    };

    setSaving(true);
    try {
      const saved = editing
        ? await api.updateProduct(product.id, payload)
        : await api.createProduct(payload);
      onSaved(saved);
    } catch {
      setSubmitError(t("sellerPortal.form.error"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="pf-name">{t("sellerPortal.form.nameLabel")}</Label>
          <Input
            id="pf-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("sellerPortal.form.namePlaceholder")}
            required
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pf-category">{t("sellerPortal.form.categoryLabel")}</Label>
          <Select
            id="pf-category"
            value={category}
            onChange={(e) => setCategory(e.target.value as ProductCategory)}
          >
            {PRODUCT_CATEGORY_OPTIONS.map((c) => (
              <option key={c} value={c}>
                {t(`sellerPortal.categories.${c}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pf-brand">{t("sellerPortal.form.brandLabel")}</Label>
          <Input
            id="pf-brand"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            placeholder={t("sellerPortal.form.brandPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pf-price">{t("sellerPortal.form.priceLabel")}</Label>
          <Input
            id="pf-price"
            type="number"
            min="0"
            step="any"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder={t("sellerPortal.form.pricePlaceholder")}
            required
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pf-unit">{t("sellerPortal.form.unitLabel")}</Label>
          <Select id="pf-unit" value={unit} onChange={(e) => setUnit(e.target.value as ProductUnit)}>
            {UNITS.map((u) => (
              <option key={u} value={u}>
                {t(`marketplace.units.${u}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pf-stock">{t("sellerPortal.form.stockLabel")}</Label>
          <Input
            id="pf-stock"
            type="number"
            min="0"
            step="1"
            value={stockQuantity}
            onChange={(e) => setStockQuantity(e.target.value)}
            placeholder={t("sellerPortal.form.stockPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="pf-description">{t("sellerPortal.form.descriptionLabel")}</Label>
          <Textarea
            id="pf-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t("sellerPortal.form.descriptionPlaceholder")}
            rows={3}
            className={`${inputClass} h-auto py-2`}
          />
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="pf-manufacturer">{t("sellerPortal.form.manufacturerLabel")}</Label>
          <Input
            id="pf-manufacturer"
            value={manufacturer}
            onChange={(e) => setManufacturer(e.target.value)}
            placeholder={t("sellerPortal.form.manufacturerPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="pf-usage">{t("sellerPortal.form.usageLabel")}</Label>
          <Textarea
            id="pf-usage"
            value={usageInstructions}
            onChange={(e) => setUsageInstructions(e.target.value)}
            placeholder={t("sellerPortal.form.usagePlaceholder")}
            rows={3}
            className={`${inputClass} h-auto py-2`}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pf-availability">{t("sellerPortal.form.availabilityLabel")}</Label>
          <Select
            id="pf-availability"
            value={availability}
            onChange={(e) => setAvailability(e.target.value as ProductAvailability)}
          >
            {PRODUCT_AVAILABILITY_OPTIONS.map((a) => (
              <option key={a} value={a}>
                {t(`sellerPortal.availability.${a}`)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex items-end gap-2 pb-2.5">
          <input
            id="pf-organic"
            type="checkbox"
            checked={organic}
            onChange={(e) => setOrganic(e.target.checked)}
            className="size-4 rounded border-input accent-brand-600"
          />
          <Label htmlFor="pf-organic" className="cursor-pointer">
            {t("sellerPortal.form.organicLabel")}
          </Label>
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label>{t("sellerPortal.form.imagesLabel")}</Label>
          <ListingImageUploader initialUrls={images} onChange={setImages} />
        </div>
      </div>

      {submitError && <p className="text-sm text-destructive">{submitError}</p>}

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="size-4 animate-spin" aria-hidden />}
          {saving ? t("sellerPortal.form.saving") : t("sellerPortal.form.save")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
          {t("sellerPortal.form.cancel")}
        </Button>
      </div>
    </form>
  );
}