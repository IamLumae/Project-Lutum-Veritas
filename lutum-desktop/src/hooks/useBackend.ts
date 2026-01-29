/**
 * useBackend Hook
 * ================
 * Kommunikation mit dem FastAPI Backend auf Port 8420.
 */

import { useState, useCallback } from "react";

const BACKEND_URL = "http://127.0.0.1:8420";

export interface ChatResponse {
  response: string;
  url_scraped: string | null;
  chars_scraped: number | null;
  error: string | null;
}

export interface OverviewResponse {
  session_title: string;
  queries_initial: string[];
  raw_response: string | null;
  error: string | null;
}

export interface PipelineResponse {
  session_title: string;
  response: string;
  queries_count: number;
  urls_count: number;
  scraped_count: number;
  error: string | null;
}

/** Event wenn ein Recherche-Punkt abgeschlossen ist */
export interface PointCompleteEvent {
  pointTitle: string;
  pointNumber: number;
  totalPoints: number;
  keyLearnings: string;
  dossierFull?: string;  // Volles Dossier für "Mehr anzeigen"
  sources: string[];
  skipped?: boolean;  // Punkt wurde übersprungen
  skipReason?: string;  // Grund für Überspringen
}

/** Event wenn Final Synthesis startet (lange Wartezeit) */
export interface SynthesisStartEvent {
  estimatedMinutes: number;
  dossierCount: number;
  totalSources: number;
}

/** Deep Research Response */
export interface DeepResearchResponse {
  final_document: string;
  total_points: number;
  total_sources: number;
  duration_seconds: number;
  error: string | null;
}

export interface ContextState {
  user_query: string;
  clarification_questions: string[];
  clarification_answers: string[];
  research_plan: string[];
  plan_version: number;
  session_title: string;
  current_step: number;
}

export interface PlanResponse {
  plan_points: string[];
  plan_text: string;
  context_state: ContextState;
  error: string | null;
}

export interface BackendState {
  loading: boolean;
  error: string | null;
  connected: boolean;
}

/**
 * Hook für Backend-Kommunikation.
 */
export function useBackend() {
  const [state, setState] = useState<BackendState>({
    loading: false,
    error: null,
    connected: false,
  });

  /**
   * Health Check - prüft ob Backend erreichbar.
   */
  const checkHealth = useCallback(async (): Promise<boolean> => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // 3s timeout

      const response = await fetch(`${BACKEND_URL}/health`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        setState((s) => ({ ...s, connected: true, error: null }));
        return true;
      }

      setState((s) => ({ ...s, connected: false, error: "Backend not responding" }));
      return false;
    } catch (e) {
      setState((s) => ({
        ...s,
        connected: false,
        error: null, // Kein Error anzeigen wenn Backend einfach nicht läuft
      }));
      return false;
    }
  }, []);

  /**
   * Sendet Chat-Nachricht an Backend.
   */
  const sendMessage = useCallback(
    async (
      message: string,
      apiKey?: string,
      maxIterations?: number
    ): Promise<ChatResponse | null> => {
      setState((s) => ({ ...s, loading: true, error: null }));

      try {
        const response = await fetch(`${BACKEND_URL}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message,
            api_key: apiKey || null,
            max_iterations: maxIterations || 5,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data: ChatResponse = await response.json();

        setState((s) => ({ ...s, loading: false, connected: true }));

        if (data.error) {
          setState((s) => ({ ...s, error: data.error }));
        }

        return data;
      } catch (e) {
        const errorMsg = e instanceof Error ? e.message : "Unknown error";
        setState((s) => ({ ...s, loading: false, error: errorMsg }));
        return null;
      }
    },
    []
  );

  /**
   * Startet Research Pipeline (Step 1: Overview).
   * Gibt session_title zurück für Session-Benennung.
   */
  const startResearch = useCallback(
    async (message: string, apiKey: string, sessionId?: string, modelSize: string = 'small', academicMode: boolean = false): Promise<OverviewResponse | null> => {
      setState((s) => ({ ...s, loading: true, error: null }));

      try {
        const response = await fetch(`${BACKEND_URL}/research/overview`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, api_key: apiKey, session_id: sessionId, model_size: modelSize, academic_mode: academicMode }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data: OverviewResponse = await response.json();

        setState((s) => ({ ...s, loading: false, connected: true }));

        if (data.error) {
          setState((s) => ({ ...s, error: data.error }));
        }

        return data;
      } catch (e) {
        const errorMsg = e instanceof Error ? e.message : "Unknown error";
        setState((s) => ({ ...s, loading: false, error: errorMsg }));
        return null;
      }
    },
    []
  );

  /**
   * Führt vollständige Research Pipeline aus (Step 1-3) - STREAMING.
   * Ruft onStatus für Status-Messages und onSources für gefundene URLs auf.
   */
  const runPipeline = useCallback(
    async (
      message: string,
      apiKey: string,
      sessionId?: string,
      onStatus?: (status: string) => void,
      onSources?: (urls: string[]) => void,
      modelSize: string = 'small',
      academicMode: boolean = false
    ): Promise<PipelineResponse | null> => {
      setState((s) => ({ ...s, loading: true, error: null }));

      try {
        const response = await fetch(`${BACKEND_URL}/research/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, api_key: apiKey, session_id: sessionId, max_step: 3, model_size: modelSize, academic_mode: academicMode }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        // Stream lesen
        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let result: PipelineResponse | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value, { stream: true });
          const lines = text.split("\n").filter((l) => l.trim());

          for (const line of lines) {
            try {
              const parsed = JSON.parse(line);

              if (parsed.type === "status" && onStatus) {
                onStatus(parsed.message);
              } else if (parsed.type === "sources" && onSources && parsed.urls) {
                // Sources Event: URLs an Frontend melden
                onSources(parsed.urls);
                if (onStatus) onStatus(parsed.message);
              } else if (parsed.type === "done") {
                result = parsed.data;
              } else if (parsed.type === "error") {
                throw new Error(parsed.message);
              }
            } catch (parseErr) {
              console.warn("Failed to parse stream line:", line);
            }
          }
        }

        setState((s) => ({ ...s, loading: false, connected: true }));

        if (result?.error) {
          setState((s) => ({ ...s, error: result.error }));
        }

        return result;
      } catch (e) {
        const errorMsg = e instanceof Error ? e.message : "Unknown error";
        setState((s) => ({ ...s, loading: false, error: errorMsg }));
        return null;
      }
    },
    []
  );

  /**
   * Step 4: Erstellt Recherche-Plan aus User-Antworten.
   */
  const createPlan = useCallback(
    async (
      userQuery: string,
      clarificationQuestions: string[],
      clarificationAnswers: string[],
      apiKey: string,
      sessionId?: string,
      modelSize: string = 'small',
      academicMode: boolean = false
    ): Promise<PlanResponse | null> => {
      setState((s) => ({ ...s, loading: true, error: null }));

      try {
        const response = await fetch(`${BACKEND_URL}/research/plan`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_query: userQuery,
            clarification_questions: clarificationQuestions,
            clarification_answers: clarificationAnswers,
            api_key: apiKey,
            session_id: sessionId,
            model_size: modelSize,
            academic_mode: academicMode,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data: PlanResponse = await response.json();

        setState((s) => ({ ...s, loading: false, connected: true }));

        if (data.error) {
          setState((s) => ({ ...s, error: data.error }));
        }

        return data;
      } catch (e) {
        const errorMsg = e instanceof Error ? e.message : "Unknown error";
        setState((s) => ({ ...s, loading: false, error: errorMsg }));
        return null;
      }
    },
    []
  );

  /**
   * Plan überarbeiten basierend auf User-Feedback.
   */
  const revisePlan = useCallback(
    async (
      contextState: ContextState,
      feedback: string,
      apiKey: string,
      sessionId?: string,
      modelSize: string = 'small',
      academicMode: boolean = false
    ): Promise<PlanResponse | null> => {
      setState((s) => ({ ...s, loading: true, error: null }));

      try {
        const response = await fetch(`${BACKEND_URL}/research/plan/revise`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            context_state: contextState,
            feedback,
            api_key: apiKey,
            session_id: sessionId,
            model_size: modelSize,
            academic_mode: academicMode,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data: PlanResponse = await response.json();

        setState((s) => ({ ...s, loading: false, connected: true }));

        if (data.error) {
          setState((s) => ({ ...s, error: data.error }));
        }

        return data;
      } catch (e) {
        const errorMsg = e instanceof Error ? e.message : "Unknown error";
        setState((s) => ({ ...s, loading: false, error: errorMsg }));
        return null;
      }
    },
    []
  );

  /**
   * Step 5: Deep Research Pipeline - STREAMING.
   * "Don't hide the sweat" - User sieht jeden abgeschlossenen Punkt.
   */
  const runDeepResearch = useCallback(
    async (
      contextState: ContextState,
      apiKey: string,
      sessionId?: string,
      onStatus?: (status: string) => void,
      onSources?: (urls: string[]) => void,
      onPointComplete?: (event: PointCompleteEvent) => void,
      onSynthesisStart?: (event: SynthesisStartEvent) => void,
      modelSize: string = 'small',
      academicMode: boolean = false,
      workModel: string = 'google/gemini-2.5-flash-preview-05-20',
      finalModel: string = 'anthropic/claude-sonnet-4'
    ): Promise<DeepResearchResponse | null> => {
      setState((s) => ({ ...s, loading: true, error: null }));

      try {
        const response = await fetch(`${BACKEND_URL}/research/deep`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            context_state: contextState,
            api_key: apiKey,
            session_id: sessionId,
            model_size: modelSize,
            academic_mode: academicMode,
            work_model: workModel,
            final_model: finalModel,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        // Stream lesen
        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let result: DeepResearchResponse | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value, { stream: true });
          const lines = text.split("\n").filter((l) => l.trim());

          for (const line of lines) {
            try {
              const parsed = JSON.parse(line);

              if (parsed.type === "status" && onStatus) {
                onStatus(parsed.message);
              } else if (parsed.type === "sources" && onSources && parsed.urls) {
                onSources(parsed.urls);
                if (onStatus) onStatus(parsed.message);
              } else if (parsed.type === "point_complete" && onPointComplete) {
                // Punkt abgeschlossen - Key Learnings + volles Dossier an UI
                onPointComplete({
                  pointTitle: parsed.point_title,
                  pointNumber: parsed.point_number,
                  totalPoints: parsed.total_points,
                  keyLearnings: parsed.key_learnings,
                  dossierFull: parsed.dossier_full,
                  sources: parsed.sources || [],
                  skipped: parsed.skipped || false,
                  skipReason: parsed.skip_reason,
                });
              } else if (parsed.type === "synthesis_start" && onSynthesisStart) {
                // Final Synthesis startet - lange Wartezeit
                onSynthesisStart({
                  estimatedMinutes: parsed.estimated_minutes,
                  dossierCount: parsed.dossier_count,
                  totalSources: parsed.total_sources,
                });
                if (onStatus) onStatus(parsed.message);
              } else if (parsed.type === "done") {
                result = parsed.data;
              } else if (parsed.type === "error") {
                throw new Error(parsed.message);
              }
            } catch (parseErr) {
              console.warn("Failed to parse stream line:", line);
            }
          }
        }

        setState((s) => ({ ...s, loading: false, connected: true }));

        if (result?.error) {
          setState((s) => ({ ...s, error: result.error }));
        }

        return result;
      } catch (e) {
        const errorMsg = e instanceof Error ? e.message : "Unknown error";
        setState((s) => ({ ...s, loading: false, error: errorMsg }));
        return null;
      }
    },
    []
  );

  // Synthesis Recovery - holt letzte gespeicherte Synthesis wenn SSE fehlgeschlagen
  const recoverSynthesis = useCallback(async (): Promise<{
    success: boolean;
    final_document?: string;
    filename?: string;
    error?: string;
  } | null> => {
    try {
      setState((s) => ({ ...s, loading: true, error: null }));

      const response = await fetch(`${BACKEND_URL}/research/latest-synthesis`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      setState((s) => ({ ...s, loading: false }));

      return result;
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : "Unknown error";
      setState((s) => ({ ...s, loading: false, error: errorMsg }));
      return null;
    }
  }, []);

  return {
    ...state,
    checkHealth,
    sendMessage,
    startResearch,
    runPipeline,
    createPlan,
    revisePlan,
    runDeepResearch,
    recoverSynthesis,
  };
}
