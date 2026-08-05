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

// jsdom ships no IntersectionObserver — motion/react's whileInView (used on
// the landing page) needs it. A no-op stub leaves elements "in view" but
// still queryable, which is what the Home smoke tests rely on.
class IntersectionObserverStub implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds = [0];
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

vi.stubGlobal("IntersectionObserver", IntersectionObserverStub);

// Boot i18next once so components render translated text (not raw keys).
import "@/i18n";
