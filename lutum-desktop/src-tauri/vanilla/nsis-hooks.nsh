; NSIS Hooks für Lutum Veritas (Vanilla)
; Vanilla = User muss Python + Dependencies selbst installieren

!include "LogicLib.nsh"

; === POSTINSTALL: Hinweis auf manuelle Python-Installation ===
!macro NSIS_HOOK_POSTINSTALL
  ; Check ob Python vorhanden ist
  nsExec::ExecToStack 'python --version'
  Pop $0  ; Return code
  Pop $1  ; Output

  ${If} $0 == 0
    DetailPrint "Python gefunden: $1"
    DetailPrint ""
    DetailPrint "Bitte installiere die Dependencies manuell:"
    DetailPrint "  pip install -r requirements.txt"
    DetailPrint "  pip install camoufox[geoip]"
    DetailPrint "  python -m camoufox fetch"
  ${Else}
    DetailPrint ""
    DetailPrint "WARNUNG: Python wurde nicht gefunden!"
    DetailPrint "Bitte installiere Python 3.11+ von https://python.org/downloads"
    DetailPrint "Danach:"
    DetailPrint "  pip install -r requirements.txt"
    DetailPrint "  pip install camoufox[geoip]"
    DetailPrint "  python -m camoufox fetch"
    MessageBox MB_OK "Python wurde nicht gefunden!$\n$\nBitte installiere Python 3.11+ von python.org und dann:$\n$\npip install -r requirements.txt$\npip install camoufox[geoip]$\npython -m camoufox fetch"
  ${EndIf}
!macroend


; === PREUNINSTALL: User fragen wegen AppData ===
!macro NSIS_HOOK_PREUNINSTALL
  MessageBox MB_YESNO "Sollen auch alle gespeicherten Recherchen gelöscht werden?" IDNO skip_delete

  RMDir /r "$LOCALAPPDATA\de.lutum.veritas"
  RMDir /r "$LOCALAPPDATA\com.lutum.veritas"
  RMDir /r "$LOCALAPPDATA\com.lutum.veritas.vanilla"
  RMDir /r "$APPDATA\de.lutum.veritas"
  RMDir /r "$APPDATA\com.lutum.veritas"
  RMDir /r "$APPDATA\com.lutum.veritas.vanilla"

  skip_delete:
!macroend
