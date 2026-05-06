/**
 * Finding #13: AI chat streaming must use cookie auth (credentials: 'include'),
 * not localStorage-based bearer tokens.
 *
 * The project uses HTTP-only cookies; localStorage.getItem('access_token')
 * is always null in production. Without credentials: 'include', cookies
 * also aren't sent — the feature is broken.
 *
 * Refs: docs/codebase-review-2026-05-04-v2.md Finding #13
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { useAIChatStream, useAIQuickQuery } from "../useAIInsights";

type FetchMock = ReturnType<typeof vi.fn<typeof fetch>>;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

function makeStreamResponse(): Response {
  // #given a minimal SSE response body with a terminal "done" event
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      const encoder = new TextEncoder();
      controller.enqueue(encoder.encode('data: {"token":"hi"}\n\n'));
      controller.enqueue(encoder.encode('data: {"done":true}\n\n'));
      controller.close();
    },
  });

  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function readAuthHeader(
  init: RequestInit | undefined,
): string | null | undefined {
  const headers = init?.headers;
  if (!headers) return undefined;
  if (headers instanceof Headers) return headers.get("Authorization");
  if (Array.isArray(headers)) {
    const found = headers.find(([k]) => k.toLowerCase() === "authorization");
    return found?.[1];
  }
  return (headers as Record<string, string>)["Authorization"];
}

function installFetchMock(): FetchMock {
  const fetchMock = vi.fn<typeof fetch>(async () => makeStreamResponse());
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("useAIChatStream — Finding #13 cookie auth fix", () => {
  let fetchMock: FetchMock;

  beforeEach(() => {
    // #given localStorage is empty so any read of access_token returns null,
    //        which would surface the bug as `Bearer null`
    window.localStorage.clear();
    fetchMock = installFetchMock();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("calls fetch with credentials: 'include'", async () => {
    // #given the streaming chat hook
    const { result } = renderHook(() => useAIChatStream(), {
      wrapper: createWrapper(),
    });

    // #when sending a message
    await act(async () => {
      await result.current.sendMessage("hello");
    });

    // #then fetch is invoked with cookie credentials so HTTP-only auth cookie is sent
    expect(fetchMock).toHaveBeenCalled();
    const init = fetchMock.mock.calls[0][1];
    expect(init?.credentials).toBe("include");
  });

  it("does not send an Authorization header derived from localStorage", async () => {
    // #given the streaming chat hook with empty localStorage
    const { result } = renderHook(() => useAIChatStream(), {
      wrapper: createWrapper(),
    });

    // #when sending a message
    await act(async () => {
      await result.current.sendMessage("hello");
    });

    // #then no Bearer header is attached (cookie is the auth mechanism)
    const init = fetchMock.mock.calls[0][1];
    expect(readAuthHeader(init)).toBeFalsy();
  });
});

describe("useAIQuickQuery — Finding #13 cookie auth fix", () => {
  let fetchMock: FetchMock;

  beforeEach(() => {
    window.localStorage.clear();
    fetchMock = installFetchMock();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("calls fetch with credentials: 'include' and no Authorization header", async () => {
    // #given the quick-query hook
    const { result } = renderHook(() => useAIQuickQuery(), {
      wrapper: createWrapper(),
    });

    // #when querying
    await act(async () => {
      await result.current.query("how much did we spend?");
    });

    // #then fetch is invoked with cookie credentials and no Bearer header
    expect(fetchMock).toHaveBeenCalled();
    const init = fetchMock.mock.calls[0][1];
    expect(init?.credentials).toBe("include");
    expect(readAuthHeader(init)).toBeFalsy();
  });
});
