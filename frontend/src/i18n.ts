import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import hi from "./locales/hi.json";

/** Languages shipped in M1. Grows to 12 in M4 (voice + auto-detect). */
export const SUPPORTED_LANGUAGES = ["en", "hi"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

/**
 * Declarative language registry — the single source of truth for the
 * language switcher. Adding a language in M4 is: ship a `locales/<code>.json`
 * pack and append an entry here (with `enabled: true`). No other wiring is
 * needed — i18next loads the resource map below and the switcher renders from
 * this list. Languages without a real translation pack stay OUT of the
 * registry (we never fake translations).
 */
export interface LanguageMeta {
  /** BCP-47 code — also the i18next resource key. */
  code: Language;
  /** Native endonym shown in the language picker. */
  nativeName: string;
  enabled: boolean;
}

export const LANGUAGES: LanguageMeta[] = [
  { code: "en", nativeName: "English", enabled: true },
  { code: "hi", nativeName: "हिन्दी", enabled: true },
];

const LOCALE_PACKS = { en, hi } as const;

const resources = Object.fromEntries(
  LANGUAGES.filter((lang) => lang.enabled).map((lang) => [
    lang.code,
    { translation: LOCALE_PACKS[lang.code] },
  ]),
) as Record<string, { translation: object }>;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en",
    supportedLngs: [...SUPPORTED_LANGUAGES],
    // "en" / "hi", not "en-US" — language-only codes.
    load: "languageOnly",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
    },
  });

export default i18n;
