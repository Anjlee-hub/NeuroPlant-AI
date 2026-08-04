import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

/**
 * Vitest config — separate from vite.config.ts so the PWA/Workbox plugin
 * never runs in the test build. Mirrors the `@` alias so imports resolve
 * identically to the app.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    // The host shell exports NODE_ENV=production globally, which otherwise
    // resolves the production React build (no React.act) and breaks testing.
    env: { NODE_ENV: "test" },
  },
});
