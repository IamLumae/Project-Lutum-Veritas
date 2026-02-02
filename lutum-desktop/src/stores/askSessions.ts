/**
 * Ask Sessions Store
 * ==================
 * Verwaltet Ask Mode Sessions (Q&A history, persistence).
 */

const STORAGE_KEY = "lutum-ask-sessions";

export interface AskMessage {
  id: string;
  role: "user" | "system";
  content: string;
  timestamp: string;
  /** Message type for different rendering */
  type?: "user_question" | "stage_update" | "scrape_progress" | "answer" | "verification";
  /** Stage identifier (C1-C6) */
  stage?: string;
  /** Sources for citations [1], [2], etc. */
  sourceRegistry?: Record<number, string>;
  /** Progress info for scraping */
  progress?: { done: number; total: number };
  /** Verification data (embedded in answer message) */
  verification?: {
    content: string;
    sourceRegistry?: Record<number, string>;
  };
}

export interface AskSession {
  id: string;
  question: string; // Truncated for display
  questionFull: string; // Full question text
  messages: AskMessage[];
  createdAt: string;
  completedAt?: string;
  durationSeconds?: number;
}

export interface AskSessionsState {
  sessions: AskSession[];
  activeSessionId: string | null;
}

/**
 * Creates new Ask session.
 * If no question provided, uses default "New Question" placeholder.
 */
export function createAskSession(question?: string): AskSession {
  const now = new Date().toISOString();
  const defaultQuestion = "Neue Frage"; // Will be replaced when user types
  const actualQuestion = question || defaultQuestion;
  const truncated = actualQuestion.length > 60 ? actualQuestion.substring(0, 57) + "..." : actualQuestion;
  return {
    id: crypto.randomUUID(),
    question: truncated,
    questionFull: actualQuestion,
    messages: [],
    createdAt: now,
  };
}

/**
 * Loads Ask sessions from localStorage.
 */
export function loadAskSessions(): AskSessionsState {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const state = JSON.parse(stored) as AskSessionsState;
      if (state.sessions && Array.isArray(state.sessions)) {
        console.log(`[AskSessions] Loaded ${state.sessions.length} Ask sessions from localStorage`);
        return state;
      }
    }
  } catch (e) {
    console.error("Failed to load Ask sessions:", e);
  }

  return {
    sessions: [],
    activeSessionId: null,
  };
}

/**
 * Saves Ask sessions to localStorage.
 */
export function saveAskSessions(state: AskSessionsState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    console.error("Failed to save Ask sessions:", e);
  }
}

/**
 * Clears all Ask sessions.
 */
export function clearAllAskSessions(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Formats relative timestamp (2m ago, 1h ago, etc.)
 */
export function formatRelativeTime(isoTimestamp: string, lang: 'de' | 'en'): string {
  const now = Date.now();
  const then = new Date(isoTimestamp).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return lang === 'de' ? 'Gerade eben' : 'Just now';
  if (diffMin < 60) return lang === 'de' ? `vor ${diffMin}m` : `${diffMin}m ago`;
  if (diffHour < 24) return lang === 'de' ? `vor ${diffHour}h` : `${diffHour}h ago`;
  if (diffDay < 7) return lang === 'de' ? `vor ${diffDay}d` : `${diffDay}d ago`;

  // Older: show date
  const date = new Date(isoTimestamp);
  return date.toLocaleDateString(lang === 'de' ? 'de-DE' : 'en-US', { month: 'short', day: 'numeric' });
}
