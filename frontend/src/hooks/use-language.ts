import { useCallback } from "react";
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

  const setLanguage = useCallback(
    (lang: Language) => {
      void i18n.changeLanguage(lang);
      document.documentElement.lang = lang;
      localStorage.setItem(STORAGE_KEY, lang);
    },
    [],
  );

  return { language, setLanguage, supported: SUPPORTED_LANGUAGES };
}
