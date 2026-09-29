@echo off
setlocal
title Nexus Grind Ops - Paperclip

rem Starts Paperclip on this computer, imports the Nexus Grind Ops agents the
rem first time, and opens the board in the browser. Safe to run again: it
rem skips whatever is already done.

set "PKG=ErikKarasek/nexus-grind-releases/paperclip/nexus-grind-ops"
set "API=http://127.0.0.1:3100"
set "HOMEDIR=%USERPROFILE%\.paperclip"
set "MARK=%HOMEDIR%\nexus-grind-ops-imported.txt"

rem 1. Node.js 24.11 or newer
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js neni nainstalovany, instaluji ho pres winget...
  winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
  echo.
  echo Node.js je nainstalovany. Zavri toto okno a spust start-windows.bat znovu.
  pause
  exit /b 0
)
node -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit(a>24||(a===24&&b>=11)?0:1)"
if errorlevel 1 (
  echo Paperclip potrebuje Node.js 24.11 nebo novejsi. Nainstalovana verze:
  node --version
  echo Aktualizuj ho prikazem:  winget upgrade -e --id OpenJS.NodeJS.LTS
  pause
  exit /b 1
)

rem 2. Claude Code, which the agents run on
where claude >nul 2>nul
if errorlevel 1 (
  echo Instaluji Claude Code...
  call npm install -g @anthropic-ai/claude-code
  echo.
  echo Ted se jednou prihlas: otevri novy terminal, napis  claude  a projdi prihlaseni.
  echo Potom spust start-windows.bat znovu.
  pause
  exit /b 0
)

rem 3. Start Paperclip in its own window unless it is already running
curl -s -f -o nul "%API%/api/health"
if not errorlevel 1 goto up
if exist "%HOMEDIR%\instances\default\config.json" (
  start "Paperclip" cmd /k npx -y paperclipai@latest run
) else (
  start "Paperclip" cmd /k npx -y paperclipai@latest onboard --yes
)
echo Cekam, az Paperclip nastartuje. Prvni spusteni muze trvat par minut...
set /a tries=0
:wait
timeout /t 3 /nobreak >nul
curl -s -f -o nul "%API%/api/health"
if not errorlevel 1 goto up
set /a tries+=1
if %tries% lss 120 goto wait
echo Paperclip nenastartoval do 6 minut. Podivej se do okna "Paperclip", co pise.
pause
exit /b 1

:up
rem 4. Import the agents once
if exist "%MARK%" goto open
echo Importuji agenty Nexus Grind Ops...
call npx -y paperclipai@latest company import %PKG% --ref main --target new --include company,agents,projects,tasks,skills --api-base %API% --yes
if not errorlevel 1 goto imported
rem Before the branch is merged the package exists only on the work branch.
call npx -y paperclipai@latest company import %PKG% --ref claude/agent-nebo-projekt-a9bess --target new --include company,agents,projects,tasks,skills --api-base %API% --yes
if errorlevel 1 (
  echo Import se nepovedl, vyse je chyba.
  pause
  exit /b 1
)
:imported
echo imported> "%MARK%"
echo.
echo Agenti jsou naimportovani a zatim pozastaveni. V prohlizeci nastav kazdemu
echo GH_TOKEN, dej Test Environment a pak je zapni i s rutinou "Weekly sweep".

:open
start "" "%API%"
echo.
echo Paperclip bezi v okne "Paperclip". Dokud ho nezavres, agenti pracuji.
pause
