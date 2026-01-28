/**
 * useResearchEvents Hook
 * ======================
 * SSE Verbindung für Live-Updates während Recherche.
 */

import { useState, useEffect, useCallback, useRef } from "react";

const BACKEND_URL = "http://127.0.0.1:8420";

export interface ResearchEvent {
  type: "connected" | "step_start" | "step_progress" | "step_done" | "error" | "done" | "ping";
  message: string;
}

/**
 * Hook für SSE Events während Recherche.
 */
export function useResearchEvents(sessionId: string | null) {
  const [currentStatus, setCurrentStatus] = useState<string>("");
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Verbindung starten
  const connect = useCallback(() => {
    if (!sessionId || eventSourceRef.current) return;

    const url = `${BACKEND_URL}/research/events/${sessionId}`;
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        // Parse JSON Event
        const parsed: ResearchEvent = JSON.parse(event.data);

        console.log("SSE Event:", parsed); // Debug

        if (parsed.type !== "ping" && parsed.message) {
          setCurrentStatus(parsed.message);
        }

        if (parsed.type === "done") {
          disconnect();
        }
      } catch (e) {
        console.error("Failed to parse SSE event:", e, event.data);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      disconnect();
    };

    eventSourceRef.current = eventSource;
  }, [sessionId]);

  // Verbindung beenden
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  // Cleanup bei unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Status zurücksetzen
  const clearStatus = useCallback(() => {
    setCurrentStatus("");
  }, []);

  return {
    currentStatus,
    isConnected,
    connect,
    disconnect,
    clearStatus,
  };
}
