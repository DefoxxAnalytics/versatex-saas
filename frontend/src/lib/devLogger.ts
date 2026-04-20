/**
 * Development-only logging utility
 *
 * All logging is gated behind import.meta.env.DEV to prevent
 * information leakage in production builds.
 *
 * Usage:
 *   import { devLog, devWarn, devError } from '@/lib/devLogger';
 *   devLog('Debug info', data);
 *   devWarn('Warning message', context);
 *   devError('Error occurred', error);
 */

type LogArgs = unknown[];

/**
 * Log debug information (only in development)
 */
export function devLog(...args: LogArgs): void {
  if (import.meta.env.DEV) {
    console.log(...args);
  }
}

/**
 * Log warnings (only in development)
 */
export function devWarn(...args: LogArgs): void {
  if (import.meta.env.DEV) {
    console.warn(...args);
  }
}

/**
 * Log errors (only in development)
 */
export function devError(...args: LogArgs): void {
  if (import.meta.env.DEV) {
    console.error(...args);
  }
}

/**
 * Log with a custom label/prefix (only in development)
 */
export function devLogLabeled(label: string, ...args: LogArgs): void {
  if (import.meta.env.DEV) {
    console.log(`[${label}]`, ...args);
  }
}

/**
 * Console group for related logs (only in development)
 */
export function devGroup(label: string, fn: () => void): void {
  if (import.meta.env.DEV) {
    console.group(label);
    fn();
    console.groupEnd();
  }
}

/**
 * Log timing information (only in development)
 */
export function devTime(label: string): void {
  if (import.meta.env.DEV) {
    console.time(label);
  }
}

export function devTimeEnd(label: string): void {
  if (import.meta.env.DEV) {
    console.timeEnd(label);
  }
}
