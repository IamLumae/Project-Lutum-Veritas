/**
 * Sessions Store
 * ===============
 * Verwaltet Chat Sessions (History, Active Session, Persistence).
 */

const STORAGE_KEY = "lutum-sessions";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string; // ISO string für JSON serialization
  url?: string;
  /** Spezial-Typ für verschiedene Anzeigen */
  type?: "text" | "plan" | "sources" | "point_summary" | "synthesis_waiting";
  /** URLs für sources-Typ (aufklappbare Quellen-Box) */
  sources?: string[];
  /** Punkt-Titel für point_summary-Typ */
  pointTitle?: string;
  /** Punkt-Nummer für point_summary-Typ */
  pointNumber?: number;
  /** Total Punkte für Fortschrittsanzeige */
  totalPoints?: number;
  /** Volles Dossier für "Mehr anzeigen" */
  dossierFull?: string;
  /** Punkt wurde übersprungen */
  skipped?: boolean;
  /** Grund für Überspringen */
  skipReason?: string;
  /** Geschätzte Minuten für Synthesis */
  estimatedMinutes?: number;
}

/** Recherche-Phase einer Session */
export type SessionPhase =
  | "initial"      // Noch keine Nachricht
  | "clarifying"   // Rückfragen gestellt, warte auf User-Antworten
  | "planning"     // Plan angezeigt, warte auf "Los geht's" oder "Bearbeiten"
  | "researching"  // Deep Research läuft
  | "done";        // Fertig

/** Context State für Step 4+ */
export interface ContextState {
  user_query: string;
  clarification_questions: string[];
  clarification_answers: string[];
  research_plan: string[];
  plan_version: number;
  session_title: string;
  current_step: number;
}

export interface Session {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
  /** Aktuelle Recherche-Phase */
  phase: SessionPhase;
  /** Context State für Plan-Flow */
  contextState?: ContextState;
}

export interface SessionsState {
  sessions: Session[];
  activeSessionId: string | null;
}

/**
 * Erstellt neue leere Session.
 */
export function createSession(): Session {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: "Neue Recherche",
    messages: [],
    createdAt: now,
    updatedAt: now,
    phase: "initial",
  };
}

/**
 * Lädt Sessions aus localStorage.
 * Version 2: Leerer Default-State erlaubt.
 * Version 3: Phase-Support mit Backward-Compatibility.
 * Version 4: ContextState und Message-Types werden korrekt migriert.
 */
export function loadSessions(): SessionsState {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const state = JSON.parse(stored) as SessionsState;
      // Validierung - sessions muss Array sein, activeSessionId kann null sein
      if (state.sessions && Array.isArray(state.sessions)) {
        // Backward-Compatibility + Vollständige Migration
        const migratedSessions = state.sessions.map((s) => {
          // Phase bestimmen (Backward-Compat + Intelligentes Fallback)
          let phase = s.phase;
          if (!phase) {
            // Wenn kein phase aber contextState mit Plan → planning
            if ((s.contextState?.research_plan?.length ?? 0) > 0) {
              phase = "planning";
            } else if (s.messages.length > 0) {
              phase = "clarifying";
            } else {
              phase = "initial";
            }
          }

          // Messages migrieren (type + sources erhalten)
          const migratedMessages = (s.messages || []).map((m) => ({
            ...m,
            type: m.type || "text",
          }));

          return {
            ...s,
            phase,
            messages: migratedMessages,
            // contextState bleibt wie es ist (wenn vorhanden)
            contextState: s.contextState,
          };
        }) as Session[];

        // Wichtig: activeSessionId auf null setzen wenn Session nicht existiert
        const validActiveId = migratedSessions.some(s => s.id === state.activeSessionId)
          ? state.activeSessionId
          : (migratedSessions.length > 0 ? migratedSessions[0].id : null);

        console.log(`[Sessions] Loaded ${migratedSessions.length} sessions from localStorage`);

        return {
          sessions: migratedSessions,
          activeSessionId: validActiveId,
        };
      }
    }
  } catch (e) {
    console.error("Failed to load sessions:", e);
  }

  // Default: LEER - keine Sessions, nur "Neue Recherche" Button
  return {
    sessions: [],
    activeSessionId: null,
  };
}

/**
 * Löscht alle Sessions (Reset).
 */
export function clearAllSessions(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Speichert Sessions in localStorage.
 */
export function saveSessions(state: SessionsState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    console.error("Failed to save sessions:", e);
  }
}

/**
 * Generiert Session Title aus erster User Message.
 */
export function generateSessionTitle(message: string): string {
  const maxLength = 40;
  const cleaned = message.trim().replace(/\s+/g, " ");
  if (cleaned.length <= maxLength) {
    return cleaned;
  }
  return cleaned.substring(0, maxLength - 3) + "...";
}
