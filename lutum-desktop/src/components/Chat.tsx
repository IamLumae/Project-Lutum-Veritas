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
import { saveSettings } from "../stores/settings";
import { save } from "@tauri-apps/plugin-dialog";
import { writeTextFile, writeFile } from "@tauri-apps/plugin-fs";
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

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

  // Helper: Persist Academic Mode
  const handleAcademicToggle = () => {
    const newVal = !academicMode;
    setAcademicMode(newVal);
    const s = loadSettings();
    saveSettings({ ...s, academicMode: newVal });
  };

  // EXPORT HANDLERS - Using Tauri native APIs
  const handleExportMD = async () => {
    if (!activeSession?.messages) {
      alert("Keine Session aktiv.");
      return;
    }

    if (activeSession.phase !== 'done') {
      alert(`Export nur möglich wenn Recherche abgeschlossen ist.\nAktueller Status: ${activeSession.phase}`);
      return;
    }

    // Finde die LÄNGSTE Assistant-Message (das ist die Synthesis, nicht die Summary)
    const assistantMessages = activeSession.messages.filter(
      m => m.role === 'assistant' && (!m.type || m.type === 'text')
    );

    if (assistantMessages.length === 0) {
      alert("Keine exportierbare Nachricht gefunden.");
      return;
    }

    // Die längste Message ist die Synthesis
    const finalMsg = assistantMessages.reduce((longest, current) =>
      current.content.length > longest.content.length ? current : longest
    );

    try {
      // Tauri Save Dialog
      const filePath = await save({
        filters: [{ name: 'Markdown', extensions: ['md'] }],
        defaultPath: `${activeSession.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_synthesis.md`
      });

      if (filePath) {
        await writeTextFile(filePath, finalMsg.content);
        alert("Markdown erfolgreich exportiert!");
      }
    } catch (err) {
      alert(`Export fehlgeschlagen: ${err}`);
    }
  };

  const handleExportPDF = async () => {
    if (!activeSession?.messages) {
      alert("Keine Session aktiv.");
      return;
    }

    if (activeSession.phase !== 'done') {
      alert(`Export nur möglich wenn Recherche abgeschlossen ist.\nAktueller Status: ${activeSession.phase}`);
      return;
    }

    // Finde die LÄNGSTE Assistant-Message (das ist die Synthesis)
    const assistantMessages = activeSession.messages.filter(
      m => m.role === 'assistant' && (!m.type || m.type === 'text')
    );

    if (assistantMessages.length === 0) {
      alert("Keine exportierbare Nachricht gefunden.");
      return;
    }

    const finalMsg = assistantMessages.reduce((longest, current) =>
      current.content.length > longest.content.length ? current : longest
    );

    try {
      // Tauri Save Dialog
      const filePath = await save({
        filters: [{ name: 'PDF', extensions: ['pdf'] }],
        defaultPath: `${activeSession.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_synthesis.pdf`
      });

      if (!filePath) return;

      // Create PDF with jsPDF
      const doc = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4'
      });

      // Page settings
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      const margin = 20;
      const maxWidth = pageWidth - (margin * 2);
      let yPos = margin;
      const lineHeight = 6;

      // Helper: Check page break
      const checkPageBreak = (needed: number) => {
        if (yPos + needed > pageHeight - margin) {
          doc.addPage();
          yPos = margin;
        }
      };

      // Helper: Parse markdown table
      const parseMarkdownTable = (tableLines: string[]): { headers: string[]; rows: string[][] } | null => {
        if (tableLines.length < 2) return null;
        const headerLine = tableLines[0];
        const separatorLine = tableLines[1];

        // Check if it's a valid table
        if (!headerLine.includes('|') || !separatorLine.match(/^\|?[\s-:|]+\|?$/)) return null;

        const parseRow = (line: string): string[] => {
          return line.split('|')
            .map(cell => cell.trim())
            .filter((_, i, arr) => i > 0 && i < arr.length - (line.endsWith('|') ? 1 : 0) || !line.startsWith('|'));
        };

        const headers = parseRow(headerLine).map(h => h.replace(/\*\*/g, ''));
        const rows = tableLines.slice(2).map(line => parseRow(line).map(c => c.replace(/\*\*/g, '')));

        return { headers, rows };
      };

      // Title
      doc.setFontSize(16);
      doc.setFont('helvetica', 'bold');
      doc.text(activeSession.title, margin, yPos);
      yPos += 12;

      // Content
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');

      // Pre-process: Remove code block markers and clean up
      let content = finalMsg.content
        .replace(/```[\w]*\n?/g, '')  // Remove ``` and ```language
        .replace(/`([^`]+)`/g, '$1') // Remove inline code backticks
        // Replace Unicode arrows and special chars with ASCII equivalents
        .replace(/→|➔|➜|➝|➞|►|▶/g, '->')
        .replace(/←|◄|◀/g, '<-')
        .replace(/↔|⟷/g, '<->')
        .replace(/⇒|⇨/g, '=>')
        .replace(/⇐|⇦/g, '<=')
        .replace(/✓|✔|☑/g, '[OK]')
        .replace(/✗|✘|☒|❌/g, '[X]')
        .replace(/•|●|○|◦|▪|▫/g, '*')
        .replace(/—|–/g, '-')
        .replace(/"|"/g, '"')
        .replace(/'|'/g, "'")
        .replace(/…/g, '...')
        .replace(/×/g, 'x')
        .replace(/÷/g, '/')
        .replace(/≤/g, '<=')
        .replace(/≥/g, '>=')
        .replace(/≠/g, '!=')
        .replace(/±/g, '+/-')
        .replace(/∞/g, 'infinity')
        .replace(/📊|📈|📉/g, '[Chart]')
        .replace(/🔗/g, '[Link]')
        .replace(/⚠️|⚠/g, '[!]')
        .replace(/💡/g, '[Tip]')
        .replace(/🎯/g, '[Target]')
        .replace(/[\u{1F300}-\u{1F9FF}]/gu, '') // Remove other emojis
        .replace(/[^\x00-\x7F\xA0-\xFF\u0100-\u017F]/g, ''); // Remove remaining non-Latin chars

      // Split content into lines
      const lines = content.split('\n');
      let i = 0;

      while (i < lines.length) {
        const line = lines[i];

        // Skip separator lines (---)
        if (line.trim().match(/^-{3,}$/)) {
          yPos += 4;
          i++;
          continue;
        }

        // Check for table start (line with |)
        if (line.includes('|') && line.trim().startsWith('|')) {
          // Collect all table lines
          const tableLines: string[] = [];
          while (i < lines.length && lines[i].includes('|')) {
            tableLines.push(lines[i]);
            i++;
          }

          const table = parseMarkdownTable(tableLines);
          if (table && table.headers.length > 0) {
            checkPageBreak(30);

            autoTable(doc, {
              startY: yPos,
              head: [table.headers],
              body: table.rows,
              margin: { left: margin, right: margin },
              styles: {
                fontSize: 8,
                cellPadding: 2,
              },
              headStyles: {
                fillColor: [66, 66, 66],
                textColor: [255, 255, 255],
                fontStyle: 'bold',
              },
              alternateRowStyles: {
                fillColor: [245, 245, 245],
              },
            });

            // Update yPos after table
            yPos = (doc as any).lastAutoTable.finalY + 8;
          }
          continue;
        }

        // Headers
        if (line.startsWith('# ')) {
          checkPageBreak(15);
          yPos += 4;
          doc.setFontSize(14);
          doc.setFont('helvetica', 'bold');
          const headerText = line.replace(/^#+ /, '').replace(/\*\*/g, '');
          const wrappedHeader = doc.splitTextToSize(headerText, maxWidth);
          for (const hLine of wrappedHeader) {
            checkPageBreak(lineHeight + 1);
            doc.text(hLine, margin, yPos);
            yPos += lineHeight + 1;
          }
          doc.setFontSize(10);
          doc.setFont('helvetica', 'normal');
          yPos += 2;
        } else if (line.startsWith('## ') || line.startsWith('### ')) {
          checkPageBreak(12);
          yPos += 3;
          doc.setFontSize(11);
          doc.setFont('helvetica', 'bold');
          const headerText = line.replace(/^#+ /, '').replace(/\*\*/g, '');
          const wrappedHeader = doc.splitTextToSize(headerText, maxWidth);
          for (const hLine of wrappedHeader) {
            checkPageBreak(lineHeight);
            doc.text(hLine, margin, yPos);
            yPos += lineHeight;
          }
          doc.setFontSize(10);
          doc.setFont('helvetica', 'normal');
          yPos += 2;
        } else if (line.trim() === '') {
          yPos += 3;
        } else if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
          // Bullet points
          checkPageBreak(lineHeight);
          const bulletText = '• ' + line.trim().substring(2).replace(/\*\*/g, '');
          const wrappedLines = doc.splitTextToSize(bulletText, maxWidth - 5);
          for (let j = 0; j < wrappedLines.length; j++) {
            checkPageBreak(lineHeight);
            doc.text(wrappedLines[j], margin + (j === 0 ? 0 : 3), yPos);
            yPos += lineHeight;
          }
        } else if (line.trim().match(/^\d+\.\s/)) {
          // Numbered lists (1. 2. 3. etc.)
          checkPageBreak(lineHeight);
          const cleanLine = line.trim().replace(/\*\*/g, '');
          const wrappedLines = doc.splitTextToSize(cleanLine, maxWidth - 5);
          for (let j = 0; j < wrappedLines.length; j++) {
            checkPageBreak(lineHeight);
            doc.text(wrappedLines[j], margin + (j === 0 ? 0 : 5), yPos);
            yPos += lineHeight;
          }
        } else {
          // Normal text - clean up any remaining formatting
          const cleanLine = line
            .replace(/\*\*/g, '')
            .replace(/\*/g, '')
            .replace(/_/g, '');
          const wrappedLines = doc.splitTextToSize(cleanLine, maxWidth);
          for (const wLine of wrappedLines) {
            checkPageBreak(lineHeight);
            doc.text(wLine, margin, yPos);
            yPos += lineHeight;
          }
        }

        i++;
      }

      // Get PDF as array buffer
      const pdfArrayBuffer = doc.output('arraybuffer');
      const uint8Array = new Uint8Array(pdfArrayBuffer);

      await writeFile(filePath, uint8Array);
      alert("PDF erfolgreich exportiert!");
    } catch (err) {
      alert(`PDF Export fehlgeschlagen: ${err}`);
    }
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
      academicMode,
      settings.workModel,
      settings.finalModel
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
            {/* Research Mode Toggle */}
            <div className="flex items-center gap-2 text-sm">
              <span className={`transition-colors ${!academicMode ? 'text-[var(--text-primary)] font-medium' : 'text-[var(--text-secondary)]'}`}>
                Normal
              </span>
              <button
                onClick={handleAcademicToggle}
                className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
                  academicMode ? 'bg-blue-600' : 'bg-[var(--bg-tertiary)] border border-[var(--border)]'
                }`}
                title={academicMode ? "Academic Deep Research aktiv" : "Normal Research aktiv"}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
                    academicMode ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
              <span className={`transition-colors ${academicMode ? 'text-[var(--text-primary)] font-medium' : 'text-[var(--text-secondary)]'}`}>
                Academic
              </span>
            </div>

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
          sessionPhase={activeSession?.phase}
        />

        {/* Input */}
        <InputBar onSend={handleSend} disabled={loading || !connected} />
      </div>

      {/* Settings Modal */}
      <Settings isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
