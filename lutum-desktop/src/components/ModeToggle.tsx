/**
 * ModeToggle Component
 * ====================
 * Toggles between Deep Research and Ask Mode.
 */

import { t, type Language } from "../i18n/translations";

interface ModeToggleProps {
  appMode: 'research' | 'ask';
  onToggle: () => void;
  language: Language;
}

export function ModeToggle({ appMode, onToggle, language }: ModeToggleProps) {
  return (
    <div className="flex items-center gap-2 text-sm border-r border-[var(--border)] pr-3">
      <span className={`transition-colors ${appMode === 'research' ? 'text-[var(--text-primary)] font-medium' : 'text-[var(--text-secondary)]'}`}>
        {t('deepResearch', language)}
      </span>
      <button
        onClick={onToggle}
        className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
          appMode === 'ask' ? 'bg-teal-600' : 'bg-[var(--bg-tertiary)] border border-[var(--border)]'
        }`}
        title={appMode === 'ask' ? t('askModeActive', language) : t('researchModeActive', language)}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
            appMode === 'ask' ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
      <span className={`transition-colors ${appMode === 'ask' ? 'text-[var(--text-primary)] font-medium' : 'text-[var(--text-secondary)]'}`}>
        {t('askMode', language)}
      </span>
    </div>
  );
}
