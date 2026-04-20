/**
 * MSW server setup for tests
 */
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

// Create the server instance
export const server = setupServer(...handlers);
