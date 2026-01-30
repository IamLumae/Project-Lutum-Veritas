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
import { useBackend, type LogEvent } from "../hooks/useBackend";
import { initDarkMode, loadSettings, PROVIDER_CONFIG } from "../stores/settings";
import { t, type Language } from "../i18n/translations";
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

  const { loading, error, connected, checkHealth, runPipeline, createPlan, revisePlan, runDeepResearch, runAcademicResearch, recoverSession, resumeSession } = useBackend();

  // Live-Status vom Streaming (ersetzt SSE)
  const [currentStatus, setCurrentStatus] = useState<string>("");

  // Timer State
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Settings State (Lifted for UI Controls) - Init directly from settings to avoid race condition
  const [modelSize, setModelSize] = useState<'small' | 'large'>(() => loadSettings().modelSize);
  const [academicMode, setAcademicMode] = useState(() => loadSettings().academicMode);
  const [language, setLanguage] = useState<Language>(() => loadSettings().language);

  // Init Settings State
  useEffect(() => {
    const s = loadSettings();
    setModelSize(s.modelSize);
    setAcademicMode(s.academicMode);
    setLanguage(s.language);
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
      alert(t('noSessionActive', language));
      return;
    }

    if (activeSession.phase !== 'done') {
      alert(t('exportOnlyWhenDone', language) + activeSession.phase);
      return;
    }

    // Find the LONGEST assistant message (that's the synthesis, not the summary)
    const assistantMessages = activeSession.messages.filter(
      m => m.role === 'assistant' && (!m.type || m.type === 'text')
    );

    if (assistantMessages.length === 0) {
      alert(t('noExportableMessage', language));
      return;
    }

    // The longest message is the synthesis
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
        alert(t('mdExportSuccess', language));
      }
    } catch (err) {
      alert(t('exportFailed', language) + err);
    }
  };

  const handleExportPDF = async () => {
    if (!activeSession?.messages) {
      alert(t('noSessionActive', language));
      return;
    }

    if (activeSession.phase !== 'done') {
      alert(t('exportOnlyWhenDone', language) + activeSession.phase);
      return;
    }

    // Find the LONGEST assistant message (that's the synthesis)
    const assistantMessages = activeSession.messages.filter(
      m => m.role === 'assistant' && (!m.type || m.type === 'text')
    );

    if (assistantMessages.length === 0) {
      alert(t('noExportableMessage', language));
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

        // Check if it's a valid table (separator line must have dashes)
        if (!headerLine.includes('|') || !separatorLine.match(/^\|?[\s-:|]+\|?$/)) return null;

        const parseRow = (line: string): string[] => {
          const cells = line.split('|').map(cell => cell.trim());
          // Remove empty first/last cells from leading/trailing pipes
          if (cells.length > 0 && cells[0] === '') cells.shift();
          if (cells.length > 0 && cells[cells.length - 1] === '') cells.pop();
          return cells;
        };

        const headers = parseRow(headerLine).map(h => h.replace(/\*\*/g, ''));
        // Skip empty rows and filter out separator line
        const rows = tableLines.slice(2)
          .filter(line => line.trim() && !line.match(/^\|?[\s-:|]+\|?$/))
          .map(line => parseRow(line).map(c => c.replace(/\*\*/g, '')));

        // Validate: headers and rows should have same column count
        if (headers.length === 0) return null;

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

        // Check for table start (line with | AND next line is separator with -)
        const nextLine = i + 1 < lines.length ? lines[i + 1] : '';
        const isTableStart = line.includes('|') && nextLine.includes('|') && nextLine.includes('-');

        if (isTableStart) {
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
          } else {
            // Failed to parse as table, rewind and process as normal text
            i -= tableLines.length;
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
      alert(t('pdfExportSuccess', language));
    } catch (err) {
      alert(t('pdfExportFailed', language) + err);
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

  // Check backend connection - fast polling until connected, then slow
  // Skip health checks during active research to prevent "offline" flicker
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;
    let wasConnected = false;

    const poll = async () => {
      // Skip health check during active research - we know backend is running if we're getting events
      if (loading) {
        return;
      }

      const online = await checkHealth();

      if (online !== wasConnected) {
        // Connection status changed - adjust polling speed
        wasConnected = online;
        if (interval) clearInterval(interval);
        interval = setInterval(poll, online ? 30000 : 2000);
      }
    };

    // Start with fast polling (2s)
    poll();
    interval = setInterval(poll, 2000);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [checkHealth, loading]);

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

  const addLogMessage = useCallback(
    (sessionId: string, event: LogEvent) => {
      const details = event.full && event.full !== event.message ? `\n\n${event.full}` : "";
      const logMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `${event.message}${details}`,
        timestamp: new Date().toISOString(),
        type: "log",
        logLevel: event.level === "ERROR" ? "error" : "warning",
      };
      addMessage(sessionId, logMsg);
    },
    [addMessage]
  );

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
        updateSession(sessionId, { title: t('researchRunning', language), phase: "clarifying" });

        // Pipeline mit Status-Callback für Live-Updates und Sources-Callback für URLs
        const settings = loadSettings();
        const baseUrl = PROVIDER_CONFIG[settings.provider].baseUrl;
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
              content: language === 'de' ? `Ich habe ${urls.length} relevante Quellen gefunden:` : `Found ${urls.length} relevant sources:`,
              timestamp: new Date().toISOString(),
              type: "sources",
              sources: urls,
            };
            addMessage(sessionId, sourcesMsg);
          },
          (event) => addLogMessage(sessionId, event),
          modelSize,
          academicMode,
          language,
          settings.provider,
          settings.workModel,
          baseUrl
        );

        // Session-Titel vom LLM
        if (pipelineResult?.session_title) {
          updateSession(sessionId, { title: pipelineResult.session_title });
        }

        // Assistant Message with follow-up questions
        const responseText = pipelineResult?.response || pipelineResult?.error || t('researchError', language);
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
        const baseUrl = PROVIDER_CONFIG[settings.provider].baseUrl;
        const planResult = await createPlan(
          ctx.user_query,
          ctx.clarification_questions,
          [content],
          settings.apiKey,
          sessionId,
          modelSize,
          academicMode,
          settings.provider,
          settings.workModel,
          baseUrl
        );

        // Check für Normal Mode (plan_points) ODER Academic Mode (academic_bereiche)
        const hasNormalPlan = planResult?.plan_points && planResult.plan_points.length > 0;
        const hasAcademicPlan = planResult?.academic_bereiche && Object.keys(planResult.academic_bereiche).length > 0;

        if (hasNormalPlan || hasAcademicPlan) {
          // Plan message with special type
          const planMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: t('planCreated', language) + planResult.plan_text + (language === 'de' ? '\n\n_Sag mir, falls ich ihn ändern soll._' : '\n\n_Let me know if you want to change it._'),
            timestamp: new Date().toISOString(),
            type: "plan",
          };
          addMessage(sessionId, planMsg);

          // Update context state with plan
          updateSession(sessionId, {
            contextState: planResult.context_state,
            phase: "planning",
          });
        } else {
          // Error
          const errorMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: planResult?.error || t('planFailed', language),
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
        const baseUrl = PROVIDER_CONFIG[settings.provider].baseUrl;
        const reviseResult = await revisePlan(
          ctx,
          content,
          settings.apiKey,
          sessionId,
          modelSize,
          academicMode,
          settings.provider,
          settings.workModel,
          baseUrl
        );

        // Check für Normal Mode (plan_points) ODER Academic Mode (academic_bereiche)
        const hasNormalPlan = reviseResult?.plan_points && reviseResult.plan_points.length > 0;
        const hasAcademicPlan = reviseResult?.academic_bereiche && Object.keys(reviseResult.academic_bereiche).length > 0;

        if (hasNormalPlan || hasAcademicPlan) {
          const planMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: t('planRevised', language) + reviseResult.context_state.plan_version + t('planRevisedSuffix', language) + reviseResult.plan_text + (language === 'de' ? '\n\n_Sag mir, falls ich ihn noch ändern soll._' : '\n\n_Let me know if you want to change it more._'),
            timestamp: new Date().toISOString(),
            type: "plan",
          };
          addMessage(sessionId, planMsg);
          updateSession(sessionId, { contextState: reviseResult.context_state });
        } else {
          const errorMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: reviseResult?.error || t('planFailed', language),
            timestamp: new Date().toISOString(),
          };
          addMessage(sessionId, errorMsg);
        }
      }
    },
    [sessionsState.activeSessionId, activeSession, runPipeline, createPlan, revisePlan, updateSession, addMessage, addLogMessage]
  );

  // Handler: "Los geht's" Button → Deep Research starten
  const handleStartResearch = useCallback(async () => {
    if (!activeSession || !activeSession.contextState) return;

    const sessionId = activeSession.id;
    const ctx = activeSession.contextState;

    // Phase auf "researching" setzen
    updateSession(sessionId, { phase: "researching" });

    const settings = loadSettings();
    const baseUrl = PROVIDER_CONFIG[settings.provider].baseUrl;

    // === ACADEMIC MODE: Hierarchische Bereiche mit Meta-Synthese ===
    if (academicMode && ctx.academic_bereiche && Object.keys(ctx.academic_bereiche).length > 0) {
      const totalBereiche = Object.keys(ctx.academic_bereiche).length;
      const totalPunkte = Object.values(ctx.academic_bereiche).reduce((sum, pts) => sum + pts.length, 0);

      // Start message für Academic Mode
      const startMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: language === 'de'
          ? `🎓 **Academic Deep Research gestartet**\n\n${totalBereiche} Bereiche mit insgesamt ${totalPunkte} Punkten.\n\n_Nach jedem Bereich siehst du die Erkenntnisse. Am Ende folgt die Meta-Synthese mit Querverbindungen._`
          : `🎓 **Academic Deep Research started**\n\n${totalBereiche} areas with ${totalPunkte} points total.\n\n_You will see findings after each area. At the end comes the meta-synthesis with cross-connections._`,
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, startMsg);

      // Academic Research ausführen
      const result = await runAcademicResearch(
        ctx,
        settings.apiKey,
        sessionId,
        // onStatus
        (status) => setCurrentStatus(status),
        // onSources
        (urls) => {
          const sourcesMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: `📚 ${urls.length} ${language === 'de' ? 'Quellen gefunden' : 'sources found'}`,
            timestamp: new Date().toISOString(),
            type: "sources",
            sources: urls,
          };
          addMessage(sessionId, sourcesMsg);
        },
        // onPointComplete
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
        // onBereichStart
        (event) => {
          const bereichMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: language === 'de'
              ? `📂 **Bereich ${event.bereichNumber}/${event.totalBereiche}: ${event.bereichTitle}**\n\n_${event.pointsInBereich} Punkte in diesem Bereich_`
              : `📂 **Area ${event.bereichNumber}/${event.totalBereiche}: ${event.bereichTitle}**\n\n_${event.pointsInBereich} points in this area_`,
            timestamp: new Date().toISOString(),
          };
          addMessage(sessionId, bereichMsg);
        },
        // onBereichComplete
        (event) => {
          const completeMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: language === 'de'
              ? `✅ **Bereich abgeschlossen: ${event.bereichTitle}**\n\n${event.dossiersCount} Dossiers aus ${event.sourcesCount} Quellen`
              : `✅ **Area complete: ${event.bereichTitle}**\n\n${event.dossiersCount} dossiers from ${event.sourcesCount} sources`,
            timestamp: new Date().toISOString(),
          };
          addMessage(sessionId, completeMsg);
        },
        // onMetaSynthesisStart
        (event) => {
          const metaMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: language === 'de'
              ? `🔬 **Meta-Synthese startet**\n\nFinde Querverbindungen zwischen ${event.bereicheCount} Bereichen aus ${event.totalSources} Quellen...\n\n_Das kann einige Minuten dauern._`
              : `🔬 **Meta-Synthesis starting**\n\nFinding cross-connections between ${event.bereicheCount} areas from ${event.totalSources} sources...\n\n_This may take a few minutes._`,
            timestamp: new Date().toISOString(),
            type: "synthesis_waiting",
          };
          addMessage(sessionId, metaMsg);
        },
        (event) => addLogMessage(sessionId, event),
        settings.provider,
        settings.workModel,
        settings.finalModel,
        language,
        baseUrl
      );

      // Ergebnis verarbeiten
      if (result?.syntheses && result?.conclusion) {
        // NEW: Structured rendering - each synthesis as collapsible block
        for (const synthesis of result.syntheses) {
          const synthesisMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: synthesis.content,
            timestamp: new Date().toISOString(),
            type: "synthesis",
            synthesisTitle: synthesis.title,
            synthesisIndex: synthesis.index,
            totalSyntheses: result.syntheses.length,
            synthesisSourcesCount: synthesis.sources_count,
          };
          addMessage(sessionId, synthesisMsg);
        }

        // Conclusion - always open, orange theme
        const conclusionMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.conclusion.content,
          timestamp: new Date().toISOString(),
          type: "conclusion",
          impactStatement: result.conclusion.impact_statement,
          conclusionMetrics: result.conclusion_metrics ? {
            totalSources: result.conclusion_metrics.total_sources,
            totalSyntheseChars: result.conclusion_metrics.total_synthese_chars,
            totalDossiers: result.conclusion_metrics.total_dossiers,
            totalAreas: result.conclusion_metrics.total_areas,
          } : undefined,
        };
        addMessage(sessionId, conclusionMsg);

        // Source Registry wird inline im Report angezeigt (ReportRenderer)
        // Keine separate Message nötig - verhindert Doppel-Anzeige

        // Summary
        const summaryMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: language === 'de'
            ? `✨ **Academic Research abgeschlossen**\n\n- ${result.total_bereiche} Bereiche\n- ${result.total_points} Punkte\n- ${result.total_sources} Quellen\n- Dauer: ${Math.round(result.duration_seconds / 60)} Minuten`
            : `✨ **Academic Research complete**\n\n- ${result.total_bereiche} areas\n- ${result.total_points} points\n- ${result.total_sources} sources\n- Duration: ${Math.round(result.duration_seconds / 60)} minutes`,
          timestamp: new Date().toISOString(),
        };
        addMessage(sessionId, summaryMsg);

        updateSession(sessionId, { phase: "done" });
      } else if (result?.final_document) {
        // LEGACY: Fallback to old behavior if no structured data
        const finalMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.final_document,
          timestamp: new Date().toISOString(),
        };
        addMessage(sessionId, finalMsg);

        updateSession(sessionId, { phase: "done" });
      } else if (result?.error) {
        const errorMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: t('researchErrorPrefix', language) + result.error,
          timestamp: new Date().toISOString(),
        };
        addMessage(sessionId, errorMsg);
        updateSession(sessionId, { phase: "planning" });
      }

      return;
    }

    // === NORMAL MODE: Flache Liste ===
    // Start message
    const startMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: t('deepResearchStarted', language) + ctx.research_plan.length + (language === 'de' ? ' Punkte ab. Das kann einige Minuten dauern.\n\n_Du siehst nach jedem Punkt die Erkenntnisse._' : ' points. This may take a few minutes.\n\n_You will see the findings after each point._'),
      timestamp: new Date().toISOString(),
    };
    addMessage(sessionId, startMsg);

    // Deep Research ausführen
    const result = await runDeepResearch(
      ctx,
      settings.apiKey,
      sessionId,
      // onStatus: Live-Status-Updates
      (status) => {
        setCurrentStatus(status);
      },
      // onSources: Sources box for each point
      (urls) => {
        const sourcesMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: t('analyzing', language) + urls.length + (language === 'de' ? ' Quellen...' : ' sources...'),
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
      // onSynthesisStart: Final Synthesis starts (long wait)
      (event) => {
        const synthMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: t('finalSynthesisStarting', language) + event.dossierCount + (language === 'de' ? ` Dossiers aus ${event.totalSources} Quellen.\nGeschätzte Dauer: ~${event.estimatedMinutes} Minuten.\n\n_Bitte nicht schließen - das dauert einen Moment._` : ` dossiers from ${event.totalSources} sources.\nEstimated duration: ~${event.estimatedMinutes} minutes.\n\n_Please don't close - this takes a moment._`),
          timestamp: new Date().toISOString(),
          type: "synthesis_waiting",
          estimatedMinutes: event.estimatedMinutes,
        };
        addMessage(sessionId, synthMsg);
      },
      (event) => addLogMessage(sessionId, event),
      modelSize,
      academicMode,
      settings.provider,
      settings.workModel,
      settings.finalModel,
      language,
      baseUrl
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
        content: t('researchComplete', language) + (language === 'de' ? `${result.total_points} Punkte bearbeitet\n- ${result.total_sources} Quellen analysiert\n- Dauer: ${Math.round(result.duration_seconds / 60)} Minuten` : `${result.total_points} points processed\n- ${result.total_sources} sources analyzed\n- Duration: ${Math.round(result.duration_seconds / 60)} minutes`),
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, summaryMsg);

      // Source Registry wird inline im Report angezeigt (ReportRenderer)
      // Keine separate Message nötig - verhindert Doppel-Anzeige

      updateSession(sessionId, { phase: "done" });
    } else if (result?.error) {
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: t('researchErrorPrefix', language) + result.error,
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, errorMsg);
      updateSession(sessionId, { phase: "planning" }); // Back to Planning
    }
  }, [activeSession, runDeepResearch, runAcademicResearch, updateSession, addMessage, addLogMessage, academicMode, language]);

  // Handler: "Edit plan" button → User can enter changes
  const handleEditPlan = useCallback(() => {
    if (!activeSession) return;

    // Prompt message for user to enter changes
    const promptMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: t('planChangePrompt', language),
      timestamp: new Date().toISOString(),
    };
    addMessage(activeSession.id, promptMsg);

    // Phase auf "clarifying" setzen damit nächste User-Message den Plan überarbeitet
    // Aber wir brauchen einen Marker dass es um Plan-Bearbeitung geht
    updateSession(activeSession.id, { phase: "planning" }); // Bleibt in planning, handleSend prüft das
  }, [activeSession, addMessage, updateSession]);

  // Handler: "Load synthesis" button → Gets last synthesis from backup
  const handleRecoverSynthesis = useCallback(async () => {
    if (!activeSession) return;

    const sessionId = activeSession.id;

    // Status message
    const loadingMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: t('loadingLastSynthesis', language),
      timestamp: new Date().toISOString(),
    };
    addMessage(sessionId, loadingMsg);

    const result = await recoverSession();

    if (result?.success && result.session_id) {
      const completedCount = result.completed_dossiers?.length || 0;
      const remainingCount = result.remaining_points?.length || 0;
      const totalCount = completedCount + remainingCount;

      if (remainingCount > 0) {
        // Es gibt noch offene Punkte - automatisch fortsetzen!
        const statusMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: language === 'de'
            ? `🔄 Session gefunden: ${completedCount}/${totalCount} Dossiers fertig. Setze fort...`
            : `🔄 Session found: ${completedCount}/${totalCount} dossiers complete. Resuming...`,
          timestamp: new Date().toISOString(),
        };
        addMessage(sessionId, statusMsg);
        updateSession(sessionId, { phase: "researching" });

        // Automatisch fortsetzen
        const settings = loadSettings();
        const baseUrl = PROVIDER_CONFIG[settings.provider].baseUrl;
        await resumeSession(
          result.session_id,
          settings.apiKey,
          settings.provider,
          settings.workModel,
          settings.finalModel,
          // onStatus
          (status) => setCurrentStatus(status),
          // onSources
          (urls) => {
            const sourcesMsg: Message = {
              id: crypto.randomUUID(),
              role: "assistant",
              content: `📚 ${urls.length} Quellen gefunden`,
              timestamp: new Date().toISOString(),
              sources: urls
            };
            addMessage(sessionId, sourcesMsg);
          },
          // onPointComplete
          (event) => {
            const pointMsg: Message = {
              id: crypto.randomUUID(),
              role: "assistant",
              content: event.skipped
                ? `⏭️ Punkt ${event.pointNumber} übersprungen: ${event.skipReason}`
                : `✅ Punkt ${event.pointNumber}/${event.totalPoints}: ${event.pointTitle}\n\n${event.dossierFull || event.keyLearnings}`,
              timestamp: new Date().toISOString(),
            };
            addMessage(sessionId, pointMsg);
          },
          // onSynthesisStart
          (event) => {
            const synthMsg: Message = {
              id: crypto.randomUUID(),
              role: "assistant",
              content: language === 'de'
                ? `🔬 Final Synthesis läuft... (${event.dossierCount} Dossiers)`
                : `🔬 Final Synthesis running... (${event.dossierCount} dossiers)`,
              timestamp: new Date().toISOString(),
            };
            addMessage(sessionId, synthMsg);
          },
          (event) => addLogMessage(sessionId, event),
          baseUrl
        );

        updateSession(sessionId, { phase: "done" });
      } else {
        // Alles fertig - nur Status zeigen
        const doneMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: language === 'de'
            ? `✅ Session bereits abgeschlossen: ${completedCount} Dossiers`
            : `✅ Session already complete: ${completedCount} dossiers`,
          timestamp: new Date().toISOString(),
        };
        addMessage(sessionId, doneMsg);
        updateSession(sessionId, { phase: "done" });
      }
    } else {
      // Error message
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: t('synthesisLoadFailed', language) + (result?.error || (language === 'de' ? 'Unbekannter Fehler' : 'Unknown error')),
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, errorMsg);
    }
  }, [activeSession, recoverSession, resumeSession, addMessage, addLogMessage, updateSession, language, setCurrentStatus]);

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
        language={language}
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
                {t('normal', language)}
              </span>
              <button
                onClick={handleAcademicToggle}
                className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
                  academicMode ? 'bg-blue-600' : 'bg-[var(--bg-tertiary)] border border-[var(--border)]'
                }`}
                title={t('academicModeActive', language)}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
                    academicMode ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
              <span className={`transition-colors ${academicMode ? 'text-[var(--text-primary)] font-medium' : 'text-[var(--text-secondary)]'}`}>
                {t('academic', language)}
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
                {connected ? t('connected', language) : t('offline', language)}
              </span>
            </div>

            {/* Settings Button */}
            <button
              onClick={() => setSettingsOpen(true)}
              className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors p-2"
              title={t('settings', language)}
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
          language={language}
        />

        {/* Input */}
        <InputBar onSend={handleSend} disabled={loading || !connected} language={language} />
      </div>

      {/* Settings Modal */}
      <Settings isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
