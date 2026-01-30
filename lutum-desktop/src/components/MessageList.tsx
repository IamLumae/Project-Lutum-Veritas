/**
 * MessageList Component
 * ======================
 * Zeigt Chat-Nachrichten an mit schönem Markdown Rendering.
 * Unterstützt Plan-Messages mit Buttons und Sources-Box.
 *
 * Security Notes:
 * - All URLs are validated before opening
 * - javascript:/data: protocols are blocked
 * - Private IPs are blocked (SSRF prevention)
 */

import React, { useRef, useEffect, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { t, type Language } from "../i18n/translations";
import { ReportRenderer } from "./ReportRenderer";

// ============================================================================
// SECURITY FUNCTIONS
// ============================================================================

/**
 * Validates URL for security.
 * Prevents javascript:, data:, file: and other dangerous protocols.
 */
function isValidUrl(url: string): boolean {
  if (!url || typeof url !== 'string') return false;
  if (url.length > 2048) return false;

  try {
    const parsed = new URL(url);
    // Only allow http/https protocols
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return false;
    }

    // Block private IPs (basic SSRF protection)
    const host = parsed.hostname.toLowerCase();
    const privatePatterns = [
      'localhost', '127.', '0.0.0.0', '10.', '192.168.',
      '172.16.', '172.17.', '172.18.', '172.19.',
      '172.20.', '172.21.', '172.22.', '172.23.',
      '172.24.', '172.25.', '172.26.', '172.27.',
      '172.28.', '172.29.', '172.30.', '172.31.',
      '169.254.', '[::1]'
    ];

    for (const pattern of privatePatterns) {
      if (host.startsWith(pattern) || host === pattern.replace('.', '')) {
        return false;
      }
    }

    return true;
  } catch {
    return false;
  }
}

/**
 * Safely opens a URL after validation.
 */
async function safeOpenUrl(url: string): Promise<void> {
  if (!isValidUrl(url)) {
    console.warn('Blocked potentially unsafe URL:', url);
    return;
  }

  try {
    await openUrl(url);
  } catch {
    // Fallback with security settings
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

/**
 * Prüft ob Content ein strukturierter Report mit unseren Markern ist.
 * Reports haben Emoji-Section-Header (## 📊) und/oder SOURCES-Block.
 */
function isReportContent(content: string): boolean {
  // Check für Emoji Section Headers
  const hasEmojiSections = /^##\s+[📊🔬📚🔗⚖️🎯📋📎💡🔍🔄]/m.test(content);

  // Check für SOURCES Block
  const hasSourcesBlock = content.includes("=== SOURCES ===");

  // Check für END REPORT oder END DOSSIER
  const hasEndMarker = content.includes("=== END REPORT ===") || content.includes("=== END DOSSIER ===");

  // Ist ein Report wenn mindestens 2 der 3 Kriterien erfüllt sind
  // ODER wenn es Emoji Sections UND mindestens ein End-Marker hat
  const criteria = [hasEmojiSections, hasSourcesBlock, hasEndMarker];
  const criteriaCount = criteria.filter(Boolean).length;

  return criteriaCount >= 2 || (hasEmojiSections && content.length > 1000);
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  url?: string;
  loading?: boolean;
  /** Spezial-Typ für verschiedene Anzeigen */
  type?: "text" | "plan" | "sources" | "point_summary" | "synthesis_waiting" | "sources_registry" | "log";
  /** Log Level für log-Nachrichten */
  logLevel?: "warning" | "error";
  /** URLs für sources-Typ */
  sources?: string[];
  /** Source Registry für klickbare Citations {1: "url1", 2: "url2"} */
  sourceRegistry?: Record<number, string>;
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

/**
 * SourcesBox - Collapsible box with clickable source links.
 * Security: URLs are validated before use.
 */
function SourcesBox({ sources, language }: { sources: string[]; language: Language }) {
  const [expanded, setExpanded] = useState(false);

  const getDomain = (url: string) => {
    if (!isValidUrl(url)) return "Invalid URL";
    try {
      return new URL(url).hostname.replace("www.", "");
    } catch {
      return "Invalid URL";
    }
  };

  return (
    <div className="mt-3 rounded-xl border border-[var(--border)] overflow-hidden bg-[var(--bg-tertiary)]/50 max-w-full">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-[var(--bg-hover)] transition-all duration-200"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
          <span className="text-lg">📚</span>
          {t('sourcesUsed', language)}{sources.length})
        </span>
        <span className={`text-[var(--text-secondary)] transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}>
          ▼
        </span>
      </button>

      {expanded && (
        <div className="border-t border-[var(--border)]">
          {sources.map((url, index) => {
            const urlIsValid = isValidUrl(url);
            return (
              <button
                key={index}
                onClick={() => urlIsValid && safeOpenUrl(url)}
                disabled={!urlIsValid}
                className={`w-full text-left px-4 py-3 transition-colors group border-b border-[var(--border)] last:border-b-0 ${
                  urlIsValid
                    ? 'hover:bg-[var(--bg-hover)] cursor-pointer'
                    : 'opacity-50 cursor-not-allowed'
                }`}
              >
                <div className="flex items-center gap-2 md:gap-3 overflow-hidden">
                  <span className="text-blue-400 text-sm md:text-base flex-shrink-0">🔗</span>
                  <div className="flex-1 min-w-0 overflow-hidden">
                    <span className="text-xs md:text-sm font-medium text-[var(--text-primary)] group-hover:text-blue-400 transition-colors">
                      {getDomain(url)}
                    </span>
                    <div className="text-xs text-[var(--text-secondary)] truncate mt-0.5 opacity-70">
                      {urlIsValid ? url : 'URL konnte nicht validiert werden'}
                    </div>
                  </div>
                  {urlIsValid && (
                    <span className="text-[var(--text-secondary)] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 hidden sm:block">
                      →
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * SourcesRegistryBox - Zeigt alle Quellen mit globaler Nummerierung.
 * Ausklappbar am Ende der Deep Research.
 */
function SourcesRegistryBox({ registry, language }: { registry: Record<number, string>; language: Language }) {
  const [expanded, setExpanded] = useState(false);

  const getDomain = (url: string) => {
    if (!isValidUrl(url)) return "Invalid URL";
    try {
      return new URL(url).hostname.replace("www.", "");
    } catch {
      return "Invalid URL";
    }
  };

  // Sortiere nach Nummer
  const sortedEntries = Object.entries(registry)
    .map(([num, url]) => ({ num: parseInt(num), url }))
    .sort((a, b) => a.num - b.num);

  return (
    <div className="rounded-xl border-2 border-purple-500/30 overflow-hidden bg-gradient-to-br from-purple-500/5 to-blue-500/10 w-full">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-purple-500/10 hover:bg-purple-500/20 transition-all duration-200"
      >
        <span className="flex items-center gap-2 text-sm font-bold text-purple-400">
          <span className="text-lg">📎</span>
          {language === 'de' ? 'Quellenverzeichnis' : 'Source Registry'} ({sortedEntries.length})
        </span>
        <span className={`text-purple-400 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}>
          ▼
        </span>
      </button>

      {/* Expandable Content */}
      {expanded && (
        <div className="border-t border-purple-500/20 max-h-[400px] overflow-y-auto">
          {sortedEntries.map(({ num, url }) => {
            const urlIsValid = isValidUrl(url);
            return (
              <button
                key={num}
                onClick={() => urlIsValid && safeOpenUrl(url)}
                disabled={!urlIsValid}
                className={`w-full text-left px-4 py-2.5 transition-colors group border-b border-purple-500/10 last:border-b-0 ${
                  urlIsValid
                    ? 'hover:bg-purple-500/10 cursor-pointer'
                    : 'opacity-50 cursor-not-allowed'
                }`}
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  {/* Citation Number Badge */}
                  <span className="flex-shrink-0 w-7 h-7 flex items-center justify-center bg-blue-500/20 text-blue-400 text-xs font-bold rounded border border-blue-500/30">
                    {num}
                  </span>
                  {/* URL Info */}
                  <div className="flex-1 min-w-0 overflow-hidden">
                    <span className="text-xs md:text-sm font-medium text-[var(--text-primary)] group-hover:text-blue-400 transition-colors">
                      {getDomain(url)}
                    </span>
                    <div className="text-xs text-[var(--text-secondary)] truncate mt-0.5 opacity-70">
                      {urlIsValid ? url : 'URL ungültig'}
                    </div>
                  </div>
                  {/* Arrow */}
                  {urlIsValid && (
                    <span className="text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                      →
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * PointSummaryBox - Zeigt Fortschritt nach jedem abgeschlossenen Recherche-Punkt.
 * "Don't hide the sweat" - User sieht dass das System arbeitet.
 * Mit ausklappbarem vollständigem Dossier.
 */
function PointSummaryBox({
  pointTitle,
  pointNumber,
  totalPoints,
  content,
  dossierFull,
  skipped,
  skipReason,
  language
}: {
  pointTitle: string;
  pointNumber: number;
  totalPoints: number;
  content: string;
  dossierFull?: string;
  skipped?: boolean;
  skipReason?: string;
  language: Language;
}) {
  const [showFullDossier, setShowFullDossier] = useState(false);
  const progress = Math.round((pointNumber / totalPoints) * 100);

  // Übersprungene Punkte anders stylen
  if (skipped) {
    return (
      <div className="rounded-xl border-2 border-yellow-500/30 overflow-hidden bg-gradient-to-br from-yellow-500/5 to-yellow-600/10 w-full">
        <div className="px-4 py-3 bg-yellow-500/10 border-b border-yellow-500/20">
          <div className="flex items-center justify-between mb-2">
            <span className="flex items-center gap-2 text-sm font-bold text-yellow-400">
              <span className="text-lg">⚠</span>
              {t('pointSkipped', language)}{pointNumber}/{totalPoints}{t('skipped', language)}
            </span>
            <span className="text-xs font-semibold text-yellow-400/80">
              {progress}%
            </span>
          </div>
          <div className="w-full h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-yellow-500 to-yellow-400 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        <div className="px-4 py-2 border-b border-yellow-500/10">
          <span className="text-sm font-semibold text-[var(--text-primary)]">
            {pointTitle}
          </span>
        </div>
        <div className="px-4 py-3 text-sm text-yellow-400/80">
          <strong>{t('reason', language)}</strong> {skipReason || (language === 'de' ? 'Unbekannt' : 'Unknown')}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border-2 border-green-500/30 overflow-hidden bg-gradient-to-br from-green-500/5 to-green-600/10 w-full">
      {/* Header mit Fortschritt */}
      <div className="px-4 py-3 bg-green-500/10 border-b border-green-500/20">
        <div className="flex items-center justify-between mb-2">
          <span className="flex items-center gap-2 text-sm font-bold text-green-400">
            <span className="text-lg">✓</span>
            {t('pointCompleted', language)}{pointNumber}/{totalPoints}{t('completed', language)}
          </span>
          <span className="text-xs font-semibold text-green-400/80">
            {progress}%
          </span>
        </div>
        {/* Progress Bar */}
        <div className="w-full h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Punkt-Titel */}
      <div className="px-4 py-2 border-b border-green-500/10">
        <span className="text-sm font-semibold text-[var(--text-primary)]">
          {pointTitle}
        </span>
      </div>

      {/* Key Learnings Content */}
      <div className="px-4 py-3 text-sm text-[var(--text-secondary)] leading-relaxed">
        <MarkdownContent content={content} isUser={false} />
      </div>

      {/* Volles Dossier ausklappbar */}
      {dossierFull && (
        <div className="border-t border-green-500/20">
          <button
            onClick={() => setShowFullDossier(!showFullDossier)}
            className="w-full flex items-center justify-between px-4 py-2 hover:bg-green-500/10 transition-all duration-200 text-sm"
          >
            <span className="flex items-center gap-2 text-green-400 font-medium">
              <span>📄</span>
              {showFullDossier ? t('hideDossier', language) : t('showFullDossier', language)}
            </span>
            <span className={`text-green-400 transition-transform duration-200 ${showFullDossier ? "rotate-180" : ""}`}>
              ▼
            </span>
          </button>

          {showFullDossier && (
            <div className="px-4 py-4 border-t border-green-500/10 bg-[var(--bg-tertiary)]/30 text-sm text-[var(--text-secondary)] leading-relaxed max-h-[500px] overflow-y-auto">
              {isReportContent(dossierFull) ? (
                <ReportRenderer content={dossierFull} />
              ) : (
                <MarkdownContent content={dossierFull} isUser={false} />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * CitationBadge - Klickbarer Citation Badge [N]
 */
function CitationBadge({ num }: { num: number }) {
  return (
    <span
      className="inline-flex items-center justify-center w-5 h-5 mx-0.5 text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded align-super cursor-default"
      title={`Quelle ${num}`}
    >
      {num}
    </span>
  );
}

/**
 * Parst Text und ersetzt [N] mit CitationBadge
 */
function parseCitationsInText(text: string, keyPrefix: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  const regex = /\[(\d+)\]/g;
  let match;
  let count = 0;

  while ((match = regex.exec(text)) !== null) {
    // Text vor der Citation
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    // Citation Badge
    const num = parseInt(match[1], 10);
    parts.push(<CitationBadge key={`${keyPrefix}-${count++}`} num={num} />);
    lastIndex = match.index + match[0].length;
  }

  // Rest des Texts
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

/**
 * Rekursiv durch Children gehen und Citations parsen
 */
function processChildrenForCitations(children: React.ReactNode, keyPrefix: string): React.ReactNode {
  if (typeof children === 'string') {
    const parsed = parseCitationsInText(children, keyPrefix);
    return parsed.length === 1 ? parsed[0] : <>{parsed}</>;
  }

  if (Array.isArray(children)) {
    return children.map((child, i) => processChildrenForCitations(child, `${keyPrefix}-${i}`));
  }

  if (React.isValidElement(children)) {
    const childProps = children.props as { children?: React.ReactNode };
    if (childProps.children) {
      return React.cloneElement(children, {}, processChildrenForCitations(childProps.children, keyPrefix));
    }
  }

  return children;
}

/**
 * MarkdownContent - Rendert Markdown mit schönem Styling.
 * Security: All URLs are validated before opening.
 */
function MarkdownContent({ content, isUser }: { content: string; isUser: boolean }) {
  const handleLinkClick = async (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault();
    await safeOpenUrl(href);
  };

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Paragraphs - MIT Citation Parsing
        p: ({ children }) => (
          <p className="mb-3 last:mb-0 leading-relaxed">{processChildrenForCitations(children, 'p')}</p>
        ),

        // Headers
        h1: ({ children }) => (
          <h1 className="text-xl font-bold mb-3 mt-4 first:mt-0 text-[var(--text-primary)]">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-lg font-bold mb-2 mt-3 first:mt-0 text-[var(--text-primary)]">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-base font-bold mb-2 mt-3 first:mt-0 text-[var(--text-primary)]">{children}</h3>
        ),

        // Bold & Italic
        strong: ({ children }) => (
          <strong className="font-semibold text-[var(--text-primary)]">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="italic opacity-90">{children}</em>
        ),

        // Lists
        ul: ({ children }) => (
          <ul className="mb-3 ml-1 space-y-1.5">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-3 ml-1 space-y-1.5 list-decimal list-inside">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="flex items-start gap-2">
            <span className="text-blue-400 mt-1.5 text-xs">●</span>
            <span className="flex-1">{processChildrenForCitations(children, 'li')}</span>
          </li>
        ),

        // Code
        code: ({ className, children }) => {
          const isBlock = className?.includes("language-");
          if (isBlock) {
            return (
              <code className="block bg-[#1a1a2e] text-[#a8dadc] p-3 md:p-4 rounded-xl my-3 text-xs md:text-sm font-mono overflow-x-auto border border-[#2a2a4a] whitespace-pre-wrap break-all">
                {children}
              </code>
            );
          }
          return (
            <code className={`px-1 md:px-1.5 py-0.5 rounded-md text-xs md:text-sm font-mono break-all ${
              isUser
                ? "bg-blue-500/30 text-blue-100"
                : "bg-[var(--bg-tertiary)] text-[var(--accent)]"
            }`}>
              {children}
            </code>
          );
        },
        pre: ({ children }) => (
          <pre className="my-3">{children}</pre>
        ),

        // Blockquotes
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-blue-400 pl-4 my-3 italic opacity-90 bg-[var(--bg-tertiary)]/50 py-2 rounded-r-lg">
            {children}
          </blockquote>
        ),

        // Links (with security validation)
        a: ({ href, children }) => {
          // Security: Validate URL before rendering as clickable
          const safeHref = href && isValidUrl(href) ? href : null;

          if (!safeHref) {
            // Render as plain text if URL is invalid
            return <span className={isUser ? "text-blue-200" : "text-[var(--text-secondary)]"}>{children}</span>;
          }

          return (
            <a
              href={safeHref}
              onClick={(e) => handleLinkClick(e, safeHref)}
              className={`underline underline-offset-2 cursor-pointer transition-colors ${
                isUser
                  ? "text-blue-200 hover:text-white"
                  : "text-blue-400 hover:text-blue-300"
              }`}
            >
              {children}
            </a>
          );
        },

        // Tables
        table: ({ children }) => (
          <div className="my-3 overflow-x-auto rounded-xl border border-[var(--border)]">
            <table className="w-full text-sm">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-[var(--bg-tertiary)]">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-4 py-2 text-left font-semibold border-b border-[var(--border)]">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-4 py-2 border-b border-[var(--border)] last:border-b-0">{processChildrenForCitations(children, 'td')}</td>
        ),

        // Horizontal Rule
        hr: () => (
          <hr className="my-4 border-[var(--border)]" />
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

interface MessageListProps {
  messages: Message[];
  loading?: boolean;
  onStartResearch?: () => void;
  onEditPlan?: () => void;
  onRecoverSynthesis?: () => void;
  showPlanButtons?: boolean;
  showRecoveryButton?: boolean;
  currentStatus?: string;
  sessionPhase?: string;
  language: Language;
}

export function MessageList({ messages, loading, onStartResearch, onEditPlan, onRecoverSynthesis, showPlanButtons, showRecoveryButton, currentStatus, sessionPhase, language }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  const prevMessagesLength = useRef(messages.length);

  // Scroll-Handler: Prüft ob User manuell hochgescrollt hat
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    // User ist "am Ende" wenn weniger als 100px vom Bottom
    setUserScrolledUp(distanceFromBottom > 100);
  };

  // Auto-Scroll nur bei NEUEN Nachrichten und wenn User nicht hochgescrollt hat
  useEffect(() => {
    const hasNewMessage = messages.length > prevMessagesLength.current;
    prevMessagesLength.current = messages.length;

    if (hasNewMessage && !userScrolledUp) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, userScrolledUp]);

  if (messages.length === 0 && !loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--text-secondary)]">
        <div className="text-center">
          <div className="text-7xl mb-6 opacity-80">🔍</div>
          <p className="text-2xl font-semibold text-[var(--text-primary)] mb-2">Lutum Veritas</p>
          <p className="text-sm opacity-70 italic">Raw. Real. Uncensored.</p>
        </div>
      </div>
    );
  }

  const lastPlanMsgIndex = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].type === "plan") return i;
    }
    return -1;
  })();

  // Finde die LÄNGSTE Assistant-Message für PDF Export (das ist die Synthesis)
  // Nur wenn phase === 'done'
  const synthesisMessageIndex = (() => {
    if (sessionPhase !== 'done') return -1;

    // Finde alle text-Assistant Messages
    const candidates: { index: number; length: number }[] = [];
    for (let i = 0; i < messages.length; i++) {
      const m = messages[i];
      if (m.role === 'assistant' && (!m.type || m.type === 'text')) {
        candidates.push({ index: i, length: m.content.length });
      }
    }

    if (candidates.length === 0) return -1;

    // Die längste ist die Synthesis
    const longest = candidates.reduce((a, b) => (b.length > a.length ? b : a));
    return longest.index;
  })();

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-6"
    >
      <div className="max-w-4xl xl:max-w-[85%] 2xl:max-w-[90%] mx-auto space-y-4 md:space-y-5">
      {messages.map((msg, index) => {
        const isPlanMessage = msg.type === "plan";
        const isLastPlan = index === lastPlanMsgIndex;
        const shouldShowButtons = isPlanMessage && isLastPlan && showPlanButtons;
        const isUser = msg.role === "user";
        const isFinalReport = index === synthesisMessageIndex;

        return (
          <div
            key={msg.id}
            className={`flex ${isUser ? "justify-end" : "justify-start"} animate-in fade-in slide-in-from-bottom-2 duration-300`}
          >
            <div
              className={`max-w-full sm:max-w-[90%] md:max-w-[85%] lg:max-w-[75%] rounded-2xl px-4 md:px-5 py-3 md:py-4 shadow-sm break-words ${
                isUser
                  ? "bg-gradient-to-br from-blue-600 to-blue-700 text-white"
                  : "bg-[var(--bg-secondary)] text-[var(--text-primary)] border border-[var(--border)]"
              }`}
            >
              {msg.url && (
                <div className="text-xs opacity-60 mb-3 truncate flex items-center gap-1.5">
                  <span>🔗</span>
                  <span>{msg.url}</span>
                </div>
              )}

              {/* Point Summary Box - Special rendering */}
              {msg.type === "log" ? (
                <div
                  className={`rounded-xl border px-4 py-3 text-sm ${
                    msg.logLevel === "error"
                      ? "border-red-500/40 bg-red-500/10 text-red-200"
                      : "border-amber-400/40 bg-amber-400/10 text-amber-200"
                  }`}
                >
                  <div className="text-xs font-semibold uppercase tracking-wide mb-2 opacity-80">
                    {msg.logLevel === "error" ? "Backend Error" : "Backend Warnung"}
                  </div>
                  <MarkdownContent content={msg.content} isUser={false} />
                </div>
              ) : msg.type === "point_summary" && msg.pointTitle ? (
                <PointSummaryBox
                  pointTitle={msg.pointTitle}
                  pointNumber={msg.pointNumber || 1}
                  totalPoints={msg.totalPoints || 1}
                  content={msg.content}
                  dossierFull={msg.dossierFull}
                  skipped={msg.skipped}
                  skipReason={msg.skipReason}
                  language={language}
                />
              ) : msg.type === "synthesis_waiting" ? (
                /* Synthesis Waiting Box - Spezielle Warteanimation */
                <div className="rounded-xl border-2 border-purple-500/30 overflow-hidden bg-gradient-to-br from-purple-500/5 to-purple-600/10 w-full">
                  <div className="px-4 py-3 bg-purple-500/10 border-b border-purple-500/20">
                    <div className="flex items-center gap-2 text-sm font-bold text-purple-400">
                      <span className="text-lg animate-spin" style={{ animationDuration: "2s" }}>🧠</span>
                      {t('finalSynthesisRunning', language)}
                      {msg.estimatedMinutes && (
                        <span className="ml-auto text-xs font-normal opacity-80">
                          ~{msg.estimatedMinutes} min
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="px-4 py-3 text-sm text-[var(--text-secondary)] leading-relaxed">
                    <MarkdownContent content={msg.content} isUser={false} />
                  </div>
                  <div className="px-4 py-2 bg-purple-500/5 border-t border-purple-500/10">
                    <div className="flex items-center gap-2 text-xs text-purple-400/70">
                      <span className="animate-pulse">●</span>
                      <span className="animate-pulse" style={{ animationDelay: "200ms" }}>●</span>
                      <span className="animate-pulse" style={{ animationDelay: "400ms" }}>●</span>
                      <span className="ml-2">{t('processing', language)}</span>
                    </div>
                  </div>
                </div>
              ) : msg.type === "sources_registry" && msg.sourceRegistry ? (
                /* Sources Registry Box - Ausklappbares Quellenverzeichnis */
                <SourcesRegistryBox registry={msg.sourceRegistry} language={language} />
              ) : (
                <>
                  {/* Markdown Content - mit ID für PDF Export wenn finaler Report */}
                  <div
                    id={isFinalReport ? "report-container" : undefined}
                    className="text-[14px] md:text-[15px] leading-relaxed break-words overflow-hidden"
                  >
                    {/* Use ReportRenderer for reports with markers, MarkdownContent for others */}
                    {isReportContent(msg.content) ? (
                      <ReportRenderer content={msg.content} />
                    ) : (
                      <MarkdownContent content={msg.content} isUser={isUser} />
                    )}
                  </div>

                  {/* Sources Box */}
                  {msg.type === "sources" && msg.sources && msg.sources.length > 0 && (
                    <SourcesBox sources={msg.sources} language={language} />
                  )}
                </>
              )}

              {/* Plan Buttons */}
              {shouldShowButtons && (
                <div className="flex gap-3 mt-5 pt-4 border-t border-[var(--border)]">
                  <button
                    onClick={onStartResearch}
                    className="flex-1 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 shadow-md hover:shadow-lg"
                  >
                    {t('letsGo', language)}
                  </button>
                  <button
                    onClick={onEditPlan}
                    className="flex-1 bg-[var(--bg-tertiary)] hover:bg-[var(--bg-hover)] text-[var(--text-primary)] px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 border border-[var(--border)]"
                  >
                    {t('editPlan', language)}
                  </button>
                </div>
              )}

              {/* Timestamp */}
              <div className={`text-xs mt-3 ${isUser ? "opacity-60" : "opacity-40"}`}>
                {msg.timestamp.toLocaleTimeString("de-DE", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </div>
            </div>
          </div>
        );
      })}

      {/* Loading Indicator - Terminal Style "Don't hide the sweat" */}
      {loading && (
        <div className="flex justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="bg-gradient-to-br from-[#0d1117] to-[#161b22] border border-[#30363d] rounded-2xl px-4 md:px-5 py-3 md:py-4 shadow-lg w-full sm:w-auto sm:min-w-[280px] sm:max-w-[500px]">
            {/* Terminal Header */}
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-[#30363d]">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
                <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
                <div className="w-3 h-3 rounded-full bg-[#27c93f]" />
              </div>
              <span className="text-xs text-[#8b949e] font-mono ml-2">deep-research</span>
            </div>

            {/* Animated Status Line */}
            <div className="font-mono text-sm">
              <div className="flex items-center gap-2">
                {/* Spinning Cog */}
                <span className="text-green-400 animate-spin" style={{ animationDuration: "1s" }}>⚙</span>
                <span className="text-green-400">$</span>
                <span className="text-[#c9d1d9]">{currentStatus || t('initializing', language)}</span>
                {/* Blinking Cursor */}
                <span className="animate-pulse text-green-400">▋</span>
              </div>

              {/* Activity Dots */}
              <div className="mt-2 flex items-center gap-1 text-xs text-[#8b949e]">
                <span className="animate-pulse" style={{ animationDelay: "0ms" }}>●</span>
                <span className="animate-pulse" style={{ animationDelay: "200ms" }}>●</span>
                <span className="animate-pulse" style={{ animationDelay: "400ms" }}>●</span>
                <span className="ml-2 opacity-60">{t('processingData', language)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recovery Button - Falls Synthesis verloren gegangen ist */}
      {showRecoveryButton && onRecoverSynthesis && (
        <div className="flex justify-center animate-in fade-in slide-in-from-bottom-2 duration-300">
          <button
            onClick={onRecoverSynthesis}
            className="flex items-center gap-2 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white px-5 py-3 rounded-xl text-sm font-semibold transition-all duration-200 shadow-md hover:shadow-lg border border-amber-500/30"
          >
            <span className="text-lg">🔄</span>
            <span>{t('restoreSynthesis', language)}</span>
          </button>
        </div>
      )}

      <div ref={bottomRef} />
      </div>
    </div>
  );
}
