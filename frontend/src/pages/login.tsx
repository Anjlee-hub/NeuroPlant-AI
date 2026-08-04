import { useTranslation } from "react-i18next";

/**
 * Login stub — full phone/OTP + password form lands with the auth task.
 */
export function LoginPage() {
  const { t } = useTranslation();

  return (
    <section className="mx-auto flex max-w-sm flex-col items-center gap-2 px-6 py-24 text-center">
      <h1 className="text-2xl font-bold">{t("auth.loginTitle")}</h1>
      <p className="text-muted-foreground">{t("auth.loginSubtitle")}</p>
    </section>
  );
}
