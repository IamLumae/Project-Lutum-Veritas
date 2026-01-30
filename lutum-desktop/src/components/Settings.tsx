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
  Provider,
  PROVIDER_CONFIG,
} from "../stores/settings";
import { t, type Language } from "../i18n/translations";

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

// Empfohlene Modelle - werden oben in der Liste angezeigt
const RECOMMENDED_WORK_MODEL = "google/gemini-2.5-flash-lite-preview-09-2025";
const RECOMMENDED_FINAL_MODEL = "qwen/qwen3-vl-235b-a22b-instruct";

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

  // Fetch OpenRouter models when modal opens and API key exists (only for OpenRouter)
  useEffect(() => {
    if (isOpen && settings.apiKey && settings.provider === 'openrouter') {
      fetchModels(settings.apiKey);
    }
  }, [isOpen, settings.apiKey, settings.provider]);

  const lang = settings.language;

  const fetchModels = async (apiKey: string) => {
    if (!apiKey) {
      setModelsError(t('apiKeyRequired', lang));
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
      setModelsError(t('modelsCouldNotLoad', lang));
    } finally {
      setModelsLoading(false);
    }
  };

  // Filtered models for dropdowns - empfohlene Modelle zuerst
  const filteredWorkModels = useMemo(() => {
    let filtered = models;
    if (workModelSearch) {
      const search = workModelSearch.toLowerCase();
      filtered = models.filter(m =>
        m.id.toLowerCase().includes(search) ||
        (m.name && m.name.toLowerCase().includes(search))
      );
    }
    // Empfohlenes Modell nach oben sortieren
    return [...filtered].sort((a, b) => {
      if (a.id === RECOMMENDED_WORK_MODEL) return -1;
      if (b.id === RECOMMENDED_WORK_MODEL) return 1;
      return 0;
    });
  }, [models, workModelSearch]);

  const filteredFinalModels = useMemo(() => {
    let filtered = models;
    if (finalModelSearch) {
      const search = finalModelSearch.toLowerCase();
      filtered = models.filter(m =>
        m.id.toLowerCase().includes(search) ||
        (m.name && m.name.toLowerCase().includes(search))
      );
    }
    // Empfohlenes Modell nach oben sortieren
    return [...filtered].sort((a, b) => {
      if (a.id === RECOMMENDED_FINAL_MODEL) return -1;
      if (b.id === RECOMMENDED_FINAL_MODEL) return 1;
      return 0;
    });
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

  // Refresh models when API key changes (only for OpenRouter)
  const handleApiKeyChange = (key: string) => {
    setSettings({ ...settings, apiKey: key });
    if (settings.provider === 'openrouter' && key && key.startsWith("sk-")) {
      // Debounce fetch
      setTimeout(() => fetchModels(key), 500);
    }
  };

  // Handle provider change
  const handleProviderChange = (provider: Provider) => {
    setSettings({ ...settings, provider });
    // Clear models when switching away from OpenRouter
    if (provider !== 'openrouter') {
      setModels([]);
    } else if (settings.apiKey) {
      fetchModels(settings.apiKey);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-6">
          {t('settingsTitle', lang)}
        </h2>

        {/* Provider Selection */}
        <div className="mb-5">
          <label className="block text-[var(--text-secondary)] text-sm mb-2">
            Provider
          </label>
          <select
            value={settings.provider}
            onChange={(e) => handleProviderChange(e.target.value as Provider)}
            className="w-full bg-[var(--bg-tertiary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {Object.entries(PROVIDER_CONFIG).map(([key, config]) => (
              <option key={key} value={key}>{config.name}</option>
            ))}
          </select>
        </div>

        {/* API Key */}
        <div className="mb-5">
          <label className="block text-[var(--text-secondary)] text-sm mb-2">
            {PROVIDER_CONFIG[settings.provider].name} API Key
          </label>
          <input
            type="password"
            value={settings.apiKey}
            onChange={(e) => handleApiKeyChange(e.target.value)}
            placeholder={PROVIDER_CONFIG[settings.provider].placeholder}
            className="w-full bg-[var(--bg-tertiary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-[var(--text-secondary)] text-xs mt-1.5">
            {settings.provider === 'openrouter' ? t('requiredForModelSelection', lang) : 'Required for API calls'}
          </p>
        </div>

        {/* Model Selection Section */}
        <div className="mb-5 p-4 bg-[var(--bg-tertiary)] rounded-lg border border-[var(--border)]">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
            {t('modelSelection', lang)}
          </h3>

          {settings.provider === 'openrouter' ? (
            <>
              {/* OpenRouter: Dropdowns mit Suche */}
              {modelsLoading && (
                <div className="text-[var(--text-secondary)] text-sm mb-3">
                  {t('loadingModels', lang)}
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
                  {t('workModel', lang)}
                </label>
                <input
                  type="text"
                  value={workModelSearch}
                  onChange={(e) => setWorkModelSearch(e.target.value)}
                  placeholder={t('search', lang)}
                  className="w-full bg-[var(--bg-primary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2 mb-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <select
                  value={settings.workModel}
                  onChange={(e) => setSettings({ ...settings, workModel: e.target.value })}
                  className="w-full bg-[var(--bg-primary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {!filteredWorkModels.find(m => m.id === settings.workModel) && (
                    <option value={settings.workModel}>{settings.workModel}</option>
                  )}
                  {filteredWorkModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name || model.id}{model.id === RECOMMENDED_WORK_MODEL ? ` (${t('recommended', lang)})` : ''}
                    </option>
                  ))}
                </select>
                <p className="text-[var(--text-secondary)] text-xs mt-1.5">
                  {t('workModelHelp', lang)}
                </p>
              </div>

              {/* Final Model Dropdown */}
              <div>
                <label className="block text-[var(--text-secondary)] text-sm mb-2">
                  {t('finalModel', lang)}
                </label>
                <input
                  type="text"
                  value={finalModelSearch}
                  onChange={(e) => setFinalModelSearch(e.target.value)}
                  placeholder={t('search', lang)}
                  className="w-full bg-[var(--bg-primary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2 mb-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <select
                  value={settings.finalModel}
                  onChange={(e) => setSettings({ ...settings, finalModel: e.target.value })}
                  className="w-full bg-[var(--bg-primary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {!filteredFinalModels.find(m => m.id === settings.finalModel) && (
                    <option value={settings.finalModel}>{settings.finalModel}</option>
                  )}
                  {filteredFinalModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name || model.id}{model.id === RECOMMENDED_FINAL_MODEL ? ` (${t('recommended', lang)})` : ''}
                    </option>
                  ))}
                </select>
                <p className="text-[var(--text-secondary)] text-xs mt-1.5">
                  {t('finalModelHelp', lang)}
                </p>
              </div>

              {models.length > 0 && (
                <div className="mt-3 text-[var(--text-secondary)] text-xs">
                  {models.length} {t('modelsAvailable', lang)}
                </div>
              )}
            </>
          ) : (
            <>
              {/* Other Providers: Text Inputs */}
              <p className="text-[var(--text-secondary)] text-xs mb-4">
                {lang === 'de'
                  ? 'Gib die Modellnamen manuell ein (z.B. gpt-4, claude-3-opus, gemini-pro)'
                  : 'Enter model names manually (e.g. gpt-4, claude-3-opus, gemini-pro)'}
              </p>

              {/* Work Model Input */}
              <div className="mb-4">
                <label className="block text-[var(--text-secondary)] text-sm mb-2">
                  {t('workModel', lang)}
                </label>
                <input
                  type="text"
                  value={settings.workModel}
                  onChange={(e) => setSettings({ ...settings, workModel: e.target.value })}
                  placeholder="gpt-4o-mini, claude-3-haiku, gemini-1.5-flash..."
                  className="w-full bg-[var(--bg-primary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-[var(--text-secondary)] text-xs mt-1.5">
                  {t('workModelHelp', lang)}
                </p>
              </div>

              {/* Final Model Input */}
              <div>
                <label className="block text-[var(--text-secondary)] text-sm mb-2">
                  {t('finalModel', lang)}
                </label>
                <input
                  type="text"
                  value={settings.finalModel}
                  onChange={(e) => setSettings({ ...settings, finalModel: e.target.value })}
                  placeholder="gpt-4o, claude-3-opus, gemini-1.5-pro..."
                  className="w-full bg-[var(--bg-primary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-[var(--text-secondary)] text-xs mt-1.5">
                  {t('finalModelHelp', lang)}
                </p>
              </div>
            </>
          )}
        </div>

        {/* Dark Mode Toggle */}
        <div className="mb-4">
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-[var(--text-secondary)] text-sm">
              {t('darkMode', lang)}
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

        {/* Language Selector */}
        <div className="mb-6">
          <label className="flex items-center justify-between">
            <span className="text-[var(--text-secondary)] text-sm">
              {t('language', lang)}
            </span>
            <select
              value={settings.language}
              onChange={(e) => setSettings({ ...settings, language: e.target.value as Language })}
              className="bg-[var(--bg-tertiary)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="de">Deutsch</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>

        {/* Buttons */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            {t('cancel', lang)}
          </button>
          <button
            onClick={handleSave}
            className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            {t('save', lang)}
          </button>
        </div>
      </div>
    </div>
  );
}
