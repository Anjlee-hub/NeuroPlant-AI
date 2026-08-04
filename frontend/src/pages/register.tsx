import { useTranslation } from "react-i18next";

/**
 * Register stub — full phone/OTP + password form lands with the auth task.
 */
export function RegisterPage() {
  const { t } = useTranslation();

  return (
    <section className="mx-auto flex max-w-sm flex-col items-center gap-2 px-6 py-24 text-center">
      <h1 className="text-2xl font-bold">{t("auth.registerTitle")}</h1>
      <p className="text-muted-foreground">{t("auth.registerSubtitle")}</p>
    </section>
  );
}
