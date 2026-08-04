import { useTranslation } from "react-i18next";

import { useLanguage } from "@/hooks/use-language";
import { cn } from "@/lib/utils";

/**
 * Inline language picker for the M1 language set. Grows into a full picker
 * (12 languages + auto-detect) in M4.
 */
export function LanguageSwitcher() {
  const { t } = useTranslation();
  const { language, setLanguage, supported } = useLanguage();

  return (
    <div
      className="flex items-center gap-0.5 rounded-lg border border-border p-0.5"
      role="group"
      aria-label={t("languages.label")}
    >
      {supported.map((lang) => (
        <button
          key={lang}
          type="button"
          onClick={() => setLanguage(lang)}
          aria-pressed={language === lang}
          className={cn(
            "rounded-md px-2 py-1 text-xs font-medium transition-colors",
            language === lang
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {t(`languages.${lang}`)}
        </button>
      ))}
    </div>
  );
}
