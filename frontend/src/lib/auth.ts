/**
 * Authentication utilities for cookie-based JWT authentication
 *
 * Security Features:
 * - JWT tokens stored in HTTP-only cookies (XSS protection)
 * - Session timeout tracking (30 minutes inactivity)
 * - HTTPS enforcement in production
 *
 * Note: Since tokens are in HTTP-only cookies, JavaScript cannot read them.
 * Auth state is determined by the presence of user data and server validation.
 */

const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const LAST_ACTIVITY_KEY = "analytics_last_activity";
const USER_KEY = "user";

/**
 * Check if user appears to be authenticated
 * Note: This only checks client-side state. Server validates the actual JWT cookie.
 *
 * @returns True if user data exists and session hasn't timed out
 */
export function isAuthenticated(): boolean {
  const user = localStorage.getItem(USER_KEY);

  // No user data means not authenticated
  if (!user) {
    return false;
  }

  // Check if session has timed out
  const lastActivity = localStorage.getItem(LAST_ACTIVITY_KEY);
  if (lastActivity) {
    const lastActivityTime = parseInt(lastActivity, 10);
    const now = Date.now();
    const timeSinceActivity = now - lastActivityTime;

    if (timeSinceActivity >= SESSION_TIMEOUT_MS) {
      // Session timed out, clear local data
      clearSession();
      return false;
    }
  }

  return true;
}

/**
 * Update the last activity timestamp
 * Call this on user interactions to prevent timeout
 */
export function updateActivity(): void {
  const now = Date.now();
  localStorage.setItem(LAST_ACTIVITY_KEY, now.toString());
}

/**
 * Clear the current session (logout)
 * Note: HTTP-only cookies are cleared by the server on logout API call
 */
export function clearSession(): void {
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(LAST_ACTIVITY_KEY);
}

/**
 * Get remaining session time in milliseconds
 *
 * @returns Remaining time in ms, or 0 if no session
 */
export function getRemainingSessionTime(): number {
  const lastActivity = localStorage.getItem(LAST_ACTIVITY_KEY);

  if (!lastActivity) {
    return 0;
  }

  const lastActivityTime = parseInt(lastActivity, 10);
  const now = Date.now();
  const timeSinceActivity = now - lastActivityTime;
  const remaining = SESSION_TIMEOUT_MS - timeSinceActivity;

  return Math.max(0, remaining);
}

/**
 * Check if session has timed out due to inactivity
 *
 * @returns True if session has timed out
 */
export function isSessionExpired(): boolean {
  if (!isAuthenticated()) {
    return true;
  }
  return getRemainingSessionTime() <= 0;
}

/**
 * Check if HTTPS is being used (production requirement)
 *
 * @returns True if using HTTPS or localhost
 */
export function isSecureContext(): boolean {
  // Allow localhost for development
  if (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
  ) {
    return true;
  }

  // Require HTTPS in production
  return window.location.protocol === "https:";
}

/**
 * Initialize session tracking after login
 */
export function initializeSession(): void {
  updateActivity();
}

/**
 * Store user data after successful login
 * Note: Tokens are stored in HTTP-only cookies by the server
 */
export function setUserData(user: unknown): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  initializeSession();
}

/**
 * Get stored user data
 */
export function getUserData<T>(): T | null {
  const user = localStorage.getItem(USER_KEY);
  if (!user) {
    return null;
  }
  try {
    return JSON.parse(user) as T;
  } catch {
    return null;
  }
}
