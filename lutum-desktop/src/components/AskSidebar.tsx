/**
 * AskSidebar Component
 * =====================
 * Sidebar for Ask Mode sessions.
 */

import { useState } from "react";
import { AskSession, formatRelativeTime } from "../stores/askSessions";
import { t, type Language } from "../i18n/translations";
import { openUrl } from "@tauri-apps/plugin-opener";
import logoImg from "../assets/logo.png";

interface AskSidebarProps {
  sessions: AskSession[];
  activeSessionId: string | null;
  language: Language;
  onSelectSession: (id: string) => void;
  onNewQuestion: () => void;
  onDeleteSession: (id: string) => void;
}

export function AskSidebar({
  sessions,
  activeSessionId,
  language,
  onSelectSession,
  onNewQuestion,
  onDeleteSession,
}: AskSidebarProps) {
  const [contextMenuSession, setContextMenuSession] = useState<string | null>(null);
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 });

  const handleContextMenu = (e: React.MouseEvent, sessionId: string) => {
    e.preventDefault();
    setContextMenuSession(sessionId);
    setMenuPos({ x: e.clientX, y: e.clientY });
  };

  const handleDelete = () => {
    if (contextMenuSession) {
      onDeleteSession(contextMenuSession);
      setContextMenuSession(null);
    }
  };

  return (
    <div className="w-64 border-r border-[var(--border)] bg-[var(--bg-secondary)] flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-[var(--border)] flex items-center justify-between">
        <span className="font-semibold text-lg text-[var(--text-primary)]">
          Ask Mode
        </span>
      </div>

      {/* New Question Button */}
      <div className="p-3">
        <button
          onClick={onNewQuestion}
          className="w-full bg-[var(--accent-active)] text-white px-4 py-2 rounded-lg font-medium hover:opacity-90 transition-opacity"
        >
          {t('newQuestion', language)}
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3">
        {sessions.length === 0 ? (
          <div className="text-[var(--text-secondary)] text-sm text-center mt-8">
            {t('noQuestionsYet', language)}
          </div>
        ) : (
          <>
            <div className="text-[var(--text-secondary)] text-xs uppercase tracking-wide mb-2 mt-2">
              {t('yourQuestions', language)}
            </div>
            <div className="space-y-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`group flex flex-col gap-1 rounded-lg px-3 py-2.5 cursor-pointer transition-colors ${
                    activeSessionId === session.id
                      ? "bg-[var(--bg-tertiary)] text-[var(--text-primary)]"
                      : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
                  }`}
                  onClick={() => onSelectSession(session.id)}
                  onContextMenu={(e) => handleContextMenu(e, session.id)}
                >
                  <span className="truncate text-sm">{session.question}</span>
                  <span className="text-xs text-[var(--text-secondary)]">
                    {formatRelativeTime(session.createdAt, language)}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Branding Panel */}
      <div className="flex-shrink-0 border-t border-[var(--border)] p-4">
        <div className="flex flex-col items-center text-center">
          {/* Logo */}
          <img
            src={logoImg}
            alt="LV Research"
            className="w-56 h-auto mb-3"
          />

          {/* Tagline */}
          <p className="text-xs text-[var(--text-secondary)] italic mb-3">
            Research Without Permission
          </p>

          {/* GitHub Link */}
          <button
            onClick={() => openUrl("https://github.com/IamLumae/Project-Lutum-Veritas")}
            className="flex items-center gap-2 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
            </svg>
            <span>View on GitHub</span>
          </button>
        </div>
      </div>

      {/* Context Menu */}
      {contextMenuSession && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setContextMenuSession(null)}
          />
          <div
            className="fixed z-50 bg-[var(--bg-primary)] border border-[var(--border)] rounded-lg shadow-lg py-1 min-w-[120px]"
            style={{ left: menuPos.x, top: menuPos.y }}
          >
            <button
              onClick={handleDelete}
              className="w-full px-4 py-2 text-left text-sm hover:bg-[var(--bg-tertiary)] text-red-500"
            >
              {t('delete', language)}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
