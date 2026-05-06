import "@testing-library/jest-dom";
import { expect, afterEach, beforeAll, afterAll } from "vitest";
import { cleanup } from "@testing-library/react";
import * as matchers from "@testing-library/jest-dom/matchers";
import { server, installHandlers } from "./mocks/server";

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

// Start MSW server before all tests. Handlers are installed inside beforeAll
// rather than at server.ts module-load time to avoid a Vite SSR race in
// parallel Vitest workers where the `handlers` named import can resolve to
// undefined, producing "__vite_ssr_import_1__.handlers is not iterable".
beforeAll(() => {
  installHandlers();
  server.listen({ onUnhandledRequest: "warn" });
});

// Reset handlers after each test (back to the full installed set)
afterEach(() => {
  cleanup();
  installHandlers();
});

// Close server after all tests
afterAll(() => {
  server.close();
});

// Mock window.matchMedia for theme tests
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  readonly root: Element | null = null;
  readonly rootMargin: string = "";
  readonly thresholds: ReadonlyArray<number> = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
};

// Mock localStorage with working storage
const localStorageData: Record<string, string> = {};
const localStorageMock = {
  getItem: (key: string) => localStorageData[key] ?? null,
  setItem: (key: string, value: string) => {
    localStorageData[key] = value;
  },
  removeItem: (key: string) => {
    delete localStorageData[key];
  },
  clear: () => {
    Object.keys(localStorageData).forEach(
      (key) => delete localStorageData[key],
    );
  },
  get length() {
    return Object.keys(localStorageData).length;
  },
  key: (index: number) => Object.keys(localStorageData)[index] ?? null,
};
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Clear localStorage between tests
afterEach(() => {
  localStorageMock.clear();
});

// Mock IndexedDB with fake-indexeddb
import "fake-indexeddb/auto";
