import { Archive, CheckCircle2, Layers, Leaf } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card, CardContent } from "@/components/ui/card";
import type { CropListingStats } from "@/types/marketplace";

/**
 * Dashboard summary counts for the farmer's own listings (M4 Task 2).
 * Mirrors the backend `CropListingStatsOut` — total / active / sold /
 * archived — so the four numbers the farmer sees are exactly the ones the
 * stats endpoint computes, never a client-side re-count.
 */
export function StatsCards({ stats }: { stats: CropListingStats }) {
  const { t } = useTranslation();

  const items = [
    { key: "total", icon: Layers },
    { key: "active", icon: Leaf },
    { key: "sold", icon: CheckCircle2 },
    { key: "archived", icon: Archive },
  ] as const;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map(({ key, icon: Icon }) => (
        <Card key={key}>
          <CardContent className="flex items-center gap-3 p-4">
            <Icon className="size-5 shrink-0 text-muted-foreground" aria-hidden />
            <div className="min-w-0">
              <p className="text-2xl font-bold leading-none">{stats[key]}</p>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {t(`marketplace.stats.${key}`)}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
