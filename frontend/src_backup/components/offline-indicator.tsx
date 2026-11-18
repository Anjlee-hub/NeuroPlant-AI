import { WifiOff } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useNetwork } from "@/offline/network";

/**
 * Fixed bottom banner shown while offline. Hidden once connectivity
 * returns (the sync loop then drains the IndexedDB queue).
 */
export function OfflineIndicator() {
  const { t } = useTranslation();
  const isOnline = useNetwork((state) => state.isOnline);

  if (isOnline) return null;

  return (
    <div
      role="status"
      className="fixed inset-x-0 bottom-0 z-40 flex items-center justify-center gap-2 border-t border-brand-300 bg-brand-50 px-4 py-2 text-sm font-medium text-brand-800 dark:border-brand-800 dark:bg-brand-950 dark:text-brand-200"
    >
      <WifiOff className="size-4 shrink-0" />
      {t("common.offline")}
    </div>
  );
}
