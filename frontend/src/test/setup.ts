import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Vitest 4 can run jsdom without a usable global localStorage depending on
// the Node host. Provide a standards-shaped in-memory implementation so
// i18n, theme and language preference tests exercise the same Storage API.
class MemoryStorage implements Storage {
  private readonly values = new Map<string, string>();

  get length(): number {
    return this.values.size;
  }

  clear(): void {
    this.values.clear();
  }

  getItem(key: string): string | null {
    return this.values.has(key) ? this.values.get(key)! : null;
  }

  key(index: number): string | null {
    return Array.from(this.values.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }

  setItem(key: string, value: string): void {
    this.values.set(String(key), String(value));
  }
}

const testLocalStorage = new MemoryStorage();

Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: testLocalStorage,
});
Object.defineProperty(window, "localStorage", {
  configurable: true,
  value: testLocalStorage,
});

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

Object.defineProperty(Element.prototype, "scrollIntoView", {
  configurable: true,
  value: vi.fn(),
});

// jsdom ships no createObjectURL/revokeObjectURL — the Scan Crop preview and
// the offline queue thumbnail rely on them. Returning a stable blob URL keeps
// the object-URL lifecycle exercises safe under jsdom.
Object.defineProperty(URL, "createObjectURL", {
  writable: true,
  value: vi.fn(() => "blob:test-preview"),
});
Object.defineProperty(URL, "revokeObjectURL", {
  writable: true,
  value: vi.fn(),
});

// Boot i18next once so components render translated text (not raw keys).
import "@/i18n";
