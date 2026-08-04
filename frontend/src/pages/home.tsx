import { useTranslation } from "react-i18next";

/**
 * Landing placeholder. The full marketing landing (hero, live scan demo,
 * how-it-works, testimonials) lands with task "M1 — landing + auth pages".
 * This stub exercises i18n + theming so the shell is verifiable now.
 */
export function HomePage() {
  const { t } = useTranslation();

  return (
    <section className="mx-auto flex max-w-3xl flex-col items-center px-6 py-24 text-center">
      <p className="text-sm font-medium uppercase tracking-widest text-brand-600 dark:text-brand-400">
        {t("landing.badge")}
      </p>
      <h1 className="mt-4 text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
        {t("landing.title")}
      </h1>
      <p className="mt-4 max-w-xl text-muted-foreground">
        {t("landing.subtitle")}
      </p>
    </section>
  );
}
