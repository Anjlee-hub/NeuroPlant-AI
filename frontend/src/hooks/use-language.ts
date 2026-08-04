import { useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";

import i18n, { type Language, SUPPORTED_LANGUAGES } from "@/i18n";

const STORAGE_KEY = "i18nextLng";

/**
 * Language switching for the current session. Persists to localStorage
 * (matching the i18next detector cache) and mirrors to <html lang>.
 * The 12-language auto-detection pipeline arrives in M4.
 */
export function useLanguage() {
  const { i18n: client } = useTranslation();
  const language = (client.resolvedLanguage as Language) || "en";

  // Keep <html lang> in sync on mount and on every change.
  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const setLanguage = useCallback(
    (lang: Language) => {
      void i18n.changeLanguage(lang);
      localStorage.setItem(STORAGE_KEY, lang);
    },
    [],
  );

  return { language, setLanguage, supported: SUPPORTED_LANGUAGES };
}
