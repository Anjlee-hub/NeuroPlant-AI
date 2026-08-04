import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom ships no matchMedia — the theme provider and theme toggle rely on it.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Boot i18next once so components render translated text (not raw keys).
import "@/i18n";
