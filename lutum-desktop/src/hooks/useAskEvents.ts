/**
 * useAskEvents Hook
 * ==================
 * SSE connection for live updates during Ask pipeline.
 */

import { useState, useEffect, useCallback, useRef } from "react";

const BACKEND_URL = "http://127.0.0.1:8420";

export interface AskEvent {
  type: "connected" | "starting" | "stage_start" | "stage_content" | "scrape_start" | "scrape_progress" | "scrape_done" | "done" | "error" | "ping" | "log";
  message: string;
  data?: {
    stage?: string; // C1, C2, C3, C4, C5, C6
    content?: string; // Stage output content
    phase?: number; // 1 or 2 for scraping phases
    done?: number; // Progress done
    total?: number; // Progress total
    count?: number; // Count of items
    sources?: Array<{ url: string; content?: string; success?: boolean }>; // Scraped sources
    queries?: string[]; // Search queries
    duration?: number; // Duration in seconds
    level?: "WARNING" | "ERROR";
    full?: string;
  };
}

/**
 * Hook for SSE events during Ask pipeline.
 */
export function useAskEvents() {
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const eventHandlerRef = useRef<((event: AskEvent) => void) | null>(null);

  // Connect to SSE endpoint
  const connect = useCallback((sessionId: string, eventHandler: (event: AskEvent) => void) => {
    if (!sessionId || eventSourceRef.current) return;

    eventHandlerRef.current = eventHandler;

    const url = `${BACKEND_URL}/ask/events/${sessionId}`;
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      console.log("[AskSSE] Connected to", url);
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const parsed: AskEvent = JSON.parse(event.data);
        console.log("[AskSSE] Event:", parsed.type, parsed.message);

        if (parsed.type !== "ping" && eventHandlerRef.current) {
          eventHandlerRef.current(parsed);
        }

        if (parsed.type === "done" || parsed.type === "error") {
          console.log("[AskSSE] Pipeline ended, closing connection");
          disconnect();
        }
      } catch (e) {
        console.error("[AskSSE] Failed to parse event:", e, event.data);
      }
    };

    eventSource.onerror = (error) => {
      console.error("[AskSSE] Connection error:", error);
      if (eventHandlerRef.current) {
        eventHandlerRef.current({
          type: "error",
          message: "Ask SSE connection lost.",
        });
      }
      setIsConnected(false);
      disconnect();
    };

    eventSourceRef.current = eventSource;
  }, []);

  // Disconnect
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
      console.log("[AskSSE] Disconnected");
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    connect,
    disconnect,
  };
}
