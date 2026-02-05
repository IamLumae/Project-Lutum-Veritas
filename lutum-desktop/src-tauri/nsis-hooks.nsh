; NSIS Hooks für Lutum Veritas
; Embedded Python - Camoufox wird beim ersten App-Start geladen

!include "LogicLib.nsh"

; === POSTINSTALL: Nichts mehr nötig - Backend lädt Camoufox beim Start ===
!macro NSIS_HOOK_POSTINSTALL
  ; Embedded Python + Dependencies sind im Bundle
  ; Camoufox Browser wird beim ersten App-Start automatisch heruntergeladen
  DetailPrint "Installation abgeschlossen. Camoufox Browser wird beim ersten Start geladen."
!macroend


; === PREUNINSTALL: User fragen wegen AppData ===
!macro NSIS_HOOK_PREUNINSTALL
  ; Frage User ob AppData gelöscht werden soll
  MessageBox MB_YESNO "Sollen auch alle gespeicherten Recherchen gelöscht werden?" IDNO skip_delete

  ; LocalAppData löschen (Tauri speichert hier)
  RMDir /r "$LOCALAPPDATA\de.lutum.veritas"
  RMDir /r "$LOCALAPPDATA\com.lutum.veritas"

  ; Roaming AppData auch (falls genutzt)
  RMDir /r "$APPDATA\de.lutum.veritas"
  RMDir /r "$APPDATA\com.lutum.veritas"

  skip_delete:
!macroend
