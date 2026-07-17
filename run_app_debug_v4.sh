#!/bin/bash
set -u
APP_PATH="${1:-dist/VIP Auto Bot V5.4.app}"
EXE="$APP_PATH/Contents/MacOS/VIP Auto Bot V5.4"
REPORT="$HOME/Desktop/VIP-Auto-Bot-V5.4-debug.txt"
LOG_DIR="$HOME/Library/Logs/VIP Auto Bot V5.4"

{
  echo "=== VIP Auto Bot V5.4 debug ==="
  date
  echo "macOS: $(sw_vers -productVersion 2>/dev/null || true)"
  echo "Arch: $(uname -m)"
  echo "App: $APP_PATH"
  echo
  codesign -dv --verbose=4 "$APP_PATH" 2>&1 || true
  echo
  echo "=== Console output ==="
  "$EXE"
  STATUS=$?
  echo
  echo "Exit status: $STATUS"
  echo
  echo "=== startup.log ==="
  cat "$LOG_DIR/startup.log" 2>/dev/null || true
  echo
  echo "=== native-crash.log ==="
  cat "$LOG_DIR/native-crash.log" 2>/dev/null || true
  echo
  echo "=== Recent diagnostic reports ==="
  find "$HOME/Library/Logs/DiagnosticReports" -maxdepth 1 -type f \
    \( -iname '*VIP*' -o -iname '*Python*' \) -mtime -1 -print 2>/dev/null || true
} 2>&1 | tee "$REPORT"

echo "Báo cáo: $REPORT"
