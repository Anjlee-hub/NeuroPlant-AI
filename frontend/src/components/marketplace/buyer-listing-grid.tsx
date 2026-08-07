import { useTranslation } from "react-i18next";

import { BuyerListingCard } from "@/components/marketplace/buyer-listing-card";
import type { CropListing } from "@/types/marketplace";

/** Responsive grid of buyer listing cards (M4 Task 3). 1 → 2 → 3 columns as
 * viewport grows; the caller owns fetching/pagination/empty states. */
export function BuyerListingGrid({ listings }: { listings: CropListing[] }) {
  const { t } = useTranslation();
  return (
    <section
      aria-label={t("marketplaceBuy.grid.listLabel")}
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {listings.map((listing) => (
        <BuyerListingCard key={listing.id} listing={listing} />
      ))}
    </section>
  );
}
