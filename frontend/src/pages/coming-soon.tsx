import { MoveLeft } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

/**
 * Stub route for modules that land in later milestones (detection,
 * crop doctor, marketplace). Reads its title from the nav i18n key so
 * the header links resolve without dead 404s in M1.
 */
export function ComingSoonPage({ navKey }: { navKey: string }) {
  const { t } = useTranslation();

  return (
    <section className="mx-auto flex max-w-md flex-col items-center gap-4 px-6 py-24 text-center">
      <Badge variant="outline">{t("common.comingSoon")}</Badge>
      <h1 className="text-2xl font-bold">{t(`nav.${navKey}`)}</h1>
      <Button asChild variant="outline">
        <Link to="/">
          <MoveLeft />
          {t("common.backHome")}
        </Link>
      </Button>
    </section>
  );
}
