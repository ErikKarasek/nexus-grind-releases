#!/bin/bash
# Starts Paperclip on this Mac, imports the Nexus Grind Ops agents the first
# time, and opens the board in the browser. Safe to run again: it skips
# whatever is already done. Paste this into Terminal (no download needed):
#   bash <(curl -fsSL https://raw.githubusercontent.com/ErikKarasek/nexus-grind-releases/main/paperclip/start-mac.command)
# or, with the file downloaded:
#   bash ~/Downloads/start-mac.command

PKG="ErikKarasek/nexus-grind-releases/paperclip/nexus-grind-ops"
API="http://127.0.0.1:3100"
HOMEDIR="$HOME/.paperclip"
MARK="$HOMEDIR/nexus-grind-ops-imported.txt"
LOG="$HOMEDIR/paperclip.log"

# 1. Node.js 24.11 or newer
if ! command -v node >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "Node.js není nainstalovaný, instaluji ho přes Homebrew..."
    brew install node || exit 1
  else
    echo "Node.js není nainstalovaný. Stáhni ho z https://nodejs.org (verze 24 nebo novější),"
    echo "nainstaluj a spusť tenhle skript znovu."
    open "https://nodejs.org"
    exit 1
  fi
fi
if ! node -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit(a>24||(a===24&&b>=11)?0:1)"; then
  echo "Paperclip potřebuje Node.js 24.11 nebo novější. Nainstalovaná verze: $(node --version)"
  echo "Aktualizuj ho (brew upgrade node, nebo nový instalátor z nodejs.org)."
  exit 1
fi

# 2. Claude Code, which the agents run on
if ! command -v claude >/dev/null 2>&1; then
  echo "Instaluji Claude Code oficiálním instalátorem..."
  curl -fsSL https://claude.ai/install.sh | bash || exit 1
  echo
  echo "Teď otevři nové okno Terminálu, napiš  claude  a projdi přihlášení. Pak spusť skript znovu."
  exit 0
fi

# 3. Start Paperclip in the background unless it is already running
mkdir -p "$HOMEDIR"
if ! curl -s -f -o /dev/null "$API/api/health"; then
  if [ -f "$HOMEDIR/instances/default/config.json" ]; then
    nohup npx -y paperclipai@latest run >>"$LOG" 2>&1 &
  else
    nohup npx -y paperclipai@latest onboard --yes >>"$LOG" 2>&1 &
  fi
  echo "Čekám, až Paperclip nastartuje. První spuštění může trvat pár minut..."
  for _ in $(seq 1 120); do
    sleep 3
    curl -s -f -o /dev/null "$API/api/health" && break
  done
  if ! curl -s -f -o /dev/null "$API/api/health"; then
    echo "Paperclip nenastartoval do 6 minut. Poslední řádky z $LOG:"
    tail -20 "$LOG"
    exit 1
  fi
fi

# 4. Import the agents once
if [ ! -f "$MARK" ]; then
  echo "Importuji agenty Nexus Grind Ops..."
  do_import() {
    npx -y paperclipai@latest company import "$PKG" --ref "$1" --target new \
      --include company,agents,projects,tasks,skills --api-base "$API" --yes
  }
  # Before the branch is merged the package exists only on the work branch.
  if do_import main || do_import claude/agent-nebo-projekt-a9bess; then
    echo imported >"$MARK"
    echo
    echo "Agenti jsou naimportovaní a zatím pozastavení. V prohlížeči nastav každému"
    echo "GH_TOKEN, dej Test Environment a pak je zapni i s rutinou \"Weekly sweep\"."
  else
    echo "Import se nepovedl, výše je chyba."
    exit 1
  fi
fi

open "$API"
echo
echo "Paperclip běží na pozadí, log je v $LOG."
echo "Po restartu Macu ho znovu spustíš tímhle skriptem."
