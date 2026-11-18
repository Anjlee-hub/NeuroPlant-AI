import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ListingImageUploader } from "@/components/marketplace/image-uploader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { SellerProfile, SellerUpdate } from "@/types/marketplace";

/**
 * Shop profile form (M4 Task 4).
 * Fields: shop_name, address, phone, delivery_available, description, opening_hours, logo_url, banner_url
 * Uses ListingImageUploader for logo and banner uploads (repurposed for single-image selection).
 */
const inputClass =
  "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

export function ShopProfileForm({
  shop,
  onSaved,
  onCancel,
}: {
  /** Current shop profile — initializes every field. */
  shop: SellerProfile;
  onSaved: (shop: SellerProfile) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();

  const [shopName, setShopName] = useState(shop.shop_name ?? "");
  const [address, setAddress] = useState(shop.address ?? "");
  const [phone, setPhone] = useState(shop.phone ?? "");
  const [deliveryAvailable, setDeliveryAvailable] = useState(shop.delivery_available ?? false);
  const [description, setDescription] = useState(shop.description ?? "");
  const [openingHours, setOpeningHours] = useState(shop.opening_hours ?? "");
  const [logoUrl, setLogoUrl] = useState<string[]>(shop.logo_url ? [shop.logo_url] : []);
  const [bannerUrl, setBannerUrl] = useState<string[]>(shop.banner_url ? [shop.banner_url] : []);

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    const name = shopName.trim();
    if (!name) {
      setSubmitError(t("sellerPortal.profile.error"));
      return;
    }

    // Use only the first image from the uploader for logo/banner
    const payload: SellerUpdate = {
      shop_name: name,
      address: address.trim() || null,
      phone: phone.trim() || null,
      delivery_available: deliveryAvailable,
      description: description.trim() || null,
      opening_hours: openingHours.trim() || null,
      logo_url: logoUrl[0] ?? null,
      banner_url: bannerUrl[0] ?? null,
    };

    setSaving(true);
    try {
      const saved = await api.updateShop(payload);
      onSaved(saved);
    } catch {
      setSubmitError(t("sellerPortal.profile.error"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="spf-shop-name">{t("sellerPortal.profile.shopNameLabel")}</Label>
          <Input
            id="spf-shop-name"
            value={shopName}
            onChange={(e) => setShopName(e.target.value)}
            placeholder={t("sellerPortal.profile.shopNamePlaceholder")}
            required
          />
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="spf-address">{t("sellerPortal.profile.addressLabel")}</Label>
          <Input
            id="spf-address"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder={t("sellerPortal.profile.addressPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="spf-phone">{t("sellerPortal.profile.phoneLabel")}</Label>
          <Input
            id="spf-phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder={t("sellerPortal.profile.phonePlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="spf-opening-hours">{t("sellerPortal.profile.openingHoursLabel")}</Label>
          <Input
            id="spf-opening-hours"
            value={openingHours}
            onChange={(e) => setOpeningHours(e.target.value)}
            placeholder={t("sellerPortal.profile.openingHoursPlaceholder")}
          />
        </div>

        <div className="flex items-center gap-2">
          <Switch
            id="spf-delivery"
            checked={deliveryAvailable}
            onChange={(e) => setDeliveryAvailable(e.target.checked)}
          />
          <Label htmlFor="spf-delivery" className="cursor-pointer font-normal">
            {t("sellerPortal.profile.deliveryLabel")}
          </Label>
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="spf-description">{t("sellerPortal.profile.descriptionLabel")}</Label>
          <Textarea
            id="spf-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t("sellerPortal.profile.descriptionPlaceholder")}
            rows={3}
            className={`${inputClass} h-auto py-2`}
          />
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label>{t("sellerPortal.profile.logoLabel")}</Label>
          <ListingImageUploader initialUrls={logoUrl} onChange={setLogoUrl} />
        </div>

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label>{t("sellerPortal.profile.bannerLabel")}</Label>
          <ListingImageUploader initialUrls={bannerUrl} onChange={setBannerUrl} />
        </div>
      </div>

      {submitError && <p className="text-sm text-destructive">{submitError}</p>}

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={saving}>
          {saving && <Loader2 className="size-4 animate-spin" aria-hidden />}
          {saving ? t("sellerPortal.profile.saving") : t("sellerPortal.profile.save")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
          {t("sellerPortal.form.cancel")}
        </Button>
      </div>
    </form>
  );
}