import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import type { CropAvailability } from "@/types/marketplace";

/**
 * Single source of truth for listing-availability colors. Previously every
 * page would have re-declared its own band mapping, so sold-out/archived
 * could drift between the dashboard, the form's status picker and (later)
 * customer browse. The archived bucket is rendered outline-on-muted so a
 * retired listing is clearly "not on the market" rather than alarming.
 */
export function availabilityVariant(
  availability: CropAvailability,
): "success" | "secondary" | "destructive" | "outline" {
  if (availability === "available") return "success";
  if (availability === "limited") return "secondary";
  if (availability === "sold_out") return "destructive";
  return "outline"; // archived
}

/** Localized availability badge (available / limited / sold out / archived). */
export function AvailabilityBadge({
  availability,
  className,
}: {
  availability: CropAvailability;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <Badge variant={availabilityVariant(availability)} className={className}>
      {t(`marketplace.availability.${availability}`)}
    </Badge>
  );
}
