import { useTranslation } from "react-i18next";

import { LANGUAGES } from "@/i18n";
import { useLanguage } from "@/hooks/use-language";
import { cn } from "@/lib/utils";

/**
 * Inline language picker driven by the `LANGUAGES` registry in `@/i18n`.
 * Grows into a full picker (12 languages + auto-detect) in M4 — adding a
 * language there is enough; the switcher renders it automatically.
 */
export function LanguageSwitcher() {
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();

  return (
    <div
      className="flex items-center gap-0.5 rounded-lg border border-border p-0.5"
      role="group"
      aria-label={t("languages.label")}
    >
      {LANGUAGES.filter((lang) => lang.enabled).map((lang) => (
        <button
          key={lang.code}
          type="button"
          onClick={() => setLanguage(lang.code)}
          aria-pressed={language === lang.code}
          className={cn(
            "rounded-md px-2 py-1 text-xs font-medium transition-colors",
            language === lang.code
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {lang.nativeName}
        </button>
      ))}
    </div>
  );
}
