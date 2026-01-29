/**
 * Settings Component
 * ===================
 * Modal für App-Einstellungen.
 * - API Key
 * - Work Model (Vorarbeit)
 * - Final Model (Synthese)
 * - Dark Mode
 */

import { useState, useEffect, useMemo } from "react";
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

interface OpenRouterModel {
  id: string;
  name: string;
  context_length?: number;
  pricing?: {
    prompt: string;
    completion: string;
  };
}

export function Settings({ isOpen, onClose }: SettingsProps) {
  const [settings, setSettings] = useState<SettingsType>(loadSettings());
  const [models, setModels] = useState<OpenRouterModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);

  // Search states for dropdowns
  const [workModelSearch, setWorkModelSearch] = useState("");
  const [finalModelSearch, setFinalModelSearch] = useState("");

  // Load settings when modal opens
  useEffect(() => {
    if (isOpen) {
      setSettings(loadSettings());
    }
  }, [isOpen]);

  // Fetch OpenRouter models when modal opens and API key exists
  useEffect(() => {
    if (isOpen && settings.apiKey) {
      fetchModels(settings.apiKey);
    }
  }, [isOpen, settings.apiKey]);

  const fetchModels = async (apiKey: string) => {
    if (!apiKey) {
      setModelsError("API Key erforderlich");
      return;
    }

    setModelsLoading(true);
    setModelsError(null);

    try {
      const response = await fetch("https://openrouter.ai/api/v1/models", {
        headers: {
          "Authorization": `Bearer ${apiKey}`,
        },
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();

      // Sort models by name
      const sortedModels = (data.data || []).sort((a: OpenRouterModel, b: OpenRouterModel) =>
        (a.name || a.id).localeCompare(b.name || b.id)
      );

      setModels(sortedModels);
    } catch (error) {
      console.error("Failed to fetch models:", error);
      setModelsError("Modelle konnten nicht geladen werden");
    } finally {
      setModelsLoading(false);
    }
  };

  // Filtered models for dropdowns
  const filteredWorkModels = useMemo(() => {
    if (!workModelSearch) return models;
    const search = workModelSearch.toLowerCase();
    return models.filter(m =>
      m.id.toLowerCase().includes(search) ||
      (m.name && m.name.toLowerCase().includes(search))
    );
  }, [models, workModelSearch]);

  const filteredFinalModels = useMemo(() => {
    if (!finalModelSearch) return models;
    const search = finalModelSearch.toLowerCase();
    return models.filter(m =>
      m.id.toLowerCase().includes(search) ||
      (m.name && m.name.toLowerCase().includes(search))
    );
  }, [models, finalModelSearch]);

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

  // Refresh models when API key changes
  const handleApiKeyChange = (key: string) => {
    setSettings({ ...settings, apiKey: key });
    if (key && key.startsWith("sk-")) {
      // Debounce fetch
      setTimeout(() => fetchModels(key), 500);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
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
            onChange={(e) => handleApiKeyChange(e.target.value)}
            placeholder="sk-or-v1-..."
            className="w-full bg-[var(--bg-tertiary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[var(--text-secondary)] text-xs mt-1.5">
            Erforderlich für Modell-Auswahl
          </p>
        </div>

        {/* Model Selection Section */}
        <div className="mb-5 p-4 bg-[var(--bg-tertiary)] rounded-lg border border-[var(--border)]">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
            Modell-Auswahl
          </h3>

          {modelsLoading && (
            <div className="text-[var(--text-secondary)] text-sm mb-3">
              Lade Modelle...
            </div>
          )}

          {modelsError && !models.length && (
            <div className="text-amber-400 text-sm mb-3">
              {modelsError}
            </div>
          )}

          {/* Work Model Dropdown */}
          <div className="mb-4">
            <label className="block text-[var(--text-secondary)] text-sm mb-2">
              Work Model (Vorarbeit)
            </label>
            <input
              type="text"
              value={workModelSearch}
              onChange={(e) => setWorkModelSearch(e.target.value)}
              placeholder="Suchen..."
              className="w-full bg-[var(--bg-primary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2 mb-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select
              value={settings.workModel}
              onChange={(e) => setSettings({ ...settings, workModel: e.target.value })}
              className="w-full bg-[var(--bg-primary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {/* Keep current value as option even if not in filtered list */}
              {!filteredWorkModels.find(m => m.id === settings.workModel) && (
                <option value={settings.workModel}>{settings.workModel}</option>
              )}
              {filteredWorkModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name || model.id}
                </option>
              ))}
            </select>
            <p className="text-[var(--text-secondary)] text-xs mt-1.5">
              Für Think, Pick URLs, Dossier (schnell + günstig)
            </p>
          </div>

          {/* Final Model Dropdown */}
          <div>
            <label className="block text-[var(--text-secondary)] text-sm mb-2">
              Final Model (Synthese)
            </label>
            <input
              type="text"
              value={finalModelSearch}
              onChange={(e) => setFinalModelSearch(e.target.value)}
              placeholder="Suchen..."
              className="w-full bg-[var(--bg-primary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2 mb-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select
              value={settings.finalModel}
              onChange={(e) => setSettings({ ...settings, finalModel: e.target.value })}
              className="w-full bg-[var(--bg-primary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {/* Keep current value as option even if not in filtered list */}
              {!filteredFinalModels.find(m => m.id === settings.finalModel) && (
                <option value={settings.finalModel}>{settings.finalModel}</option>
              )}
              {filteredFinalModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name || model.id}
                </option>
              ))}
            </select>
            <p className="text-[var(--text-secondary)] text-xs mt-1.5">
              Für finale Synthese (größer = bessere Qualität)
            </p>
          </div>

          {/* Models count info */}
          {models.length > 0 && (
            <div className="mt-3 text-[var(--text-secondary)] text-xs">
              {models.length} Modelle verfügbar
            </div>
          )}
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
                settings.darkMode ? "bg-blue-600" : "bg-[var(--bg-tertiary)] border border-[var(--border)]"
              }`}
            >
              <div
                className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform shadow-sm ${
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
