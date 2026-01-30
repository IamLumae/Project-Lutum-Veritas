/**
 * useBackend Hook
 * ================
 * Kommunikation mit dem FastAPI Backend auf Port 8420.
 */

import { useState, useCallback } from "react";

const BACKEND_URL = "http://127.0.0.1:8420";

/**
 * Übersetzt technische Fehler in benutzerfreundliche Nachrichten.
 */
function getUserFriendlyError(error: unknown): string {
  const msg = error instanceof Error ? error.message : String(error);
  const lowerMsg = msg.toLowerCase();

  // Netzwerk-Fehler
  if (lowerMsg.includes('fetch') || lowerMsg.includes('network') || lowerMsg.includes('failed to fetch')) {
    return 'Verbindung zum Backend fehlgeschlagen. Bitte prüfe ob das Backend läuft.';
  }

  // Timeout
  if (lowerMsg.includes('timeout') || lowerMsg.includes('aborted')) {
    return 'Die Anfrage hat zu lange gedauert. Bitte versuche es erneut.';
  }

  // HTTP Status Codes
  if (lowerMsg.includes('http 401') || lowerMsg.includes('unauthorized')) {
    return 'API-Key ist ungültig. Bitte in den Einstellungen überprüfen.';
  }
  if (lowerMsg.includes('http 403') || lowerMsg.includes('forbidden')) {
    return 'Zugriff verweigert. API-Key hat keine Berechtigung.';
  }
  if (lowerMsg.includes('http 429') || lowerMsg.includes('rate limit')) {
    return 'Zu viele Anfragen. Bitte warte kurz und versuche es dann erneut.';
  }
  if (lowerMsg.includes('http 500') || lowerMsg.includes('internal server')) {
    return 'Backend-Fehler. Bitte versuche es erneut.';
  }
  if (lowerMsg.includes('http 502') || lowerMsg.includes('http 503') || lowerMsg.includes('http 504')) {
    return 'Backend nicht erreichbar. Bitte starte das Backend neu.';
  }

  // API-spezifische Fehler
  if (lowerMsg.includes('api key') || lowerMsg.includes('api_key')) {
    return 'Problem mit dem API-Key. Bitte in den Einstellungen überprüfen.';
  }
  if (lowerMsg.includes('model not found') || lowerMsg.includes('unknown model')) {
    return 'Das Modell wurde nicht gefunden. Bitte prüfe den Modellnamen in den Einstellungen.';
  }
  if (lowerMsg.includes('quota') || lowerMsg.includes('credits')) {
    return 'API-Kontingent aufgebraucht. Bitte API-Key-Guthaben prüfen.';
  }

  // Wenn nichts passt, aber kurze technische Message
  if (msg.length < 100 && !lowerMsg.includes('error')) {
    return msg; // Kurze Messages können durchgereicht werden
  }

  // Fallback für alles andere
  return 'Ein Fehler ist aufgetreten. Bitte versuche es erneut.';
}

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
  source_registry?: Record<number, string>;  // NEU: {1: "url1", 2: "url2", ...} für klickbare Citations
  error: string | null;
}

/** Single Synthesis Block (collapsible in UI) */
export interface SynthesisBlock {
  index: number;
  title: string;
  content: string;
  sources_count: number;
  dossiers_count: number;
}

/** Conclusion Block (always open, orange background) */
export interface ConclusionBlock {
  impact_statement: string;
  content: string;
  title: string;
}

/** Conclusion Metrics */
export interface ConclusionMetrics {
  total_sources: number;
  total_synthese_chars: number;
  total_dossiers: number;
  total_raw_chars: number;
  total_areas: number;
}

/** Academic Research Response (erweitert Deep Research) */
export interface AcademicResearchResponse extends DeepResearchResponse {
  total_bereiche: number;
  // NEW: Structured data for collapsible UI
  syntheses?: SynthesisBlock[];
  conclusion?: ConclusionBlock;
  conclusion_metrics?: ConclusionMetrics;
}

/** Event wenn ein Bereich startet (Academic Mode) */
export interface BereichStartEvent {
  bereichTitle: string;
  bereichNumber: number;
  totalBereiche: number;
  pointsInBereich: number;
}

/** Event wenn ein Bereich abgeschlossen ist (Academic Mode) */
export interface BereichCompleteEvent {
  bereichTitle: string;
  bereichNumber: number;
  totalBereiche: number;
  dossiersCount: number;
  sourcesCount: number;
}

/** Event wenn Meta-Synthese startet (Academic Mode) */
export interface MetaSynthesisStartEvent {
  bereicheCount: number;
  totalSources: number;
}

/** Backend Log Event (WARN/ERROR level) */
export interface LogEvent {
  level: "WARNING" | "ERROR";
  message: string;  // Short version for display
  full: string;     // Full log message
}

export interface ContextState {
  user_query: string;
  clarification_questions: string[];
  clarification_answers: string[];
  research_plan: string[];
  plan_version: number;
  session_title: string;
  current_step: number;
  /** Academic Mode: Hierarchische Bereiche mit Unterpunkten */
  academic_bereiche?: Record<string, string[]>;
}

export interface PlanResponse {
  plan_points: string[];
  plan_text: string;
  context_state: ContextState;
  academic_bereiche?: Record<string, string[]>;  // Academic Mode: Hierarchische Bereiche
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
        const errorMsg = getUserFriendlyError(e);
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
    async (
      message: string,
      apiKey: string,
      sessionId?: string,
      modelSize: string = 'small',
      academicMode: boolean = false,
      provider: string = 'openrouter',
      workModel: string = 'google/gemini-2.5-flash-lite-preview-09-2025',
      baseUrl: string = 'https://openrouter.ai/api/v1/chat/completions'
    ): Promise<OverviewResponse | null> => {
      setState((s) => ({ ...s, loading: true, error: null }));

      try {
        const response = await fetch(`${BACKEND_URL}/research/overview`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message,
            api_key: apiKey,
            session_id: sessionId,
            model_size: modelSize,
            academic_mode: academicMode,
            provider,
            work_model: workModel,
            base_url: baseUrl,
          }),
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
        const errorMsg = getUserFriendlyError(e);
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
      onLog?: (event: LogEvent) => void,
      modelSize: string = 'small',
      academicMode: boolean = false,
      language: string = 'de',
      provider: string = 'openrouter',
      workModel: string = 'google/gemini-2.5-flash-lite-preview-09-2025',
      baseUrl: string = 'https://openrouter.ai/api/v1/chat/completions'
    ): Promise<PipelineResponse | null> => {
      setState((s) => ({ ...s, loading: true, error: null }));

      try {
        const response = await fetch(`${BACKEND_URL}/research/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message,
            api_key: apiKey,
            session_id: sessionId,
            max_step: 3,
            model_size: modelSize,
            academic_mode: academicMode,
            language: language,
            provider,
            work_model: workModel,
            base_url: baseUrl,
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
              } else if (parsed.type === "log" && onLog) {
                // Backend log event (WARN/ERROR)
                onLog({
                  level: parsed.level,
                  message: parsed.message,
                  full: parsed.full,
                });
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
        const errorMsg = getUserFriendlyError(e);
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
      academicMode: boolean = false,
      provider: string = 'openrouter',
      workModel: string = 'google/gemini-2.5-flash-lite-preview-09-2025',
      baseUrl: string = 'https://openrouter.ai/api/v1/chat/completions'
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
            provider,
            work_model: workModel,
            base_url: baseUrl,
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
        const errorMsg = getUserFriendlyError(e);
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
      academicMode: boolean = false,
      provider: string = 'openrouter',
      workModel: string = 'google/gemini-2.5-flash-lite-preview-09-2025',
      baseUrl: string = 'https://openrouter.ai/api/v1/chat/completions'
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
            provider,
            work_model: workModel,
            base_url: baseUrl,
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
        const errorMsg = getUserFriendlyError(e);
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
      onLog?: (event: LogEvent) => void,
      modelSize: string = 'small',
      academicMode: boolean = false,
      provider: string = 'openrouter',
      workModel: string = 'google/gemini-2.5-flash-lite-preview-09-2025',
      finalModel: string = 'qwen/qwen3-vl-235b-a22b-instruct',
      language: string = 'de',
      baseUrl: string = 'https://openrouter.ai/api/v1/chat/completions'
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
            provider,
            work_model: workModel,
            final_model: finalModel,
            language: language,
            base_url: baseUrl,
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
              } else if (parsed.type === "log" && onLog) {
                // Backend log event (WARN/ERROR)
                onLog({
                  level: parsed.level,
                  message: parsed.message,
                  full: parsed.full,
                });
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
        const errorMsg = getUserFriendlyError(e);
        setState((s) => ({ ...s, loading: false, error: errorMsg }));
        return null;
      }
    },
    []
  );

  /**
   * Step 5 Academic: Academic Research Pipeline - STREAMING.
   * Hierarchische Bereiche mit Meta-Synthese am Ende.
   */
  const runAcademicResearch = useCallback(
    async (
      contextState: ContextState & { academic_bereiche?: Record<string, string[]> },
      apiKey: string,
      sessionId?: string,
      onStatus?: (status: string) => void,
      onSources?: (urls: string[]) => void,
      onPointComplete?: (event: PointCompleteEvent) => void,
      onBereichStart?: (event: BereichStartEvent) => void,
      onBereichComplete?: (event: BereichCompleteEvent) => void,
      onMetaSynthesisStart?: (event: MetaSynthesisStartEvent) => void,
      onLog?: (event: LogEvent) => void,
      provider: string = 'openrouter',
      workModel: string = 'google/gemini-2.5-flash-lite-preview-09-2025',
      finalModel: string = 'qwen/qwen3-vl-235b-a22b-instruct',
      language: string = 'de',
      baseUrl: string = 'https://openrouter.ai/api/v1/chat/completions'
    ): Promise<AcademicResearchResponse | null> => {
      setState((s) => ({ ...s, loading: true, error: null }));

      try {
        const response = await fetch(`${BACKEND_URL}/research/academic`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            context_state: contextState,
            api_key: apiKey,
            session_id: sessionId,
            provider,
            work_model: workModel,
            final_model: finalModel,
            language: language,
            base_url: baseUrl,
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
        let result: AcademicResearchResponse | null = null;

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
                // Punkt abgeschlossen
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
              } else if (parsed.type === "bereich_start" && onBereichStart) {
                // Bereich startet
                onBereichStart({
                  bereichTitle: parsed.bereich_title,
                  bereichNumber: parsed.bereich_number,
                  totalBereiche: parsed.total_bereiche,
                  pointsInBereich: parsed.points_in_bereich,
                });
              } else if (parsed.type === "bereich_complete" && onBereichComplete) {
                // Bereich abgeschlossen
                onBereichComplete({
                  bereichTitle: parsed.bereich_title,
                  bereichNumber: parsed.bereich_number,
                  totalBereiche: parsed.total_bereiche,
                  dossiersCount: parsed.dossiers_count,
                  sourcesCount: parsed.sources_count,
                });
              } else if (parsed.type === "meta_synthesis_start" && onMetaSynthesisStart) {
                // Meta-Synthese startet
                onMetaSynthesisStart({
                  bereicheCount: parsed.bereiche_count,
                  totalSources: parsed.total_sources,
                });
                if (onStatus) onStatus(parsed.message);
              } else if (parsed.type === "log" && onLog) {
                // Backend log event (WARN/ERROR)
                onLog({
                  level: parsed.level,
                  message: parsed.message,
                  full: parsed.full,
                });
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
        const errorMsg = getUserFriendlyError(e);
        setState((s) => ({ ...s, loading: false, error: errorMsg }));
        return null;
      }
    },
    []
  );

  // Session Recovery - holt Checkpoint der letzten Session
  const recoverSession = useCallback(async (sessionId?: string): Promise<{
    success: boolean;
    session_id?: string;
    user_query?: string;
    research_plan?: string[];
    completed_dossiers?: Array<{ point: string; dossier: string; sources: string[] }>;
    remaining_points?: string[];
    status?: string;
    error?: string;
  } | null> => {
    try {
      setState((s) => ({ ...s, loading: true, error: null }));

      // Wenn keine sessionId gegeben, hole die neueste
      const url = sessionId
        ? `${BACKEND_URL}/research/session/${sessionId}`
        : `${BACKEND_URL}/research/latest-synthesis`;

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      setState((s) => ({ ...s, loading: false }));

      return result;
    } catch (e) {
      const errorMsg = getUserFriendlyError(e);
      setState((s) => ({ ...s, loading: false, error: errorMsg }));
      return null;
    }
  }, []);

  // Liste aller Sessions holen
  const listSessions = useCallback(async (): Promise<{
    sessions: Array<{
      session_id: string;
      user_query: string;
      status: string;
      completed_dossiers: number;
      total_points: number;
      last_modified: string;
    }>;
  } | null> => {
    try {
      const response = await fetch(`${BACKEND_URL}/research/sessions`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (e) {
      console.error("Failed to list sessions:", e);
      return null;
    }
  }, []);

  // Session fortsetzen - ruft /research/resume auf
  const resumeSession = useCallback(async (
    sessionId: string,
    apiKey: string,
    provider: string = 'openrouter',
    workModel: string = 'google/gemini-2.5-flash-lite-preview-09-2025',
    finalModel: string = 'qwen/qwen3-vl-235b-a22b-instruct',
    onStatus?: (status: string) => void,
    onSources?: (urls: string[]) => void,
    onPointComplete?: (event: PointCompleteEvent) => void,
    onSynthesisStart?: (event: SynthesisStartEvent) => void,
    onLog?: (event: LogEvent) => void,
    baseUrl: string = 'https://openrouter.ai/api/v1/chat/completions'
  ): Promise<DeepResearchResponse | null> => {
    setState((s) => ({ ...s, loading: true, error: null }));

    try {
      const response = await fetch(`${BACKEND_URL}/research/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          api_key: apiKey,
          provider,
          work_model: workModel,
          final_model: finalModel,
          base_url: baseUrl,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Streaming Response verarbeiten (gleich wie runDeepResearch)
      const reader = response.body?.getReader();
      if (!reader) throw new Error("No reader");

      const decoder = new TextDecoder();
      let finalResult: DeepResearchResponse | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n").filter(Boolean);

        for (const line of lines) {
          try {
            const event = JSON.parse(line);

            if (event.type === "status" && onStatus) {
              onStatus(event.message);
            } else if (event.type === "sources" && onSources) {
              onSources(event.urls);
            } else if (event.type === "point_complete" && onPointComplete) {
              onPointComplete(event as PointCompleteEvent);
            } else if (event.type === "synthesis_start" && onSynthesisStart) {
              onSynthesisStart(event as SynthesisStartEvent);
            } else if (event.type === "log" && onLog) {
              // Backend log event (WARN/ERROR)
              onLog({
                level: event.level,
                message: event.message,
                full: event.full,
              });
            } else if (event.type === "done") {
              finalResult = event.data;
            } else if (event.type === "error") {
              throw new Error(event.message);
            }
          } catch {
            // Skip invalid JSON lines
          }
        }
      }

      setState((s) => ({ ...s, loading: false }));
      return finalResult;
    } catch (e) {
      const errorMsg = getUserFriendlyError(e);
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
    runAcademicResearch,
    recoverSession,
    listSessions,
    resumeSession,
  };
}
