import { jsxLocPlugin } from "@builder.io/vite-plugin-jsx-loc";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "path";
import { defineConfig } from "vite";
import { vitePluginManusRuntime } from "vite-plugin-manus-runtime";

// jsxLocPlugin and vitePluginManusRuntime are dev/IDE-only instrumentation:
//   - In test mode (VITEST=1) they tear over Vitest's worker IPC under
//     parallel-worker contention.
//   - In production builds (`vite build`) the Manus runtime emits an inline
//     ~365 KB <script id="manus-runtime"> that has no production purpose
//     AND forces script-src 'unsafe-inline' in the nginx CSP. Gating on
//     `command === 'build'` lets the CSP drop 'unsafe-inline' cleanly.
// Only loaded for `vite serve` (dev server), not for tests or production.
export default defineConfig(({ command }) => {
  const isTest = !!process.env.VITEST;
  const isBuild = command === "build";
  const plugins = [
    react(),
    tailwindcss(),
    ...(!isTest && !isBuild ? [jsxLocPlugin(), vitePluginManusRuntime()] : []),
  ];

  return {
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
            // v3.1 Phase 2 (F-H3): split recharts into its own chunk. It's
            // imported by ~21 page files (AI Insights, P2P, Pareto, Tail-
            // Spend, Maverick, etc.); without an explicit chunk Rollup
            // duplicates the ~600KB lib across page chunks instead of
            // sharing it as vendor code.
            "vendor-recharts": ["recharts"],
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
  };
});
