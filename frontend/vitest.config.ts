import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    exclude: ["src/tests/e2e/**", "node_modules/**", "dist/**"],
    setupFiles: "./src/tests/setup.ts",
    css: true,
    restoreMocks: true,
    clearMocks: true,
  },
});
