/**
 * Settings Store
 * ===============
 * Verwaltet App-Einstellungen (API Key, Max Iterations, Dark Mode).
 * Persistiert in localStorage.
 */

const STORAGE_KEY = "lutum-settings";

import type { Language } from '../i18n/translations';

export interface Settings {
  apiKey: string;
  darkMode: boolean;
  modelSize: 'small' | 'large'; // Legacy - kept for backwards compatibility
  academicMode: boolean;
  workModel: string;   // Modell für Vorarbeit (Think, Pick URLs, Dossier)
  finalModel: string;  // Modell für Final Synthesis
  language: Language;  // UI + Prompt Sprache
}

const DEFAULT_SETTINGS: Settings = {
  apiKey: "",
  darkMode: true,
  modelSize: 'small',
  academicMode: false,
  workModel: "google/gemini-2.5-flash-lite-preview-09-2025",
  finalModel: "qwen/qwen3-vl-235b-a22b-instruct",
  language: 'de',
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
