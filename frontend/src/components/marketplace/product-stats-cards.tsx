import { Archive, Box, CheckCircle2, AlertCircle } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";
import type { ProductStats } from "@/types/marketplace";

/**
 * Dashboard summary counts for the seller's own catalog (M4 Task 4).
 * Mirrors the backend `ProductStatsOut` — total / active (in_stock) /
 * out_of_stock / archived — so the four numbers the seller sees are exactly
 * the ones the stats endpoint computes.
 */
export function ProductStatsCards({ stats }: { stats: ProductStats }) {
  const { t } = useTranslation();

  const items = [
    { key: "total", label: "sellerPortal.stats.total", icon: Box },
    { key: "active", label: "sellerPortal.stats.active", icon: CheckCircle2 },
    { key: "out_of_stock", label: "sellerPortal.stats.out_of_stock", icon: AlertCircle },
    { key: "archived", label: "sellerPortal.stats.archived", icon: Archive },
  ] as const;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map(({ key, label, icon: Icon }) => (
        <Card key={key}>
          <CardContent className="flex items-center gap-3 p-4">
            <Icon className="size-5 shrink-0 text-muted-foreground" aria-hidden />
            <div className="min-w-0">
              <p className="text-2xl font-bold leading-none">{stats[key]}</p>
              <p className="mt-1 truncate text-xs text-muted-foreground">{t(label)}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}