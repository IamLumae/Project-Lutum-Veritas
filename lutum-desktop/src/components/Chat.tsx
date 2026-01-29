/**
 * Chat Component
 * ===============
 * Hauptcontainer mit Sidebar + Chat-Bereich.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { Sidebar } from "./Sidebar";
import { MessageList } from "./MessageList";
import { InputBar } from "./InputBar";
import { Settings } from "./Settings";
import { useBackend } from "../hooks/useBackend";
import { initDarkMode, loadSettings } from "../stores/settings";
import {
  SessionsState,
  Session,
  Message,
  ContextState,
  loadSessions,
  saveSessions,
  createSession,
} from "../stores/sessions";
// @ts-ignore
import html2pdf from "html2pdf.js";
import { saveSettings } from "../stores/settings";

export function Chat() {
  // Sessions State
  const [sessionsState, setSessionsState] = useState<SessionsState>(loadSessions);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const { loading, error, connected, checkHealth, runPipeline, createPlan, revisePlan, runDeepResearch, recoverSynthesis } = useBackend();

  // Live-Status vom Streaming (ersetzt SSE)
  const [currentStatus, setCurrentStatus] = useState<string>("");

  // Timer State
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Settings State (Lifted for UI Controls)
  const [modelSize, setModelSize] = useState<'small' | 'large'>('small');
  const [academicMode, setAcademicMode] = useState(false);

  // Init Settings State
  useEffect(() => {
    const s = loadSettings();
    setModelSize(s.modelSize);
    setAcademicMode(s.academicMode);
  }, [settingsOpen]); // Refresh if settings modal changed something

  // Helper: Persist Model Size
  const handleModelChange = (size: 'small' | 'large') => {
    setModelSize(size);
    const s = loadSettings();
    saveSettings({ ...s, modelSize: size });
  };

  // Helper: Persist Academic Mode
  const handleAcademicToggle = () => {
    const newVal = !academicMode;
    setAcademicMode(newVal);
    const s = loadSettings();
    saveSettings({ ...s, academicMode: newVal });
  };

  // EXPORT HANDLERS
  const handleExportMD = () => {
    if (!activeSession?.messages) return;
    const finalMsg = [...activeSession.messages].reverse().find(m => m.role === 'assistant' && !m.type);
    if (!finalMsg) return;

    const blob = new Blob([finalMsg.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeSession.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_synthesis.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = () => {
    // Finde das Element mit der ID "report-content" oder den Container der letzten Message
    // Wir müssen dem ReportRenderer eine ID geben oder hier tricksen.
    // Einfachheitshalber: Wir rendern den Content temporär in ein verstecktes Div für html2pdf

    // Besser: Wir suchen im DOM nach dem gerenderten Report.
    // Da wir MarkdownView/ReportView nutzen, sollten wir dort vielleicht exportieren?
    // User will Button "MD/PDF" im Chat (Header oder Footer?).
    // Der Plan sagt "Header or near final message".
    // Ich nehme den Header.

    const element = document.getElementById('report-container');
    if (!element) {
      alert("Kein Report gefunden zum Exportieren. Bitte warten bis Synthesis fertig ist.");
      return;
    }

    const opt: any = {
      margin: [10, 10],
      filename: `${activeSession?.title || 'report'}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, logging: false },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };

    html2pdf().set(opt).from(element).save();
  };

  // Timer starten/stoppen basierend auf loading
  useEffect(() => {
    if (loading) {
      setElapsedSeconds(0);
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setCurrentStatus("");
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [loading]);

  // Format Timer als MM:SS
  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // Init dark mode on mount
  useEffect(() => {
    initDarkMode();
  }, []);

  // Check backend connection
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  // Save sessions on change
  useEffect(() => {
    saveSessions(sessionsState);
  }, [sessionsState]);

  // Get active session
  const activeSession = sessionsState.sessions.find(
    (s) => s.id === sessionsState.activeSessionId
  );

  // Convert stored messages to display format
  const displayMessages = (activeSession?.messages || []).map((m) => ({
    ...m,
    timestamp: new Date(m.timestamp),
    loading: false,
  }));

  // Session handlers
  const handleNewSession = useCallback(() => {
    const newSession = createSession();
    setSessionsState((prev) => ({
      sessions: [newSession, ...prev.sessions],
      activeSessionId: newSession.id,
    }));
  }, []);

  const handleSelectSession = useCallback((id: string) => {
    setSessionsState((prev) => ({
      ...prev,
      activeSessionId: id,
    }));
  }, []);

  const handleDeleteSession = useCallback((id: string) => {
    setSessionsState((prev) => {
      const newSessions = prev.sessions.filter((s) => s.id !== id);

      // If deleting active session, switch to another or null
      let newActiveId = prev.activeSessionId;
      if (id === prev.activeSessionId) {
        newActiveId = newSessions.length > 0 ? newSessions[0].id : null;
      }

      return {
        sessions: newSessions,
        activeSessionId: newActiveId,
      };
    });
  }, []);

  const handleRenameSession = useCallback((id: string, newTitle: string) => {
    setSessionsState((prev) => ({
      ...prev,
      sessions: prev.sessions.map((s) =>
        s.id === id ? { ...s, title: newTitle, updatedAt: new Date().toISOString() } : s
      ),
    }));
  }, []);

  // Helper: Session updaten
  const updateSession = useCallback((id: string, updates: Partial<Session>) => {
    setSessionsState((prev) => ({
      ...prev,
      sessions: prev.sessions.map((s) =>
        s.id === id ? { ...s, ...updates, updatedAt: new Date().toISOString() } : s
      ),
    }));
  }, []);

  // Helper: Message zur Session hinzufügen
  const addMessage = useCallback((sessionId: string, msg: Message) => {
    setSessionsState((prev) => ({
      ...prev,
      sessions: prev.sessions.map((s) =>
        s.id === sessionId
          ? { ...s, messages: [...s.messages, msg], updatedAt: new Date().toISOString() }
          : s
      ),
    }));
  }, []);

  // Send message handler - Phase-basiert
  const handleSend = useCallback(
    async (content: string) => {
      // Auto-create Session wenn keine existiert
      let sessionId = sessionsState.activeSessionId;
      let session = activeSession;

      if (!sessionId) {
        const newSession = createSession();
        setSessionsState((prev) => ({
          sessions: [newSession, ...prev.sessions],
          activeSessionId: newSession.id,
        }));
        sessionId = newSession.id;
        session = newSession;
      }

      if (!sessionId || !session) return;

      const now = new Date().toISOString();
      const phase = session.phase || "initial";

      // Create user message
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: now,
      };
      addMessage(sessionId, userMsg);

      // === PHASE: INITIAL → Pipeline Step 1-3 ===
      if (phase === "initial") {
        updateSession(sessionId, { title: "Recherche läuft...", phase: "clarifying" });

        // Pipeline mit Status-Callback für Live-Updates und Sources-Callback für URLs
        const settings = loadSettings();
        const pipelineResult = await runPipeline(
          content,
          settings.apiKey,
          sessionId,
          (status) => {
            setCurrentStatus(status);
          },
          (urls) => {
            // Sources Message erstellen wenn URLs gefunden werden
            const sourcesMsg: Message = {
              id: crypto.randomUUID(),
              role: "assistant",
              content: `Ich habe ${urls.length} relevanten Quellen gefunden:`,
              timestamp: new Date().toISOString(),
              type: "sources",
              sources: urls,
            };
            addMessage(sessionId, sourcesMsg);
          },
          modelSize,
          academicMode
        );

        // Session-Titel vom LLM
        if (pipelineResult?.session_title) {
          updateSession(sessionId, { title: pipelineResult.session_title });
        }

        // Assistant Message mit Rückfragen
        const responseText = pipelineResult?.response || pipelineResult?.error || "Fehler bei der Recherche";
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: responseText,
          timestamp: new Date().toISOString(),
        };
        addMessage(sessionId, assistantMsg);

        // Context State initialisieren für Step 4
        const contextState: ContextState = {
          user_query: content,
          clarification_questions: [], // Werden aus Response geparst wenn nötig
          clarification_answers: [],
          research_plan: [],
          plan_version: 0,
          session_title: pipelineResult?.session_title || "",
          current_step: 3,
        };
        updateSession(sessionId, { contextState, phase: "clarifying" });
      }

      // === PHASE: CLARIFYING → Plan erstellen (Step 4) ===
      else if (phase === "clarifying") {
        const ctx = session.contextState;
        if (!ctx) return;

        const settings = loadSettings();
        const planResult = await createPlan(
          ctx.user_query,
          ctx.clarification_questions,
          [content],
          settings.apiKey,
          sessionId,
          modelSize,
          academicMode
        );

        if (planResult?.plan_points && planResult.plan_points.length > 0) {
          // Plan-Message mit speziellem Typ
          const planMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: `**Recherche-Plan erstellt:**\n\n${planResult.plan_text}\n\n_Sag mir, falls ich ihn ändern soll._`,
            timestamp: new Date().toISOString(),
            type: "plan",
          };
          addMessage(sessionId, planMsg);

          // Context State mit Plan updaten
          updateSession(sessionId, {
            contextState: planResult.context_state,
            phase: "planning",
          });
        } else {
          // Fehler
          const errorMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: planResult?.error || "Plan konnte nicht erstellt werden.",
            timestamp: new Date().toISOString(),
          };
          addMessage(sessionId, errorMsg);
        }
      }

      // === PHASE: PLANNING → Plan bearbeiten ===
      else if (phase === "planning") {
        const ctx = session.contextState;
        if (!ctx) return;

        // User will Plan ändern
        const settings = loadSettings();
        const reviseResult = await revisePlan(ctx, content, settings.apiKey, sessionId, modelSize, academicMode);

        if (reviseResult?.plan_points && reviseResult.plan_points.length > 0) {
          const planMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: `**Recherche-Plan überarbeitet (v${reviseResult.context_state.plan_version}):**\n\n${reviseResult.plan_text}\n\n_Sag mir, falls ich ihn noch ändern soll._`,
            timestamp: new Date().toISOString(),
            type: "plan",
          };
          addMessage(sessionId, planMsg);
          updateSession(sessionId, { contextState: reviseResult.context_state });
        } else {
          const errorMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: reviseResult?.error || "Plan konnte nicht überarbeitet werden.",
            timestamp: new Date().toISOString(),
          };
          addMessage(sessionId, errorMsg);
        }
      }
    },
    [sessionsState.activeSessionId, activeSession, runPipeline, createPlan, revisePlan, updateSession, addMessage]
  );

  // Handler: "Los geht's" Button → Deep Research starten
  const handleStartResearch = useCallback(async () => {
    if (!activeSession || !activeSession.contextState) return;

    const sessionId = activeSession.id;
    const ctx = activeSession.contextState;

    // Phase auf "researching" setzen
    updateSession(sessionId, { phase: "researching" });

    // Start-Message
    const startMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: `**Deep Research gestartet**\n\nIch arbeite jetzt ${ctx.research_plan.length} Punkte ab. Das kann einige Minuten dauern.\n\n_Du siehst nach jedem Punkt die Erkenntnisse._`,
      timestamp: new Date().toISOString(),
    };
    addMessage(sessionId, startMsg);

    // Deep Research ausführen
    const settings = loadSettings();
    const result = await runDeepResearch(
      ctx,
      settings.apiKey,
      sessionId,
      // onStatus: Live-Status-Updates
      (status) => {
        setCurrentStatus(status);
      },
      // onSources: Quellen-Box für jeden Punkt
      (urls) => {
        const sourcesMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Analysiere ${urls.length} Quellen...`,
          timestamp: new Date().toISOString(),
          type: "sources",
          sources: urls,
        };
        addMessage(sessionId, sourcesMsg);
      },
      // onPointComplete: Key Learnings nach jedem Punkt
      (event) => {
        const pointMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: event.keyLearnings,
          timestamp: new Date().toISOString(),
          type: "point_summary",
          pointTitle: event.pointTitle,
          pointNumber: event.pointNumber,
          totalPoints: event.totalPoints,
          dossierFull: event.dossierFull,
          skipped: event.skipped,
          skipReason: event.skipReason,
        };
        addMessage(sessionId, pointMsg);
      },
      // onSynthesisStart: Final Synthesis beginnt (lange Wartezeit)
      (event) => {
        const synthMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `**Final Synthesis startet**\n\nKombiniere ${event.dossierCount} Dossiers aus ${event.totalSources} Quellen.\nGeschätzte Dauer: ~${event.estimatedMinutes} Minuten.\n\n_Bitte nicht schließen - das dauert einen Moment._`,
          timestamp: new Date().toISOString(),
          type: "synthesis_waiting",
          estimatedMinutes: event.estimatedMinutes,
        };
        addMessage(sessionId, synthMsg);
      },
      modelSize,
      academicMode
    );

    // Finale Response
    if (result?.final_document) {
      const finalMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.final_document,
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, finalMsg);

      // Summary Message
      const summaryMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `**Recherche abgeschlossen**\n\n- ${result.total_points} Punkte bearbeitet\n- ${result.total_sources} Quellen analysiert\n- Dauer: ${Math.round(result.duration_seconds / 60)} Minuten`,
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, summaryMsg);

      updateSession(sessionId, { phase: "done" });
    } else if (result?.error) {
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `**Fehler bei der Recherche:**\n\n${result.error}`,
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, errorMsg);
      updateSession(sessionId, { phase: "planning" }); // Zurück zu Planning
    }
  }, [activeSession, runDeepResearch, updateSession, addMessage]);

  // Handler: "Plan bearbeiten" Button → User kann Änderungen eingeben
  const handleEditPlan = useCallback(() => {
    if (!activeSession) return;

    // Prompt-Message dass User seine Änderungswünsche eingeben soll
    const promptMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "Was möchtest du am Plan ändern? Beschreibe deine Änderungswünsche:",
      timestamp: new Date().toISOString(),
    };
    addMessage(activeSession.id, promptMsg);

    // Phase auf "clarifying" setzen damit nächste User-Message den Plan überarbeitet
    // Aber wir brauchen einen Marker dass es um Plan-Bearbeitung geht
    updateSession(activeSession.id, { phase: "planning" }); // Bleibt in planning, handleSend prüft das
  }, [activeSession, addMessage, updateSession]);

  // Handler: "Synthesis laden" Button → Holt letzte Synthesis aus Backup
  const handleRecoverSynthesis = useCallback(async () => {
    if (!activeSession) return;

    const sessionId = activeSession.id;

    // Status-Message
    const loadingMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "🔄 Lade letzte Synthesis aus Backup...",
      timestamp: new Date().toISOString(),
    };
    addMessage(sessionId, loadingMsg);

    const result = await recoverSynthesis();

    if (result?.success && result.final_document) {
      // Finale Response als Message
      const finalMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.final_document,
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, finalMsg);

      // Success Message
      const successMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `✅ **Synthesis erfolgreich wiederhergestellt**\n\nQuelle: \`${result.filename}\``,
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, successMsg);

      updateSession(sessionId, { phase: "done" });
    } else {
      // Error Message
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `❌ **Synthesis konnte nicht geladen werden**\n\n${result?.error || "Unbekannter Fehler"}`,
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, errorMsg);
    }
  }, [activeSession, recoverSynthesis, addMessage, updateSession]);

  return (
    <div className="h-screen flex bg-[var(--bg-primary)] overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        sessions={sessionsState.sessions}
        activeSessionId={sessionsState.activeSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
          <div className="flex items-center gap-3">
            <h1 className="text-[var(--text-primary)] font-semibold">
              {activeSession?.title || "Lutum Veritas"}
            </h1>
            {/* Timer + Status während Recherche */}
            {loading && (
              <div className="flex items-center gap-2">
                <span className="text-[var(--accent)] text-sm font-mono">
                  ⏱ {formatTimer(elapsedSeconds)}
                </span>
                {currentStatus && (
                  <span className="text-[var(--text-secondary)] text-sm animate-pulse">
                    {currentStatus}
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Model Selector */}
            <select
              value={modelSize}
              onChange={(e) => handleModelChange(e.target.value as 'small' | 'large')}
              className="bg-[var(--bg-tertiary)] text-[var(--text-secondary)] text-sm border border-[var(--border)] rounded-md px-2 py-1 focus:outline-none focus:border-blue-500"
              title="Modell-Größe wählen"
            >
              <option value="small">Small (Fast)</option>
              <option value="large">Large (Deep)</option>
            </select>

            {/* Academic Toggle */}
            <button
              onClick={handleAcademicToggle}
              className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-sm transition-colors ${academicMode
                ? "bg-blue-900/30 border-blue-700 text-blue-300"
                : "bg-transparent border-transparent text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
                }`}
              title="Academic Mode"
            >
              <span className={`w-2 h-2 rounded-full ${academicMode ? "bg-blue-400" : "bg-gray-600"}`} />
              Academic
            </button>

            {/* Export Buttons */}
            {activeSession?.phase === 'done' && (
              <div className="flex items-center gap-1 border-l border-[var(--border)] pl-3 mr-2">
                <button
                  onClick={handleExportMD}
                  className="p-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-tertiary)] rounded"
                  title="Export Markdown"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
                </button>
                <button
                  onClick={handleExportPDF}
                  className="p-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-tertiary)] rounded"
                  title="Export PDF"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" /></svg>
                </button>
              </div>
            )}

            {/* Connection Status */}
            <div className="flex items-center gap-1">
              <div
                className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"
                  }`}
              />
              <span className="text-[var(--text-secondary)] text-sm">
                {connected ? "Verbunden" : "Offline"}
              </span>
            </div>

            {/* Settings Button */}
            <button
              onClick={() => setSettingsOpen(true)}
              className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors p-2"
              title="Einstellungen"
            >
              ⚙️
            </button>
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-900/50 text-red-200 px-4 py-2 text-sm">
            {error}
          </div>
        )}

        {/* Messages */}
        <MessageList
          messages={displayMessages}
          loading={loading}
          onStartResearch={handleStartResearch}
          onEditPlan={handleEditPlan}
          onRecoverSynthesis={handleRecoverSynthesis}
          showPlanButtons={activeSession?.phase === "planning"}
          showRecoveryButton={activeSession?.phase === "researching" && !loading}
          currentStatus={currentStatus}
        />

        {/* Input */}
        <InputBar onSend={handleSend} disabled={loading || !connected} />
      </div>

      {/* Settings Modal */}
      <Settings isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
