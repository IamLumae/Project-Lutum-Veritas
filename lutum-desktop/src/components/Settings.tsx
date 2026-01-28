/**
 * Settings Component
 * ===================
 * Modal für App-Einstellungen.
 */

import { useState, useEffect } from "react";
import {
  Settings as SettingsType,
  loadSettings,
  saveSettings,
  applyDarkMode,
} from "../stores/settings";

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Settings({ isOpen, onClose }: SettingsProps) {
  const [settings, setSettings] = useState<SettingsType>(loadSettings());

  useEffect(() => {
    if (isOpen) {
      setSettings(loadSettings());
    }
  }, [isOpen]);

  // Live preview dark mode toggle
  const handleDarkModeChange = (isDark: boolean) => {
    setSettings((prev) => ({ ...prev, darkMode: isDark }));
    applyDarkMode(isDark);
  };

  const handleSave = () => {
    saveSettings(settings);
    onClose();
  };

  const handleCancel = () => {
    // Revert dark mode if changed
    const original = loadSettings();
    applyDarkMode(original.darkMode);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6 w-full max-w-md shadow-xl">
        <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-6">
          Einstellungen
        </h2>

        {/* API Key */}
        <div className="mb-5">
          <label className="block text-[var(--text-secondary)] text-sm mb-2">
            OpenRouter API Key
          </label>
          <input
            type="password"
            value={settings.apiKey}
            onChange={(e) =>
              setSettings({ ...settings, apiKey: e.target.value })
            }
            placeholder="sk-or-v1-..."
            className="w-full bg-[var(--bg-tertiary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[var(--text-secondary)] text-xs mt-1.5">
            Optional - überschreibt den Default-Key
          </p>
        </div>

        {/* Max Iterations */}
        <div className="mb-5">
          <label className="block text-[var(--text-secondary)] text-sm mb-2">
            Max Iterationen: {settings.maxIterations}
          </label>
          <input
            type="range"
            min="1"
            max="20"
            value={settings.maxIterations}
            onChange={(e) =>
              setSettings({
                ...settings,
                maxIterations: parseInt(e.target.value),
              })
            }
            className="w-full accent-blue-600"
          />
          <p className="text-[var(--text-secondary)] text-xs mt-1.5">
            Begrenzt API-Kosten bei komplexen Recherchen
          </p>
        </div>

        {/* Dark Mode Toggle */}
        <div className="mb-6">
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-[var(--text-secondary)] text-sm">
              Dark Mode
            </span>
            <button
              onClick={() => handleDarkModeChange(!settings.darkMode)}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                settings.darkMode ? "bg-blue-600" : "bg-[var(--bg-tertiary)]"
              }`}
            >
              <div
                className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  settings.darkMode ? "translate-x-7" : "translate-x-1"
                }`}
              />
            </button>
          </label>
        </div>

        {/* Buttons */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            Abbrechen
          </button>
          <button
            onClick={handleSave}
            className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Speichern
          </button>
        </div>
      </div>
    </div>
  );
}
