; NSIS Hooks für Lutum Veritas
; Python Check + Backend Setup

!include "LogicLib.nsh"

; === POSTINSTALL: Python Check + pip install ===
!macro NSIS_HOOK_POSTINSTALL
  ; Check ob Python installiert ist
  nsExec::ExecToStack 'python --version'
  Pop $0  ; Return code
  Pop $1  ; Output

  ${If} $0 != 0
    ; Auch py launcher versuchen
    nsExec::ExecToStack 'py -3 --version'
    Pop $0
    Pop $1

    ${If} $0 != 0
      ; Python nicht gefunden
      MessageBox MB_OK "Python 3.11+ wird benötigt aber nicht gefunden.$\n$\nBitte installiere Python von python.org$\nund starte die Installation erneut.$\n$\nWICHTIG: Bei der Installation 'Add to PATH' aktivieren!"
      ExecShell "open" "https://www.python.org/downloads/"
      Goto skip_deps
    ${EndIf}
  ${EndIf}

  ; Python gefunden - pip install ausführen
  DetailPrint "Python gefunden: $1"
  DetailPrint "Installiere Backend Dependencies..."

  ; pip install (--user für Installation ohne Admin)
  nsExec::ExecToLog 'python -m pip install --user -q -r "$INSTDIR\backend\requirements.txt"'
  Pop $0

  ${If} $0 != 0
    ; Fallback: py launcher
    nsExec::ExecToLog 'py -3 -m pip install --user -q -r "$INSTDIR\backend\requirements.txt"'
    Pop $0

    ${If} $0 != 0
      MessageBox MB_OK "Dependencies Installation fehlgeschlagen.$\n$\nBitte manuell ausführen:$\npip install -r requirements.txt"
      Goto skip_deps
    ${EndIf}
  ${EndIf}

  ; Camoufox Browser Binary herunterladen (KRITISCH für Scraping!)
  DetailPrint "Lade Camoufox Browser herunter (kann 1-2 Minuten dauern)..."
  nsExec::ExecToLog 'python -m camoufox fetch'
  Pop $0

  ${If} $0 != 0
    ; Fallback: py launcher
    nsExec::ExecToLog 'py -3 -m camoufox fetch'
    Pop $0

    ${If} $0 != 0
      MessageBox MB_OK "Camoufox Browser Download fehlgeschlagen.$\n$\nBitte manuell ausführen:$\npython -m camoufox fetch"
    ${EndIf}
  ${EndIf}

  skip_deps:
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
