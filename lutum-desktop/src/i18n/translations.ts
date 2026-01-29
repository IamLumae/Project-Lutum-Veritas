/**
 * Lutum Veritas - Internationalization
 * Supports: German (de), English (en)
 */

export type Language = 'de' | 'en';

export const translations = {
  de: {
    // Chat.tsx
    noSessionActive: "Keine Session aktiv.",
    exportOnlyWhenDone: "Export nur möglich wenn Recherche abgeschlossen ist.\nAktueller Status: ",
    noExportableMessage: "Keine exportierbare Nachricht gefunden.",
    mdExportSuccess: "Markdown erfolgreich exportiert!",
    exportFailed: "Export fehlgeschlagen: ",
    pdfExportSuccess: "PDF erfolgreich exportiert!",
    pdfExportFailed: "PDF Export fehlgeschlagen: ",
    researchRunning: "Recherche läuft...",
    researchError: "Fehler bei der Recherche",
    planCreated: "**Recherche-Plan erstellt:**\n\n",
    planFailed: "Plan konnte nicht erstellt werden.",
    planRevised: "**Recherche-Plan überarbeitet (v",
    planRevisedSuffix: "):**\n\n",
    deepResearchStarted: "**Deep Research gestartet**\n\nIch arbeite jetzt ",
    analyzing: "Analysiere ",
    finalSynthesisStarting: "**Final Synthesis startet**\n\nKombiniere ",
    researchComplete: "**Recherche abgeschlossen**\n\n- ",
    researchErrorPrefix: "**Fehler bei der Recherche:**\n\n",
    planChangePrompt: "Was möchtest du am Plan ändern? Beschreibe deine Änderungswünsche:",
    loadingLastSynthesis: "Lade letzte Synthesis aus Backup...",
    synthesisRestored: "**Synthesis erfolgreich wiederhergestellt**\n\nQuelle: `",
    synthesisLoadFailed: "**Synthesis konnte nicht geladen werden**\n\n",
    academicModeActive: "Academic Deep Research aktiv",
    connected: "Verbunden",
    offline: "Offline",
    settings: "Einstellungen",
    normal: "Normal",
    academic: "Academic",

    // Sidebar.tsx
    newResearch: "Neue Recherche",
    yourResearches: "Deine Recherchen",
    noResearchesYet: "Noch keine Recherchen",
    rename: "Umbenennen",
    delete: "Löschen",

    // Settings.tsx
    apiKeyRequired: "API Key erforderlich",
    modelsCouldNotLoad: "Modelle konnten nicht geladen werden",
    settingsTitle: "Einstellungen",
    requiredForModelSelection: "Erforderlich für Modell-Auswahl",
    modelSelection: "Modell-Auswahl",
    loadingModels: "Lade Modelle...",
    workModel: "Work Model (Vorarbeit)",
    search: "Suchen...",
    workModelHelp: "Für Think, Pick URLs, Dossier (schnell + günstig)",
    finalModel: "Final Model (Synthese)",
    finalModelHelp: "Für finale Synthese (größer = bessere Qualität)",
    modelsAvailable: "Modelle verfügbar",
    recommended: "Empfohlen",
    darkMode: "Dark Mode",
    language: "Sprache",
    cancel: "Abbrechen",
    save: "Speichern",

    // MessageList.tsx
    sourcesUsed: "Genutzte Quellen (",
    pointSkipped: "Punkt ",
    skipped: " übersprungen",
    reason: "Grund:",
    pointCompleted: "Punkt ",
    completed: " abgeschlossen",
    hideDossier: "Dossier ausblenden",
    showFullDossier: "Volles Dossier anzeigen",
    startNewResearch: "Starte eine neue Recherche",
    finalSynthesisRunning: "Final Synthesis läuft...",
    processing: "Verarbeite...",
    letsGo: "Los geht's",
    editPlan: "Plan bearbeiten",
    initializing: "Initialisiere...",
    processingData: "Verarbeite Daten...",
    restoreSynthesis: "Synthesis wiederherstellen",

    // InputBar.tsx
    startResearch: "Recherche starten...",
  },

  en: {
    // Chat.tsx
    noSessionActive: "No session active.",
    exportOnlyWhenDone: "Export only available when research is complete.\nCurrent status: ",
    noExportableMessage: "No exportable message found.",
    mdExportSuccess: "Markdown exported successfully!",
    exportFailed: "Export failed: ",
    pdfExportSuccess: "PDF exported successfully!",
    pdfExportFailed: "PDF export failed: ",
    researchRunning: "Research running...",
    researchError: "Research error",
    planCreated: "**Research Plan created:**\n\n",
    planFailed: "Could not create plan.",
    planRevised: "**Research Plan revised (v",
    planRevisedSuffix: "):**\n\n",
    deepResearchStarted: "**Deep Research started**\n\nNow working on ",
    analyzing: "Analyzing ",
    finalSynthesisStarting: "**Final Synthesis starting**\n\nCombining ",
    researchComplete: "**Research complete**\n\n- ",
    researchErrorPrefix: "**Research error:**\n\n",
    planChangePrompt: "What would you like to change about the plan? Describe your changes:",
    loadingLastSynthesis: "Loading last synthesis from backup...",
    synthesisRestored: "**Synthesis successfully restored**\n\nSource: `",
    synthesisLoadFailed: "**Could not load synthesis**\n\n",
    academicModeActive: "Academic Deep Research active",
    connected: "Connected",
    offline: "Offline",
    settings: "Settings",
    normal: "Normal",
    academic: "Academic",

    // Sidebar.tsx
    newResearch: "New Research",
    yourResearches: "Your Researches",
    noResearchesYet: "No researches yet",
    rename: "Rename",
    delete: "Delete",

    // Settings.tsx
    apiKeyRequired: "API Key required",
    modelsCouldNotLoad: "Could not load models",
    settingsTitle: "Settings",
    requiredForModelSelection: "Required for model selection",
    modelSelection: "Model Selection",
    loadingModels: "Loading models...",
    workModel: "Work Model (Preprocessing)",
    search: "Search...",
    workModelHelp: "For Think, Pick URLs, Dossier (fast + cheap)",
    finalModel: "Final Model (Synthesis)",
    finalModelHelp: "For final synthesis (larger = better quality)",
    modelsAvailable: "models available",
    recommended: "Recommended",
    darkMode: "Dark Mode",
    language: "Language",
    cancel: "Cancel",
    save: "Save",

    // MessageList.tsx
    sourcesUsed: "Sources used (",
    pointSkipped: "Point ",
    skipped: " skipped",
    reason: "Reason:",
    pointCompleted: "Point ",
    completed: " completed",
    hideDossier: "Hide dossier",
    showFullDossier: "Show full dossier",
    startNewResearch: "Start a new research",
    finalSynthesisRunning: "Final Synthesis running...",
    processing: "Processing...",
    letsGo: "Let's go",
    editPlan: "Edit plan",
    initializing: "Initializing...",
    processingData: "Processing data...",
    restoreSynthesis: "Restore synthesis",

    // InputBar.tsx
    startResearch: "Start research...",
  }
} as const;

export type TranslationKey = keyof typeof translations.de;

export function t(key: TranslationKey, lang: Language): string {
  return translations[lang][key];
}
