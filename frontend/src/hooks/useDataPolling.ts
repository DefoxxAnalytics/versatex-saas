/**
 * useDataPolling Hook
 *
 * Polls the backend for new data every 60 seconds.
 * Shows notification when data count changes, prompting user to refresh.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { procurementAPI } from "@/lib/api";
import { toast } from "sonner";

const POLLING_INTERVAL = 60000; // 60 seconds

interface PollingState {
  /** Whether polling is active */
  isPolling: boolean;
  /** Last known record count */
  lastCount: number | null;
  /** Whether new data is available */
  hasNewData: boolean;
  /** Last check timestamp */
  lastChecked: Date | null;
}

interface UseDataPollingOptions {
  /** Polling interval in milliseconds (default: 60000) */
  interval?: number;
  /** Whether to start polling immediately (default: true) */
  enabled?: boolean;
  /** Callback when new data is detected */
  onNewData?: (newCount: number, previousCount: number) => void;
}

/**
 * Hook for polling backend for new data
 */
export function useDataPolling(options: UseDataPollingOptions = {}) {
  const { interval = POLLING_INTERVAL, enabled = true, onNewData } = options;

  const [state, setState] = useState<PollingState>({
    isPolling: false,
    lastCount: null,
    hasNewData: false,
    lastChecked: null,
  });

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isFirstCheck = useRef(true);

  /**
   * Check for new data
   */
  const checkForNewData = useCallback(async () => {
    try {
      // Fetch just the count (page_size=1 for efficiency)
      const response = await procurementAPI.getTransactions({ page_size: 1 });
      const currentCount = response.data.count;
      const now = new Date();

      setState((prev) => {
        // On first check, just store the count
        if (isFirstCheck.current) {
          isFirstCheck.current = false;
          return {
            ...prev,
            lastCount: currentCount,
            lastChecked: now,
          };
        }

        // Check if count changed
        if (prev.lastCount !== null && currentCount !== prev.lastCount) {
          // New data detected
          onNewData?.(currentCount, prev.lastCount);

          // Show toast notification
          const diff = currentCount - prev.lastCount;
          if (diff > 0) {
            toast.info(
              `${diff} new record${diff > 1 ? "s" : ""} available. Click refresh to update.`,
              {
                duration: 10000,
                action: {
                  label: "Refresh Now",
                  onClick: () => {
                    window.dispatchEvent(new CustomEvent("refreshData"));
                  },
                },
              },
            );
          } else if (diff < 0) {
            toast.info(`Data has been updated. Click refresh to see changes.`, {
              duration: 10000,
              action: {
                label: "Refresh Now",
                onClick: () => {
                  window.dispatchEvent(new CustomEvent("refreshData"));
                },
              },
            });
          }

          return {
            ...prev,
            lastCount: currentCount,
            hasNewData: true,
            lastChecked: now,
          };
        }

        return {
          ...prev,
          lastChecked: now,
        };
      });
    } catch (error) {
      // Only log in development
      if (import.meta.env.DEV) {
        console.error("Polling error:", error);
      }
      // Don't update state on error, just skip this check
    }
  }, [onNewData]);

  /**
   * Start polling
   */
  const startPolling = useCallback(() => {
    if (intervalRef.current) return;

    setState((prev) => ({ ...prev, isPolling: true }));

    // Initial check
    checkForNewData();

    // Set up interval
    intervalRef.current = setInterval(checkForNewData, interval);
  }, [checkForNewData, interval]);

  /**
   * Stop polling
   */
  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    setState((prev) => ({ ...prev, isPolling: false }));
  }, []);

  /**
   * Clear the "new data" flag
   */
  const clearNewDataFlag = useCallback(() => {
    setState((prev) => ({ ...prev, hasNewData: false }));
  }, []);

  // Start/stop polling based on enabled state
  useEffect(() => {
    if (enabled) {
      startPolling();
    } else {
      stopPolling();
    }

    return () => {
      stopPolling();
    };
  }, [enabled, startPolling, stopPolling]);

  // Listen for manual refresh events
  useEffect(() => {
    const handleRefresh = () => {
      clearNewDataFlag();
      // Reset count to trigger fresh check
      isFirstCheck.current = true;
      checkForNewData();
    };

    window.addEventListener("refreshData", handleRefresh);
    return () => {
      window.removeEventListener("refreshData", handleRefresh);
    };
  }, [clearNewDataFlag, checkForNewData]);

  return {
    ...state,
    startPolling,
    stopPolling,
    checkForNewData,
    clearNewDataFlag,
  };
}
