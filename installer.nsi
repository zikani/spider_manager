!define APP_NAME "Spider Manager"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Spider Manager Team"
!define APP_EXE "SpiderManager.exe"
!define APP_WEBSITE "https://github.com/zikani/spider-manager"

Name "${APP_NAME}"
OutFile "SpiderManager-${APP_VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES\Spider Manager"
InstallDirRegKey HKLM "Software\SpiderManager" "InstallLocation"
RequestExecutionLevel admin

; Interface settings
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "resources\icons\spider_logo.ico"
!define MUI_UNICON "resources\icons\spider_logo.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

Section "Main Files" SEC01
  SetOutPath "$INSTDIR"
  File /r "dist\SpiderManager\*"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  ; Create shortcuts
  CreateDirectory "$SMPROGRAMS\Spider Manager"
  CreateShortCut "$SMPROGRAMS\Spider Manager\Spider Manager.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortCut "$SMPROGRAMS\Spider Manager\Uninstall.lnk" "$INSTDIR\uninstall.exe"
  CreateShortCut "$DESKTOP\Spider Manager.lnk" "$INSTDIR\${APP_EXE}"
  
  ; Register file associations
  WriteRegStr HKCR ".spider" "" "SpiderManager.Download"
  WriteRegStr HKCR "SpiderManager.Download" "" "Spider Manager Download"
  WriteRegStr HKCR "SpiderManager.Download\shell\open\command" "" '"$INSTDIR\${APP_EXE}" "%1"'
  WriteRegStr HKCR "SpiderManager.Download\DefaultIcon" "" "$INSTDIR\${APP_EXE},0"
  
  ; Write registry keys
  WriteRegStr HKLM "Software\SpiderManager" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\SpiderManager" "Version" "${APP_VERSION}"
  
  ; Register browser extension
  WriteRegStr HKLM "Software\SpiderManager\BrowserExtension" "Installed" "1"
  
  ; Add to PATH (optional)
  ${EnvVarUpdate} "PATH" "E" "HKLM" "$INSTDIR"
SectionEnd

Section "Start Menu Shortcut" SEC02
  ; Already created in Main Files section
SectionEnd

Section "Desktop Shortcut" SEC03
  ; Already created in Main Files section
SectionEnd

Section "Uninstall"
  ; Remove files and directories
  RMDir /r "$INSTDIR"
  RMDir /r "$SMPROGRAMS\Spider Manager"
  Delete "$DESKTOP\Spider Manager.lnk"
  
  ; Remove registry keys
  DeleteRegKey HKLM "Software\SpiderManager"
  DeleteRegKey HKCR ".spider"
  DeleteRegKey HKCR "SpiderManager.Download"
  
  ; Remove from PATH
  ${EnvVarUpdate} "PATH" "R" "HKLM" "$INSTDIR"
SectionEnd

; Function to update environment variables
!include "WinMessages.nsh"
!include "FileFunc.nsh"
!insertmacro GetParent
!insertmacro RefreshShellIcons

Function EnvVarUpdate
  Exch $1 ; $1 = environment variable value
  Exch
  Exch $0 ; $0 = environment variable name
  Exch
  Exch 2
  Exch $2 ; $2 = action (A=add, R=remove)
  Exch 2
  Push $3
  Push $4
  Push $5
  Push $6
  
  ReadRegStr $3 HKCU "Environment" $0
  ReadRegStr $4 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" $0
  
  ${If} $2 == "A"
    ${If} $3 != ""
      StrCpy $3 "$3;$1"
    ${Else}
      StrCpy $3 "$1"
    ${EndIf}
    ${If} $4 != ""
      StrCpy $4 "$4;$1"
    ${Else}
      StrCpy $4 "$1"
    ${EndIf}
  ${ElseIf} $2 == "R"
    ${If} $3 != ""
      ${WordReplace} $3 "$1" "" "+" $5
      StrCpy $3 $5
    ${EndIf}
    ${If} $4 != ""
      ${WordReplace} $4 "$1" "" "+" $5
      StrCpy $4 $5
    ${EndIf}
  ${EndIf}
  
  WriteRegStr HKCU "Environment" $0 $3
  WriteRegStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" $0 $4
  
  ${RefreshShellIcons}
  
  Pop $6
  Pop $5
  Pop $4
  Pop $3
  Pop $0
  Pop $1
FunctionEnd
