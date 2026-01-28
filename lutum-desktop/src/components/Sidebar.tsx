/**
 * Sidebar Component
 * ==================
 * ChatGPT-Style Session-Liste.
 */

import { useState, useEffect, useRef } from "react";
import { Session } from "../stores/sessions";

/**
 * Typewriter Hook - animiert Text Buchstabe für Buchstabe.
 */
function useTypewriter(text: string, speed: number = 50): string {
  const [displayText, setDisplayText] = useState("");
  const prevTextRef = useRef("");

  useEffect(() => {
    // Nur animieren wenn sich der Text geändert hat UND nicht "Recherche läuft..."
    if (text === prevTextRef.current || text === "Recherche läuft..." || text === "Neue Recherche") {
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
}

export function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onRenameSession,
}: SidebarProps) {
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
          <span>Neue Recherche</span>
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto px-2">
        <div className="text-xs text-[var(--text-secondary)] px-3 py-2 font-medium">
          Deine Recherchen
        </div>

        {sessions.length === 0 ? (
          <p className="text-[var(--text-secondary)] text-sm text-center p-4">
            Noch keine Recherchen
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
            Umbenennen
          </button>
          <button
            onClick={handleDelete}
            className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/20 transition-colors block"
          >
            Löschen
          </button>
        </div>
      )}
    </div>
  );
}
