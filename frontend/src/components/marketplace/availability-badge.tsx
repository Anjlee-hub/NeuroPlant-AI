import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import type { CropAvailability, ProductAvailability } from "@/types/marketplace";

/**
 * Single source of truth for listing-availability colors. Previously every
 * page would have re-declared its own band mapping, so sold-out/archived
 * could drift between the dashboard, the form's status picker and (later)
 * customer browse. The archived bucket is rendered outline-on-muted so a
 * retired listing is clearly "not on the market" rather than alarming.
 */
export function cropAvailabilityVariant(
  availability: CropAvailability,
): "success" | "secondary" | "destructive" | "outline" {
  if (availability === "available") return "success";
  if (availability === "limited") return "secondary";
  if (availability === "sold_out") return "destructive";
  return "outline"; // archived
}

export function productAvailabilityVariant(
  availability: ProductAvailability,
): "success" | "secondary" | "destructive" | "outline" {
  if (availability === "in_stock") return "success";
  if (availability === "out_of_stock") return "destructive";
  return "outline"; // archived
}

/** Localized availability badge for farmer crop listings (available / limited / sold out / archived). */
export function CropAvailabilityBadge({
  availability,
  className,
}: {
  availability: CropAvailability;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <Badge variant={cropAvailabilityVariant(availability)} className={className}>
      {t(`marketplace.availability.${availability}`)}
    </Badge>
  );
}

/** Localized availability badge for seller products (in_stock / out_of_stock / archived). */
export function ProductAvailabilityBadge({
  availability,
  className,
}: {
  availability: ProductAvailability;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <Badge variant={productAvailabilityVariant(availability)} className={className}>
      {t(`sellerPortal.availability.${availability}`)}
    </Badge>
  );
}

/** Legacy export for backwards compatibility — use CropAvailabilityBadge or ProductAvailabilityBadge instead. */
export function AvailabilityBadge({
  availability,
  className,
}: {
  availability: CropAvailability;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <Badge variant={cropAvailabilityVariant(availability)} className={className}>
      {t(`marketplace.availability.${availability}`)}
    </Badge>
  );
}
