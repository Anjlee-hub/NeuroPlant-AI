import { CalendarClock, MoveLeft, Sparkles, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface ComingSoonPageProps {
  /** Nav/feature key — resolves the title via `nav.<navKey>`. */
  navKey: string;
  /** Milestone this feature lands in, e.g. "3" → "Milestone 3". */
  milestone: string;
  icon: LucideIcon;
}

/**
 * Honest "coming later" page for features deferred to a future milestone.
 * Unlike a dead link, it tells the user *what* is coming and *when*, so a
 * placeholder never masquerades as a broken feature.
 */
export function ComingSoonPage({ navKey, milestone, icon: Icon }: ComingSoonPageProps) {
  const { t } = useTranslation();
  const features = t(`comingSoon.${navKey}Features`, { returnObjects: true }) as string[];

  return (
    <section className="mx-auto max-w-2xl px-6 py-16 text-center sm:py-20">
      <Badge variant="outline">{t("comingSoon.badge")}</Badge>
      <h1 className="mt-4 flex items-center justify-center gap-2 text-3xl font-bold tracking-tight">
        <Icon className="size-7 text-brand-600 dark:text-brand-400" />
        {t(`nav.${navKey}`)}
      </h1>
      <p className="mx-auto mt-3 max-w-xl text-lg text-muted-foreground">
        {t(`comingSoon.${navKey}Body`)}
      </p>

      <p className="mt-5 inline-flex items-center gap-2 rounded-full border border-brand-300 bg-brand-50 px-4 py-1.5 text-sm font-medium text-brand-800 dark:border-brand-800 dark:bg-brand-950 dark:text-brand-200">
        <CalendarClock className="size-4" />
        {t("comingSoon.milestone", { milestone })}
      </p>

      <Card className="mt-8 text-left">
        <CardContent className="p-6">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <Sparkles className="size-4 text-brand-500" />
            {t("comingSoon.plannedTitle")}
          </h2>
          <ul className="mt-4 flex flex-col gap-3">
            {features.map((feature) => (
              <li key={feature} className="flex items-start gap-3 text-sm">
                <span
                  aria-hidden
                  className="mt-1.5 size-2 shrink-0 rounded-full bg-brand-500"
                />
                <span className="text-muted-foreground">{feature}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Button asChild variant="outline" className="mt-8">
        <Link to="/">
          <MoveLeft />
          {t("common.backHome")}
        </Link>
      </Button>
    </section>
  );
}
