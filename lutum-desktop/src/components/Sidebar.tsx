/**
 * Sidebar Component
 * ==================
 * ChatGPT-Style Session-Liste.
 */

import { useState, useEffect, useRef } from "react";
import { Session } from "../stores/sessions";
import { openUrl } from "@tauri-apps/plugin-opener";
import logoImg from "../assets/logo.png";
import { t, type Language } from "../i18n/translations";

/**
 * Typewriter Hook - animiert Text Buchstabe für Buchstabe.
 */
function useTypewriter(text: string, speed: number = 50): string {
  const [displayText, setDisplayText] = useState("");
  const prevTextRef = useRef("");

  useEffect(() => {
    // Don't animate for status texts or new research placeholder
    const skipTexts = ["Recherche läuft...", "Neue Recherche", "Research running...", "New Research"];
    if (text === prevTextRef.current || skipTexts.includes(text)) {
      setDisplayText(text);
      return;
    }

    prevTextRef.current = text;
    setDisplayText("");

    let index = 0;
    const timer = setInterval(() => {
      if (index < text.length) {
        setDisplayText(text.slice(0, index + 1));
        index++;
      } else {
        clearInterval(timer);
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, speed]);

  return displayText;
}

interface SessionItemProps {
  session: Session;
  isActive: boolean;
  isEditing: boolean;
  editValue: string;
  onSelect: () => void;
  onContextMenu: (e: React.MouseEvent) => void;
  onEditChange: (value: string) => void;
  onEditFinish: () => void;
  onEditKeyDown: (e: React.KeyboardEvent) => void;
}

function SessionItem({
  session,
  isActive,
  isEditing,
  editValue,
  onSelect,
  onContextMenu,
  onEditChange,
  onEditFinish,
  onEditKeyDown,
}: SessionItemProps) {
  const displayTitle = useTypewriter(session.title, 40);

  return (
    <div
      className={`group flex items-center gap-2 rounded-lg px-3 py-2.5 cursor-pointer transition-colors ${
        isActive
          ? "bg-[var(--bg-tertiary)] text-[var(--text-primary)]"
          : "text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
      }`}
      onClick={() => !isEditing && onSelect()}
      onContextMenu={onContextMenu}
    >
      {isEditing ? (
        <input
          type="text"
          value={editValue}
          onChange={(e) => onEditChange(e.target.value)}
          onBlur={onEditFinish}
          onKeyDown={onEditKeyDown}
          autoFocus
          className="flex-1 bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm px-2 py-1 rounded border border-[var(--border)] outline-none focus:border-[var(--accent)]"
        />
      ) : (
        <span className="flex-1 truncate text-sm">{displayTitle}</span>
      )}
    </div>
  );
}

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  onRenameSession: (id: string, newTitle: string) => void;
  language: Language;
}

export function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onRenameSession,
  language,
}: SidebarProps) {
  const lang = language;
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    sessionId: string;
  } | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const handleContextMenu = (e: React.MouseEvent, sessionId: string) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, sessionId });
  };

  const handleCloseContextMenu = () => {
    setContextMenu(null);
  };

  const handleDelete = () => {
    if (contextMenu) {
      onDeleteSession(contextMenu.sessionId);
      setContextMenu(null);
    }
  };

  const handleStartRename = () => {
    if (contextMenu) {
      const session = sessions.find((s) => s.id === contextMenu.sessionId);
      if (session) {
        setEditingId(contextMenu.sessionId);
        setEditValue(session.title);
      }
      setContextMenu(null);
    }
  };

  const handleFinishRename = () => {
    if (editingId && editValue.trim()) {
      onRenameSession(editingId, editValue.trim());
    }
    setEditingId(null);
    setEditValue("");
  };

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleFinishRename();
    } else if (e.key === "Escape") {
      setEditingId(null);
      setEditValue("");
    }
  };

  return (
    <div
      className="w-64 min-w-[200px] flex-shrink-0 bg-[var(--bg-secondary)] border-r border-[var(--border)] flex flex-col h-full overflow-hidden"
      onClick={handleCloseContextMenu}
    >
      {/* Header - New Research Button */}
      <div className="p-3">
        <button
          onClick={onNewSession}
          className="w-full bg-transparent hover:bg-[var(--bg-tertiary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-4 py-3 flex items-center gap-3 transition-colors"
        >
          <span className="text-lg">+</span>
          <span>{t('newResearch', lang)}</span>
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto px-2 min-h-0">
        <div className="text-xs text-[var(--text-secondary)] px-3 py-2 font-medium">
          {t('yourResearches', lang)}
        </div>

        {sessions.length === 0 ? (
          <p className="text-[var(--text-secondary)] text-sm text-center p-4">
            {t('noResearchesYet', lang)}
          </p>
        ) : (
          <div className="space-y-0.5">
            {sessions
              .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
              .map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={session.id === activeSessionId}
                  isEditing={editingId === session.id}
                  editValue={editValue}
                  onSelect={() => onSelectSession(session.id)}
                  onContextMenu={(e) => handleContextMenu(e, session.id)}
                  onEditChange={setEditValue}
                  onEditFinish={handleFinishRename}
                  onEditKeyDown={handleRenameKeyDown}
                />
              ))}
          </div>
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
      {contextMenu && (
        <div
          className="fixed bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg shadow-lg py-1 z-50 min-w-[120px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={handleStartRename}
            className="w-full px-4 py-2 text-left text-sm text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors block"
          >
            {t('rename', lang)}
          </button>
          <button
            onClick={handleDelete}
            className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/20 transition-colors block"
          >
            {t('delete', lang)}
          </button>
        </div>
      )}
    </div>
  );
}
