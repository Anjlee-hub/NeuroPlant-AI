import { MoveLeft } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <section className="mx-auto flex max-w-md flex-col items-center gap-4 px-6 py-24 text-center">
      <p className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
        404
      </p>
      <h1 className="text-2xl font-bold">{t("common.notFoundTitle")}</h1>
      <p className="text-muted-foreground">{t("common.notFoundBody")}</p>
      <Button asChild variant="outline">
        <Link to="/">
          <MoveLeft />
          {t("common.backHome")}
        </Link>
      </Button>
    </section>
  );
}
