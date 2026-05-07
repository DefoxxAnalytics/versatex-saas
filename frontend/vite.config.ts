import { jsxLocPlugin } from "@builder.io/vite-plugin-jsx-loc";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "path";
import { defineConfig } from "vite";
import { vitePluginManusRuntime } from "vite-plugin-manus-runtime";

// jsxLocPlugin and vitePluginManusRuntime instrument source files with
// positional metadata that's serialized over Vitest's worker IPC. Under
// parallel-worker contention the JSON payloads can tear, producing flaky
// "SyntaxError: Unterminated string" / "missing ) after argument list"
// failures in random suites. Exclude them from test mode.
const isTest = !!process.env.VITEST;

const plugins = [
  react(),
  tailwindcss(),
  ...(isTest ? [] : [jsxLocPlugin(), vitePluginManusRuntime()]),
];

export default defineConfig({
  plugins,
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "src"),
      "@assets": path.resolve(import.meta.dirname, "attached_assets"),
    },
  },
  envDir: path.resolve(import.meta.dirname),
  root: path.resolve(import.meta.dirname),
  build: {
    outDir: path.resolve(import.meta.dirname, "dist"),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom"],
          "vendor-charts": ["echarts"],
          "vendor-query": ["@tanstack/react-query"],
          "vendor-ui": [
            "@radix-ui/react-dialog",
            "@radix-ui/react-dropdown-menu",
            "@radix-ui/react-tooltip",
            "@radix-ui/react-popover",
            "@radix-ui/react-select",
            "@radix-ui/react-tabs",
            "@radix-ui/react-avatar",
            "@radix-ui/react-checkbox",
            "@radix-ui/react-label",
            "@radix-ui/react-separator",
            "@radix-ui/react-slot",
            "@radix-ui/react-switch",
          ],
          "vendor-router": ["wouter"],
          "vendor-utils": [
            "axios",
            "clsx",
            "class-variance-authority",
            "tailwind-merge",
          ],
        },
      },
    },
  },
  server: {
    port: 5173,
    strictPort: false, // Will find next available port if 5173 is busy
    host: true,
    allowedHosts: [
      ".manuspre.computer",
      ".manus.computer",
      ".manus-asia.computer",
      ".manuscomputer.ai",
      ".manusvm.computer",
      "localhost",
      "127.0.0.1",
    ],
    fs: {
      strict: true,
      deny: ["**/.*"],
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    exclude: ["**/node_modules/**", "**/e2e/**"],
    // Serialize suites in one fork. Halves the flake rate vs default
    // multi-fork (~3/10 vs ~6/10) without meaningfully increasing wall
    // time on a 30-suite project. Combined with the server.ts deferred-
    // handlers fix and the test-mode plugin exclusion above, the original
    // "handlers is not iterable" failure mode is eliminated; the residual
    // ~30% flake is a Vite transform-pipeline issue (Unterminated JSON /
    // Invalid token / missing-paren errors at suite-load time, hitting
    // random files each run) that's beyond this cleanup's scope.
    pool: "forks",
    poolOptions: {
      forks: {
        singleFork: true,
      },
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov", "json-summary"],
      // Floors set just below current measured coverage (May 2026 baseline:
      // 70.69 stmt / 61.13 branch / 65.89 func / 72.02 line). Ratchet up as
      // tests are added; never relax.
      thresholds: {
        lines: 65,
        statements: 65,
        functions: 60,
        branches: 55,
      },
    },
  },
});
