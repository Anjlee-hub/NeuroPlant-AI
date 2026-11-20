import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import i18n from "@/i18n";
import { LANGUAGES } from "@/i18n";
import { AUTO_LANGUAGE_STORAGE_KEY, useLanguage } from "@/hooks/use-language";
import { cn } from "@/lib/utils";

/**
 * Inline language picker driven by the `LANGUAGES` registry in `@/i18n`.
 * Grows into a full picker (12 languages + auto-detect) in M4 — adding a
 * language there is enough; the switcher renders it automatically.
 */
export function LanguageSwitcher() {
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  const [autoLanguage, setAutoLanguage] = useState(
    () => localStorage.getItem(AUTO_LANGUAGE_STORAGE_KEY) === "true",
  );

  useEffect(() => {
    if (!autoLanguage) return;
    if (!navigator.geolocation) return;
    let active = true;

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(position.coords.latitude)}&lon=${encodeURIComponent(position.coords.longitude)}`,
          );
          if (!active || !response.ok) return;
          const data = (await response.json()) as {
            address?: { state?: string; region?: string; country_code?: string };
          };
          if (!active || localStorage.getItem(AUTO_LANGUAGE_STORAGE_KEY) !== "true") return;
          const region = (data.address?.state ?? data.address?.region ?? "").toLowerCase();
          const hindiRegions = [
            "uttar pradesh", "bihar", "rajasthan", "madhya pradesh",
            "chhattisgarh", "jharkhand", "uttarakhand", "haryana",
            "himachal pradesh", "delhi", "chandigarh",
          ];
          const nextLanguage =
            data.address?.country_code?.toLowerCase() === "in" &&
            hindiRegions.some((name) => region.includes(name))
              ? "hi"
              : "en";
          void i18n.changeLanguage(nextLanguage);
          localStorage.setItem("i18nextLng", nextLanguage);
        } catch {
          // Keep the user's current language if reverse geocoding fails.
        }
      },
      () => undefined,
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
    );

    return () => {
      active = false;
    };
  }, [autoLanguage]);

  const toggleAutoLanguage = () => {
    const next = !autoLanguage;
    setAutoLanguage(next);
    localStorage.setItem(AUTO_LANGUAGE_STORAGE_KEY, String(next));
  };

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        role="switch"
        aria-checked={autoLanguage}
        aria-label={t("languages.autoLabel")}
        title={t("languages.autoLabel")}
        onClick={toggleAutoLanguage}
        className={cn(
          "hidden h-7 items-center gap-1.5 rounded-lg border px-2 text-[11px] font-semibold sm:flex",
          autoLanguage ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground",
        )}
      >
        <span>{t("languages.auto")}</span>
        <span className={cn("relative h-4 w-7 rounded-full transition-colors", autoLanguage ? "bg-primary" : "bg-muted-foreground/30")}>
          <span className={cn("absolute top-0.5 size-3 rounded-full bg-white transition-transform", autoLanguage ? "left-3.5" : "left-0.5")} />
        </span>
      </button>
    <div
      className="flex items-center gap-0.5 rounded-lg border border-border p-0.5"
      role="group"
      aria-label={t("languages.label")}
    >
      {LANGUAGES.filter((lang) => lang.enabled).map((lang) => (
        <button
          key={lang.code}
          type="button"
          onClick={() => {
            setLanguage(lang.code);
            setAutoLanguage(false);
          }}
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
    </div>
  );
}
