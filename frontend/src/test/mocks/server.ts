/**
 * MSW server setup for tests.
 *
 * The server is constructed with no initial handlers; setup.ts loads them
 * inside beforeAll via installHandlers(). This avoids a Vite SSR module-load
 * race where parallel Vitest workers can see `handlers` as undefined when
 * this module's top-level evaluates first, producing the TypeError
 * "__vite_ssr_import_1__.handlers is not iterable".
 */
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer();

export function installHandlers(): void {
  server.resetHandlers(...handlers);
}
