/**
 * Tests for Authentication Utilities (lib/auth.ts)
 *
 * Tests cover:
 * - Session authentication status
 * - Activity tracking and timeout
 * - Session expiration
 * - User data storage and retrieval
 * - Security context checks
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  isAuthenticated,
  updateActivity,
  clearSession,
  getRemainingSessionTime,
  isSessionExpired,
  isSecureContext,
  initializeSession,
  setUserData,
  getUserData,
} from "../auth";

// Constants to match the auth.ts file
const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const LAST_ACTIVITY_KEY = "analytics_last_activity";
const USER_KEY = "user";

describe("Authentication Utilities", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    localStorage.clear();
    vi.useRealTimers();
  });

  // =====================
  // isAuthenticated Tests
  // =====================
  describe("isAuthenticated", () => {
    it("should return false when no user data exists", () => {
      expect(isAuthenticated()).toBe(false);
    });

    it("should return true when user data exists and no timeout", () => {
      localStorage.setItem(
        USER_KEY,
        JSON.stringify({ id: 1, username: "test" }),
      );
      localStorage.setItem(LAST_ACTIVITY_KEY, Date.now().toString());

      expect(isAuthenticated()).toBe(true);
    });

    it("should return true when user exists but no activity timestamp", () => {
      localStorage.setItem(
        USER_KEY,
        JSON.stringify({ id: 1, username: "test" }),
      );
      // No LAST_ACTIVITY_KEY set

      expect(isAuthenticated()).toBe(true);
    });

    it("should return false when session has timed out", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      // Set user data with old activity
      localStorage.setItem(
        USER_KEY,
        JSON.stringify({ id: 1, username: "test" }),
      );
      localStorage.setItem(
        LAST_ACTIVITY_KEY,
        (now - SESSION_TIMEOUT_MS - 1000).toString(),
      );

      expect(isAuthenticated()).toBe(false);
    });

    it("should return true when session is just under timeout", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      localStorage.setItem(
        USER_KEY,
        JSON.stringify({ id: 1, username: "test" }),
      );
      localStorage.setItem(
        LAST_ACTIVITY_KEY,
        (now - SESSION_TIMEOUT_MS + 1000).toString(),
      );

      expect(isAuthenticated()).toBe(true);
    });

    it("should clear session data when timeout is detected", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      localStorage.setItem(
        USER_KEY,
        JSON.stringify({ id: 1, username: "test" }),
      );
      localStorage.setItem(
        LAST_ACTIVITY_KEY,
        (now - SESSION_TIMEOUT_MS - 1000).toString(),
      );

      isAuthenticated();

      // Session should be cleared
      expect(localStorage.getItem(USER_KEY)).toBeNull();
      expect(localStorage.getItem(LAST_ACTIVITY_KEY)).toBeNull();
    });
  });

  // =====================
  // updateActivity Tests
  // =====================
  describe("updateActivity", () => {
    it("should store current timestamp in localStorage", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      updateActivity();

      expect(localStorage.getItem(LAST_ACTIVITY_KEY)).toBe(now.toString());
    });

    it("should update existing timestamp", () => {
      const oldTime = Date.now();
      vi.setSystemTime(oldTime);
      localStorage.setItem(LAST_ACTIVITY_KEY, oldTime.toString());

      // Advance time
      const newTime = oldTime + 5000;
      vi.setSystemTime(newTime);

      updateActivity();

      expect(localStorage.getItem(LAST_ACTIVITY_KEY)).toBe(newTime.toString());
    });
  });

  // =====================
  // clearSession Tests
  // =====================
  describe("clearSession", () => {
    it("should remove user data from localStorage", () => {
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      localStorage.setItem(LAST_ACTIVITY_KEY, "12345");

      clearSession();

      expect(localStorage.getItem(USER_KEY)).toBeNull();
    });

    it("should remove activity timestamp from localStorage", () => {
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      localStorage.setItem(LAST_ACTIVITY_KEY, "12345");

      clearSession();

      expect(localStorage.getItem(LAST_ACTIVITY_KEY)).toBeNull();
    });

    it("should not throw when localStorage is already empty", () => {
      expect(() => clearSession()).not.toThrow();
    });
  });

  // =====================
  // getRemainingSessionTime Tests
  // =====================
  describe("getRemainingSessionTime", () => {
    it("should return 0 when no activity timestamp exists", () => {
      expect(getRemainingSessionTime()).toBe(0);
    });

    it("should return full session time when just logged in", () => {
      const now = Date.now();
      vi.setSystemTime(now);
      localStorage.setItem(LAST_ACTIVITY_KEY, now.toString());

      const remaining = getRemainingSessionTime();
      expect(remaining).toBe(SESSION_TIMEOUT_MS);
    });

    it("should return reduced time after some activity", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      const elapsedTime = 10 * 60 * 1000; // 10 minutes
      localStorage.setItem(LAST_ACTIVITY_KEY, (now - elapsedTime).toString());

      const remaining = getRemainingSessionTime();
      expect(remaining).toBe(SESSION_TIMEOUT_MS - elapsedTime);
    });

    it("should return 0 when session has expired", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      localStorage.setItem(
        LAST_ACTIVITY_KEY,
        (now - SESSION_TIMEOUT_MS - 1000).toString(),
      );

      const remaining = getRemainingSessionTime();
      expect(remaining).toBe(0);
    });

    it("should never return negative value", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      // Set activity way in the past
      localStorage.setItem(
        LAST_ACTIVITY_KEY,
        (now - SESSION_TIMEOUT_MS * 2).toString(),
      );

      const remaining = getRemainingSessionTime();
      expect(remaining).toBeGreaterThanOrEqual(0);
    });
  });

  // =====================
  // isSessionExpired Tests
  // =====================
  describe("isSessionExpired", () => {
    it("should return true when not authenticated", () => {
      // No user data
      expect(isSessionExpired()).toBe(true);
    });

    it("should return false when session is active", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      localStorage.setItem(LAST_ACTIVITY_KEY, now.toString());

      expect(isSessionExpired()).toBe(false);
    });

    it("should return true when session time has run out", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      localStorage.setItem(
        LAST_ACTIVITY_KEY,
        (now - SESSION_TIMEOUT_MS - 1).toString(),
      );

      expect(isSessionExpired()).toBe(true);
    });

    it("should return false when exactly at timeout boundary", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      // Set activity exactly at timeout boundary (not yet expired)
      localStorage.setItem(
        LAST_ACTIVITY_KEY,
        (now - SESSION_TIMEOUT_MS + 1).toString(),
      );

      expect(isSessionExpired()).toBe(false);
    });
  });

  // =====================
  // isSecureContext Tests
  // =====================
  describe("isSecureContext", () => {
    const originalLocation = window.location;

    beforeEach(() => {
      // Mock window.location
      delete (window as any).location;
    });

    afterEach(() => {
      window.location = originalLocation;
    });

    it("should return true for localhost", () => {
      window.location = {
        ...originalLocation,
        hostname: "localhost",
        protocol: "http:",
      } as Location;

      expect(isSecureContext()).toBe(true);
    });

    it("should return true for 127.0.0.1", () => {
      window.location = {
        ...originalLocation,
        hostname: "127.0.0.1",
        protocol: "http:",
      } as Location;

      expect(isSecureContext()).toBe(true);
    });

    it("should return true for HTTPS in production", () => {
      window.location = {
        ...originalLocation,
        hostname: "app.example.com",
        protocol: "https:",
      } as Location;

      expect(isSecureContext()).toBe(true);
    });

    it("should return false for HTTP in production", () => {
      window.location = {
        ...originalLocation,
        hostname: "app.example.com",
        protocol: "http:",
      } as Location;

      expect(isSecureContext()).toBe(false);
    });
  });

  // =====================
  // initializeSession Tests
  // =====================
  describe("initializeSession", () => {
    it("should set activity timestamp", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      initializeSession();

      expect(localStorage.getItem(LAST_ACTIVITY_KEY)).toBe(now.toString());
    });
  });

  // =====================
  // setUserData Tests
  // =====================
  describe("setUserData", () => {
    it("should store user object as JSON string", () => {
      const user = { id: 1, username: "testuser", email: "test@example.com" };

      setUserData(user);

      const stored = localStorage.getItem(USER_KEY);
      expect(stored).toBe(JSON.stringify(user));
    });

    it("should initialize session after storing user data", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      setUserData({ id: 1 });

      expect(localStorage.getItem(LAST_ACTIVITY_KEY)).toBe(now.toString());
    });

    it("should handle complex user objects", () => {
      const complexUser = {
        id: 1,
        username: "admin",
        profile: {
          organization: 1,
          role: "admin",
          permissions: ["read", "write", "delete"],
        },
      };

      setUserData(complexUser);

      const stored = localStorage.getItem(USER_KEY);
      expect(JSON.parse(stored!)).toEqual(complexUser);
    });
  });

  // =====================
  // getUserData Tests
  // =====================
  describe("getUserData", () => {
    it("should return null when no user data exists", () => {
      expect(getUserData()).toBeNull();
    });

    it("should return parsed user object", () => {
      const user = { id: 1, username: "testuser" };
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      const result = getUserData<{ id: number; username: string }>();

      expect(result).toEqual(user);
    });

    it("should return typed user data", () => {
      interface TestUser {
        id: number;
        name: string;
        role: "admin" | "user";
      }

      const user: TestUser = { id: 1, name: "Test", role: "admin" };
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      const result = getUserData<TestUser>();

      expect(result).toEqual(user);
      expect(result?.role).toBe("admin");
    });

    it("should return null for invalid JSON", () => {
      localStorage.setItem(USER_KEY, "not valid json {{{");

      const result = getUserData();

      expect(result).toBeNull();
    });

    it("should return null for empty string", () => {
      localStorage.setItem(USER_KEY, "");

      // Empty string is falsy but not removed
      const result = getUserData();

      // JSON.parse('') will throw, so should return null
      expect(result).toBeNull();
    });
  });

  // =====================
  // Integration Tests
  // =====================
  describe("Integration Scenarios", () => {
    it("should handle complete login-activity-logout flow", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      // Step 1: Login
      const user = { id: 1, username: "testuser" };
      setUserData(user);
      expect(isAuthenticated()).toBe(true);

      // Step 2: Some activity
      vi.setSystemTime(now + 5 * 60 * 1000); // 5 minutes later
      updateActivity();
      expect(isAuthenticated()).toBe(true);
      expect(getRemainingSessionTime()).toBe(SESSION_TIMEOUT_MS);

      // Step 3: More time passes but still active
      vi.setSystemTime(now + 20 * 60 * 1000); // 20 minutes later
      expect(isAuthenticated()).toBe(true);
      expect(getRemainingSessionTime()).toBe(
        SESSION_TIMEOUT_MS - 15 * 60 * 1000,
      );

      // Step 4: Logout
      clearSession();
      expect(isAuthenticated()).toBe(false);
      expect(getUserData()).toBeNull();
    });

    it("should handle session timeout scenario", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      // Login
      setUserData({ id: 1 });
      expect(isAuthenticated()).toBe(true);

      // Wait for timeout
      vi.setSystemTime(now + SESSION_TIMEOUT_MS + 1000);

      // Check authentication (should detect timeout and clear)
      expect(isAuthenticated()).toBe(false);
      expect(getUserData()).toBeNull();
    });

    it("should keep session alive with regular activity updates", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      setUserData({ id: 1 });

      // Simulate activity every 10 minutes
      for (let i = 1; i <= 5; i++) {
        vi.setSystemTime(now + i * 10 * 60 * 1000);
        updateActivity();
        expect(isAuthenticated()).toBe(true);
      }

      // 50 minutes have passed total, but session is still active
      expect(getRemainingSessionTime()).toBe(SESSION_TIMEOUT_MS);
    });
  });
});
