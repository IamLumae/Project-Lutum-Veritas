/**
 * ReportRenderer - Immersive Report Rendering
 * ============================================
 * Parst und rendert strukturierte Reports mit:
 * - Animierten Section Headers
 * - Klickbaren Citations
 * - Schönen Tabellen
 * - Highlight-Boxen
 * - Ausklappbarem Quellenverzeichnis
 */

import React, { useState, useMemo } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ============================================================================
// TYPES
// ============================================================================

interface Citation {
  number: number;
  url: string;
  title: string;
}

interface ParsedSection {
  emoji: string;
  title: string;
  content: string;
  level: number;
}

// ============================================================================
// PARSER FUNCTIONS
// ============================================================================

/**
 * Parst alle Sektionen mit Emoji-Markern aus dem Text.
 * Exported for potential future use in advanced section-based rendering.
 */
export function parseSections(text: string): ParsedSection[] {
  const sections: ParsedSection[] = [];
  const lines = text.split('\n');
  let currentSection: ParsedSection | null = null;
  let currentContent: string[] = [];

  // Pattern: ##+ EMOJI? TITEL
  const pattern = /^(#{2,4})\s+([^\s]*)\s*(.*)$/;

  for (const line of lines) {
    const match = line.match(pattern);

    if (match) {
      // Vorherige Sektion abschließen
      if (currentSection) {
        currentSection.content = currentContent.join('\n').trim();
        sections.push(currentSection);
        currentContent = [];
      }

      const hashes = match[1];
      const potentialEmoji = match[2];
      const rest = match[3];

      const level = hashes.length - 1;

      // Check ob zweiter Teil ein Emoji ist
      const isEmoji = potentialEmoji && /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]/u.test(potentialEmoji);

      const emoji = isEmoji ? potentialEmoji : "";
      const title = isEmoji ? rest.trim() : `${potentialEmoji} ${rest}`.trim();

      currentSection = { emoji, title, content: "", level };
    } else {
      currentContent.push(line);
    }
  }

  // Letzte Sektion abschließen
  if (currentSection) {
    currentSection.content = currentContent.join('\n').trim();
    sections.push(currentSection);
  }

  return sections;
}

/**
 * Parst das Quellenverzeichnis aus dem Text.
 * Unterstützt mehrere Formate:
 * - === SOURCES === ... === END SOURCES ===
 * - ## Quellenverzeichnis / ## Sources
 * - Inline [N] URL patterns
 */
function parseCitations(text: string): Map<number, Citation> {
  const citations = new Map<number, Citation>();

  // Format 1: === SOURCES === Block
  const sourcesMatch = text.match(/=== SOURCES ===\n([\s\S]+?)\n=== END SOURCES ===/);

  if (sourcesMatch) {
    const sourcesBlock = sourcesMatch[1];
    for (const line of sourcesBlock.trim().split('\n')) {
      const trimmedLine = line.trim();
      if (!trimmedLine) continue;

      // Format: [N] URL - Title  oder  [N] URL
      const match = trimmedLine.match(/\[(\d+)\]\s+(\S+)(?:\s+-\s+(.+))?/);
      if (match) {
        const num = parseInt(match[1], 10);
        const url = match[2].trim();
        const title = match[3]?.trim() || "";

        citations.set(num, { number: num, url, title });
      }
    }
  }

  // Format 2: ## Quellenverzeichnis oder ## Sources Section
  if (citations.size === 0) {
    const sectionMatch = text.match(/##\s*(?:📎\s*)?(?:Quellenverzeichnis|Sources|Quellen|References)\s*\n([\s\S]+?)(?=\n##|\n===|$)/i);
    if (sectionMatch) {
      const sourcesBlock = sectionMatch[1];
      for (const line of sourcesBlock.trim().split('\n')) {
        const trimmedLine = line.trim();
        if (!trimmedLine || trimmedLine.startsWith('#')) continue;

        // Format: [N] URL oder - [N] URL
        const match = trimmedLine.match(/\[(\d+)\]\s*(https?:\/\/\S+)/);
        if (match) {
          const num = parseInt(match[1], 10);
          const url = match[2].trim();
          citations.set(num, { number: num, url, title: "" });
        }
      }
    }
  }

  // Format 3: Sammle alle inline URLs die mit Citations verknüpft sind
  // z.B. "laut Studie[1] (https://example.com)"
  if (citations.size === 0) {
    // Suche nach allen [N] gefolgt von einer URL in Klammern oder direkt danach
    const inlinePattern = /\[(\d+)\](?:\s*\(?(https?:\/\/[^\s\)]+)\)?|\s*(?::|→|-)?\s*(https?:\/\/\S+))/g;
    let match;
    while ((match = inlinePattern.exec(text)) !== null) {
      const num = parseInt(match[1], 10);
      const url = (match[2] || match[3])?.trim();
      if (url && !citations.has(num)) {
        citations.set(num, { number: num, url, title: "" });
      }
    }
  }

  return citations;
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

/**
 * SectionHeader - Animierter Section Header mit Emoji und Gradient.
 * isConclusion: Spezielles Styling für die QUERVERBINDUNGEN & CONCLUSION Section.
 */
function SectionHeader({ emoji, title, level, isConclusion = false }: { emoji: string; title: string; level: number; isConclusion?: boolean }) {
  const sizeClasses = level === 1
    ? "text-xl md:text-2xl"
    : level === 2
      ? "text-lg md:text-xl"
      : "text-base md:text-lg";

  // Conclusion bekommt goldenes/oranges Gradient, normal ist purple-blue
  const textGradient = isConclusion
    ? "bg-gradient-to-r from-amber-400 via-orange-400 to-rose-400"
    : "bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400";

  const lineGradient = isConclusion
    ? "bg-gradient-to-r from-amber-500/50 via-orange-500/30 to-transparent"
    : "bg-gradient-to-r from-purple-500/50 via-blue-500/30 to-transparent";

  const borderGlow = isConclusion
    ? "ring-2 ring-amber-500/20 shadow-lg shadow-amber-500/10"
    : "";

  return (
    <div className={`flex items-center gap-3 mb-4 mt-6 first:mt-0 animate-in fade-in slide-in-from-left-4 duration-500 ${isConclusion ? "py-2 px-3 rounded-lg bg-gradient-to-r from-amber-500/5 to-orange-500/5 " + borderGlow : ""}`}>
      {emoji && (
        <span className={`${level === 1 ? "text-2xl md:text-3xl" : "text-xl md:text-2xl"} ${isConclusion ? "animate-pulse" : ""}`}>
          {emoji}
        </span>
      )}
      <h2 className={`
        font-bold text-transparent bg-clip-text
        ${textGradient}
        ${sizeClasses}
      `}>
        {title}
      </h2>
      <div className={`flex-1 h-px ${lineGradient}`} />
    </div>
  );
}

/**
 * CitationLink - Klickbarer Citation Badge.
 * Security: URL is validated before use.
 */
function CitationLink({
  number,
  citation,
  onClick
}: {
  number: number;
  citation?: Citation;
  onClick: (url: string) => void;
}) {
  const url = citation?.url || "";
  const hasValidUrl = url && isValidUrl(url);
  const title = citation?.title || (hasValidUrl ? citation?.url : `Quelle ${number}`);

  return (
    <span
      className={`
        inline-flex items-center justify-center
        w-5 h-5 mx-0.5 text-xs font-bold
        bg-blue-500/20 text-blue-400 border border-blue-500/30
        rounded
        ${hasValidUrl ? 'cursor-pointer hover:bg-blue-500/40 hover:border-blue-400/50' : 'cursor-default opacity-60'}
        transition-all duration-200
        align-super
      `}
      onClick={(e) => {
        e.stopPropagation();
        // Security: Only open validated URLs
        if (hasValidUrl) onClick(url);
      }}
      title={hasValidUrl ? title : 'URL nicht verfügbar'}
    >
      {number}
    </span>
  );
}

/**
 * HighlightBox - Styled Blockquote für > 💡 / > ⚠️ / > ❓
 */
function HighlightBox({ emoji, title, children }: { emoji: string; title: string; children: React.ReactNode }) {
  const colors = {
    "💡": {
      border: "border-green-500/50",
      bg: "bg-green-500/10",
      text: "text-green-400",
      glow: "shadow-green-500/20",
    },
    "⚠️": {
      border: "border-yellow-500/50",
      bg: "bg-yellow-500/10",
      text: "text-yellow-400",
      glow: "shadow-yellow-500/20",
    },
    "❓": {
      border: "border-purple-500/50",
      bg: "bg-purple-500/10",
      text: "text-purple-400",
      glow: "shadow-purple-500/20",
    },
  }[emoji] || {
    border: "border-blue-500/50",
    bg: "bg-blue-500/10",
    text: "text-blue-400",
    glow: "shadow-blue-500/20",
  };

  return (
    <div className={`
      my-4 p-4 rounded-xl border-l-4 ${colors.border} ${colors.bg}
      shadow-lg ${colors.glow}
      animate-in fade-in slide-in-from-left-2 duration-300
    `}>
      <div className={`flex items-center gap-2 font-semibold ${colors.text} mb-2`}>
        <span className="text-lg">{emoji}</span>
        <span>{title}</span>
      </div>
      <div className="text-[var(--text-secondary)] text-sm leading-relaxed">
        {children}
      </div>
    </div>
  );
}

/**
 * DataTable - Schön gestylte Tabelle mit Hover-Effekten.
 */
function DataTable({ children }: { children: React.ReactNode }) {
  return (
    <div className="my-4 overflow-x-auto rounded-xl border border-[var(--border)] shadow-lg animate-in fade-in duration-300">
      <table className="w-full text-sm">
        {children}
      </table>
    </div>
  );
}

/**
 * SourcesAccordion - Ausklappbares Quellenverzeichnis am Ende.
 */
function SourcesAccordion({
  citations,
  onOpenUrl
}: {
  citations: Map<number, Citation>;
  onOpenUrl: (url: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  if (citations.size === 0) return null;

  const sortedCitations = Array.from(citations.values()).sort((a, b) => a.number - b.number);

  return (
    <div className="mt-8 rounded-xl border border-purple-500/30 overflow-hidden shadow-lg animate-in fade-in slide-in-from-bottom-4 duration-500">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex justify-between items-center bg-gradient-to-r from-purple-500/10 to-blue-500/10 hover:from-purple-500/20 hover:to-blue-500/20 transition-all duration-300"
      >
        <span className="flex items-center gap-3 font-bold text-[var(--text-primary)]">
          <span className="text-xl">📎</span>
          <span>Quellenverzeichnis</span>
          <span className="text-sm font-normal text-[var(--text-secondary)]">
            ({citations.size} Quellen)
          </span>
        </span>
        <span className={`text-purple-400 transition-transform duration-300 ${expanded ? "rotate-180" : ""}`}>
          ▼
        </span>
      </button>

      {expanded && (
        <div className="border-t border-purple-500/20 divide-y divide-[var(--border)]">
          {sortedCitations.map((citation) => {
            // Security: Validate URL before rendering
            const hasValidUrl = isValidUrl(citation.url);

            return (
              <button
                key={citation.number}
                onClick={() => hasValidUrl && onOpenUrl(citation.url)}
                disabled={!hasValidUrl}
                className={`w-full p-3 flex items-start gap-3 transition-colors text-left group ${
                  hasValidUrl
                    ? 'hover:bg-[var(--bg-hover)] cursor-pointer'
                    : 'opacity-50 cursor-not-allowed'
                }`}
              >
                <span className="
                  flex-shrink-0 w-6 h-6 flex items-center justify-center
                  bg-blue-500/20 text-blue-400 text-xs font-bold rounded
                  group-hover:bg-blue-500/40 transition-colors
                ">
                  {citation.number}
                </span>
                <div className="flex-1 min-w-0 overflow-hidden">
                  <div className="text-sm text-[var(--text-primary)] group-hover:text-blue-400 transition-colors truncate">
                    {citation.title || (hasValidUrl ? getDomain(citation.url) : 'Ungültige URL')}
                  </div>
                  <div className="text-xs text-[var(--text-secondary)] truncate opacity-70">
                    {hasValidUrl ? citation.url : 'URL konnte nicht validiert werden'}
                  </div>
                </div>
                {hasValidUrl && (
                  <span className="text-[var(--text-secondary)] opacity-0 group-hover:opacity-100 transition-opacity">
                    →
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * DossierTransition - Animierte Übergangsbox zwischen Dossiers.
 */
export function DossierTransition({ from, to, total }: { from: number; to: number; total: number }) {
  return (
    <div className="my-8 flex items-center justify-center gap-4 animate-in fade-in zoom-in duration-500">
      <div className="w-12 h-12 rounded-full bg-green-500/20 border border-green-500/30 flex items-center justify-center shadow-lg shadow-green-500/20">
        <span className="text-green-400 text-xl">✓</span>
      </div>
      <div className="flex flex-col items-center">
        <span className="text-sm text-[var(--text-secondary)]">
          Dossier {from}/{total} abgeschlossen
        </span>
        <div className="flex gap-1.5 my-2">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="w-2 h-2 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 150}ms` }}
            />
          ))}
        </div>
        <span className="text-sm text-purple-400 font-medium">
          Starte Dossier {to}...
        </span>
      </div>
    </div>
  );
}

// ============================================================================
// SECURITY & HELPER FUNCTIONS
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

function getDomain(url: string): string {
  try {
    if (!isValidUrl(url)) return "Invalid URL";
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return "Invalid URL";
  }
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

interface ReportRendererProps {
  content: string;
  className?: string;
}

export function ReportRenderer({ content, className = "" }: ReportRendererProps) {
  // Parse citations einmal
  const citations = useMemo(() => parseCitations(content), [content]);

  // URL öffnen (mit Security Validation)
  const handleOpenUrl = async (url: string) => {
    // Security: Validate URL before opening
    if (!isValidUrl(url)) {
      console.warn('Blocked potentially unsafe URL:', url);
      return;
    }

    try {
      await openUrl(url);
    } catch {
      // Fallback with noopener/noreferrer for security
      window.open(url, "_blank", "noopener,noreferrer");
    }
  };

  // Content ohne Sources-Block für Rendering
  const contentWithoutSources = content.replace(
    /=== SOURCES ===[\s\S]+?=== END SOURCES ===/,
    ''
  ).replace(
    /=== END REPORT ===/,
    ''
  ).replace(
    /=== END DOSSIER ===/,
    ''
  ).trim();

  // Custom Markdown Renderer mit Citation-Support
  const renderMarkdown = (text: string) => (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Headers mit Emoji-Erkennung
        h2: ({ children }) => {
          const text = String(children);
          // Check für Emoji am Anfang
          const emojiMatch = text.match(/^([^\s]+)\s+(.+)$/);

          // Check ob es die CONCLUSION Section ist (🔮 oder Text enthält QUERVERBINDUNGEN/CONCLUSION)
          const isConclusionSection = text.includes('🔮') ||
            text.toUpperCase().includes('QUERVERBINDUNGEN') ||
            text.toUpperCase().includes('CONCLUSION');

          if (emojiMatch && /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]/u.test(emojiMatch[1])) {
            return <SectionHeader emoji={emojiMatch[1]} title={emojiMatch[2]} level={1} isConclusion={isConclusionSection} />;
          }
          return <SectionHeader emoji="" title={text} level={1} isConclusion={isConclusionSection} />;
        },
        h3: ({ children }) => {
          const text = String(children);
          const emojiMatch = text.match(/^([^\s]+)\s+(.+)$/);
          if (emojiMatch && /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]/u.test(emojiMatch[1])) {
            return <SectionHeader emoji={emojiMatch[1]} title={emojiMatch[2]} level={2} />;
          }
          return (
            <h3 className="text-base md:text-lg font-bold mb-2 mt-4 text-[var(--text-primary)]">
              {children}
            </h3>
          );
        },
        h4: ({ children }) => (
          <h4 className="text-sm md:text-base font-bold mb-2 mt-3 text-[var(--text-primary)]">
            {children}
          </h4>
        ),

        // Paragraphs mit Citation-Parsing
        p: ({ children }) => {
          // Parse inline citations [N] - auch mehrere hintereinander wie [4][7]
          const processString = (text: string, keyPrefix: string): React.ReactNode[] => {
            const parts: React.ReactNode[] = [];
            let lastIndex = 0;
            // Regex matcht einzelne oder mehrere aufeinanderfolgende Citations
            const regex = /\[(\d+)\]/g;
            let match;
            let citationCount = 0;

            while ((match = regex.exec(text)) !== null) {
              // Text vor der Citation
              if (match.index > lastIndex) {
                parts.push(text.slice(lastIndex, match.index));
              }

              // Citation Link
              const num = parseInt(match[1], 10);
              parts.push(
                <CitationLink
                  key={`${keyPrefix}-${citationCount++}`}
                  number={num}
                  citation={citations.get(num)}
                  onClick={handleOpenUrl}
                />
              );

              lastIndex = match.index + match[0].length;
            }

            // Rest des Texts
            if (lastIndex < text.length) {
              parts.push(text.slice(lastIndex));
            }

            return parts;
          };

          // Rekursiv durch alle Children gehen
          const processChildren = (child: React.ReactNode, index: number): React.ReactNode => {
            if (typeof child === 'string') {
              const processed = processString(child, `p-${index}`);
              return processed.length === 1 ? processed[0] : processed;
            }

            // Wenn es ein React Element ist, versuche dessen Children zu verarbeiten
            if (React.isValidElement(child)) {
              const childProps = child.props as { children?: React.ReactNode };
              if (childProps.children) {
                const newChildren = Array.isArray(childProps.children)
                  ? childProps.children.map((c: React.ReactNode, i: number) => processChildren(c, i))
                  : processChildren(childProps.children, 0);

                // Clone das Element mit neuen Children
                return React.cloneElement(child, {}, newChildren);
              }
            }

            return child;
          };

          const processedChildren = Array.isArray(children)
            ? children.map((child, i) => processChildren(child, i))
            : processChildren(children, 0);

          return (
            <p className="mb-3 last:mb-0 leading-relaxed text-[var(--text-secondary)]">
              {processedChildren}
            </p>
          );
        },

        // Blockquotes als Highlight-Boxen
        blockquote: ({ children }) => {
          // Extract text to detect emoji
          const textContent = String(children);
          const emojiMatch = textContent.match(/^([💡⚠️❓])\s*\*\*([^*]+)\*\*/);

          if (emojiMatch) {
            return (
              <HighlightBox emoji={emojiMatch[1]} title={emojiMatch[2]}>
                {children}
              </HighlightBox>
            );
          }

          return (
            <blockquote className="border-l-4 border-blue-500/50 pl-4 my-4 italic text-[var(--text-secondary)] bg-blue-500/5 py-2 rounded-r-lg">
              {children}
            </blockquote>
          );
        },

        // Tabellen
        table: ({ children }) => <DataTable>{children}</DataTable>,
        thead: ({ children }) => (
          <thead className="bg-gradient-to-r from-purple-500/10 to-blue-500/10">
            {children}
          </thead>
        ),
        th: ({ children }) => (
          <th className="px-3 md:px-4 py-2 md:py-3 text-left font-semibold text-[var(--text-primary)] border-b border-[var(--border)] text-xs md:text-sm">
            {children}
          </th>
        ),
        tbody: ({ children }) => <tbody>{children}</tbody>,
        tr: ({ children }) => (
          <tr className="hover:bg-[var(--bg-hover)] transition-colors">
            {children}
          </tr>
        ),
        td: ({ children }) => {
          // Parse citations in table cells
          const processString = (text: string, keyPrefix: string): React.ReactNode[] => {
            const parts: React.ReactNode[] = [];
            let lastIndex = 0;
            const regex = /\[(\d+)\]/g;
            let match;
            let citationCount = 0;

            while ((match = regex.exec(text)) !== null) {
              if (match.index > lastIndex) {
                parts.push(text.slice(lastIndex, match.index));
              }
              const num = parseInt(match[1], 10);
              parts.push(
                <CitationLink
                  key={`${keyPrefix}-${citationCount++}`}
                  number={num}
                  citation={citations.get(num)}
                  onClick={handleOpenUrl}
                />
              );
              lastIndex = match.index + match[0].length;
            }
            if (lastIndex < text.length) {
              parts.push(text.slice(lastIndex));
            }
            return parts;
          };

          const processChildren = (child: React.ReactNode, index: number): React.ReactNode => {
            if (typeof child === 'string') {
              const processed = processString(child, `td-${index}`);
              return processed.length === 1 ? processed[0] : processed;
            }
            return child;
          };

          const processedChildren = Array.isArray(children)
            ? children.map((child, i) => processChildren(child, i))
            : processChildren(children, 0);

          return (
            <td className="px-3 md:px-4 py-2 md:py-3 border-b border-[var(--border)] text-[var(--text-secondary)] text-xs md:text-sm">
              {processedChildren}
            </td>
          );
        },

        // Listen
        ul: ({ children }) => (
          <ul className="mb-3 ml-1 space-y-1.5">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-3 ml-1 space-y-1.5">{children}</ol>
        ),
        li: ({ children }) => {
          // Parse citations in list items
          const processString = (text: string, keyPrefix: string): React.ReactNode[] => {
            const parts: React.ReactNode[] = [];
            let lastIndex = 0;
            const regex = /\[(\d+)\]/g;
            let match;
            let citationCount = 0;

            while ((match = regex.exec(text)) !== null) {
              if (match.index > lastIndex) {
                parts.push(text.slice(lastIndex, match.index));
              }
              const num = parseInt(match[1], 10);
              parts.push(
                <CitationLink
                  key={`${keyPrefix}-${citationCount++}`}
                  number={num}
                  citation={citations.get(num)}
                  onClick={handleOpenUrl}
                />
              );
              lastIndex = match.index + match[0].length;
            }
            if (lastIndex < text.length) {
              parts.push(text.slice(lastIndex));
            }
            return parts;
          };

          const processChildren = (child: React.ReactNode, index: number): React.ReactNode => {
            if (typeof child === 'string') {
              const processed = processString(child, `li-${index}`);
              return processed.length === 1 ? processed[0] : processed;
            }
            if (React.isValidElement(child)) {
              const childProps = child.props as { children?: React.ReactNode };
              if (childProps.children) {
                const newChildren = Array.isArray(childProps.children)
                  ? childProps.children.map((c: React.ReactNode, i: number) => processChildren(c, i))
                  : processChildren(childProps.children, 0);
                return React.cloneElement(child, {}, newChildren);
              }
            }
            return child;
          };

          const processedChildren = Array.isArray(children)
            ? children.map((child, i) => processChildren(child, i))
            : processChildren(children, 0);

          // Check für nummerierte Liste im Format "1) Text"
          const text = String(children);
          const numberedMatch = text.match(/^(\d+)\)\s*(.+)$/);

          if (numberedMatch) {
            return (
              <li className="flex items-start gap-2">
                <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center bg-purple-500/20 text-purple-400 text-xs font-bold rounded">
                  {numberedMatch[1]}
                </span>
                <span className="flex-1 text-[var(--text-secondary)]">{processedChildren}</span>
              </li>
            );
          }

          return (
            <li className="flex items-start gap-2">
              <span className="text-blue-400 mt-1.5 text-xs flex-shrink-0">●</span>
              <span className="flex-1 text-[var(--text-secondary)]">{processedChildren}</span>
            </li>
          );
        },

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
            <code className="px-1.5 py-0.5 rounded-md text-xs md:text-sm font-mono bg-[var(--bg-tertiary)] text-[var(--accent)] break-all">
              {children}
            </code>
          );
        },
        pre: ({ children }) => <pre className="my-3">{children}</pre>,

        // Strong/Em mit Citation-Support
        strong: ({ children }) => {
          const text = String(children);
          // Check für Key-Value Format: **Key:**
          if (text.endsWith(':')) {
            return (
              <strong className="font-semibold text-purple-400">
                {children}
              </strong>
            );
          }
          return (
            <strong className="font-semibold text-[var(--text-primary)]">
              {children}
            </strong>
          );
        },
        em: ({ children }) => (
          <em className="italic opacity-90">{children}</em>
        ),

        // Links (with security validation)
        a: ({ href, children }) => {
          // Security: Validate URL before rendering as clickable
          const safeHref = href && isValidUrl(href) ? href : null;

          if (!safeHref) {
            // Render as plain text if URL is invalid
            return <span className="text-[var(--text-secondary)]">{children}</span>;
          }

          return (
            <a
              href={safeHref}
              onClick={(e) => {
                e.preventDefault();
                handleOpenUrl(safeHref);
              }}
              className="text-blue-400 hover:text-blue-300 underline underline-offset-2 cursor-pointer transition-colors"
            >
              {children}
            </a>
          );
        },

        // Horizontal Rule
        hr: () => (
          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-[var(--border)] to-transparent" />
            <span className="text-[var(--text-secondary)] opacity-30">◆</span>
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-[var(--border)] to-transparent" />
          </div>
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  );

  return (
    <div className={`report-renderer ${className}`}>
      {/* Main Content */}
      <div className="text-sm md:text-[15px] leading-relaxed">
        {renderMarkdown(contentWithoutSources)}
      </div>

      {/* Sources Accordion */}
      <SourcesAccordion citations={citations} onOpenUrl={handleOpenUrl} />
    </div>
  );
}

// Export additional components for use elsewhere
export { SectionHeader, CitationLink, HighlightBox, DataTable, SourcesAccordion };
