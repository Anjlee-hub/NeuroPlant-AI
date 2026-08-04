import { Leaf } from "lucide-react";
import { useTranslation } from "react-i18next";

export function Footer() {
  const { t } = useTranslation();
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-2 px-6 py-8 text-center">
        <span className="flex items-center gap-2 font-semibold">
          <Leaf className="size-4 text-primary" />
          {t("app.name")}
        </span>
        <p className="text-sm text-muted-foreground">{t("footer.tagline")}</p>
        <p className="text-xs text-muted-foreground/70">
          © {year} {t("app.name")}. {t("footer.rights")}
        </p>
      </div>
    </footer>
  );
}
