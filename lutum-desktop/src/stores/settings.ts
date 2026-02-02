/**
 * Settings Store
 * ===============
 * Verwaltet App-Einstellungen (API Key, Max Iterations, Dark Mode).
 * Persistiert in localStorage.
 */

const STORAGE_KEY = "lutum-settings";

import type { Language } from '../i18n/translations';

export type Provider = 'openrouter' | 'openai' | 'anthropic' | 'google' | 'huggingface';

export const PROVIDER_CONFIG: Record<Provider, { name: string; baseUrl: string; placeholder: string }> = {
  openrouter: {
    name: 'OpenRouter',
    baseUrl: 'https://openrouter.ai/api/v1/chat/completions',
    placeholder: 'sk-or-v1-...'
  },
  openai: {
    name: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1/chat/completions',
    placeholder: 'sk-...'
  },
  anthropic: {
    name: 'Anthropic',
    baseUrl: 'https://api.anthropic.com/v1/messages',
    placeholder: 'sk-ant-...'
  },
  google: {
    name: 'Google Gemini',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
    placeholder: 'AIza...'
  },
  huggingface: {
    name: 'HuggingFace',
    baseUrl: 'https://api-inference.huggingface.co/v1/chat/completions',
    placeholder: 'hf_...'
  },
};

export interface Settings {
  apiKey: string;
  darkMode: boolean;
  modelSize: 'small' | 'large'; // Legacy - kept for backwards compatibility
  academicMode: boolean;
  provider: Provider;  // API Provider
  workModel: string;   // Modell für Vorarbeit (Think, Pick URLs, Dossier)
  finalModel: string;  // Modell für Final Synthesis
  language: Language;  // UI + Prompt Sprache
  appMode: 'research' | 'ask';  // App Mode: Deep Research vs Ask Mode
}

const DEFAULT_SETTINGS: Settings = {
  apiKey: "",
  darkMode: true,
  modelSize: 'small',
  academicMode: false,
  provider: 'openrouter',
  workModel: "google/gemini-2.5-flash-lite-preview-09-2025",
  finalModel: "qwen/qwen3-vl-235b-a22b-instruct",
  language: 'de',
  appMode: 'research',
};

/**
 * Lädt Settings aus localStorage.
 */
export function loadSettings(): Settings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    }
  } catch (e) {
    console.error("Failed to load settings:", e);
  }
  return DEFAULT_SETTINGS;
}

/**
 * Speichert Settings in localStorage.
 */
export function saveSettings(settings: Settings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    // Dark Mode sofort anwenden
    applyDarkMode(settings.darkMode);
  } catch (e) {
    console.error("Failed to save settings:", e);
  }
}

/**
 * Wendet Dark Mode auf document an.
 */
export function applyDarkMode(isDark: boolean): void {
  if (isDark) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

/**
 * Initialisiert Dark Mode beim App-Start.
 */
export function initDarkMode(): void {
  const settings = loadSettings();
  applyDarkMode(settings.darkMode);
}

/**
 * Applies mode-specific color theme to document.
 */
export function applyModeTheme(mode: 'research' | 'ask'): void {
  document.documentElement.classList.remove('mode-research', 'mode-ask');
  document.documentElement.classList.add(`mode-${mode}`);
}

/**
 * Initializes mode theme on app start.
 */
export function initModeTheme(): void {
  const settings = loadSettings();
  applyModeTheme(settings.appMode);
}
