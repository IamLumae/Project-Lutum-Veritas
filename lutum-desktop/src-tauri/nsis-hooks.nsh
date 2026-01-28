; NSIS Hooks für Lutum Veritas
; Löscht AppData bei Deinstallation

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
