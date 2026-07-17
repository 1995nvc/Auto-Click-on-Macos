#!/bin/bash
set -Eeuo pipefail

APP_NAME="VIP Auto Bot V5.4"
SCRIPT_NAME="vip_auto_bot_macos_v4.py"
REQUIREMENTS_FILE="requirements_macos.txt"
BUNDLE_ID="${BUNDLE_ID:-com.vipautobot.v54}"
ICON_FILE="${ICON_FILE:-app.icns}"
CODESIGN_IDENTITY="${CODESIGN_IDENTITY:-}"
NOTARY_PROFILE="${NOTARY_PROFILE:-}"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

fail() { printf '\n❌ %s\n' "$*" >&2; exit 1; }
info() { printf '\n▶ %s\n' "$*"; }

[[ "$(uname -s)" == "Darwin" ]] || fail "Script này phải chạy trên macOS."
[[ -f "$SCRIPT_NAME" ]] || fail "Thiếu $SCRIPT_NAME"
[[ -f "$REQUIREMENTS_FILE" ]] || fail "Thiếu $REQUIREMENTS_FILE"

# Ưu tiên Python chính thức từ python.org vì có Tcl/Tk ổn định.
if [[ -n "${PYTHON_BIN:-}" ]]; then
  PY="$PYTHON_BIN"
elif [[ -x "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13" ]]; then
  PY="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13"
elif command -v python3.13 >/dev/null 2>&1; then
  PY="$(command -v python3.13)"
else
  PY="$(command -v python3 || true)"
fi
[[ -n "$PY" ]] || fail "Không tìm thấy Python 3. Hãy cài Python 3.13 từ python.org."

info "Kiểm tra Python và Tkinter"
"$PY" - <<'PY'
import sys, sysconfig
import tkinter as tk
print("Executable:", sys.executable)
print("Version:", sys.version)
print("Platform:", sysconfig.get_platform())
if sysconfig.get_config_var("Py_GIL_DISABLED"):
    raise SystemExit("Không dùng Python free-threaded để build ứng dụng này.")
root = tk.Tk()
root.withdraw()
root.update_idletasks()
print("Tk:", tk.TkVersion, "Tcl:", tk.TclVersion)
root.destroy()
PY

info "Tạo môi trường build sạch"
rm -rf .venv build dist
"$PY" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r "$REQUIREMENTS_FILE"

info "Kiểm tra dependency và cú pháp"
python - <<'PY'
import tkinter as tk
import customtkinter
import pyautogui
import pynput
import cv2
import Quartz
import AppKit
print("✅ Dependency imports OK")
root = tk.Tk(); root.withdraw(); root.update_idletasks(); root.destroy()
print("✅ Tk window test OK")
PY
python -m py_compile "$SCRIPT_NAME"

ARCH="${TARGET_ARCH:-$(uname -m)}"
case "$ARCH" in arm64|x86_64|universal2) ;; *) fail "TARGET_ARCH không hợp lệ: $ARCH" ;; esac
SAFE_NAME="${APP_NAME// /-}"
APP_PATH="$ROOT_DIR/dist/${APP_NAME}.app"
DMG_PATH="$ROOT_DIR/dist/${SAFE_NAME}-macOS-${ARCH}.dmg"
STAGING_DIR="$ROOT_DIR/build/dmg-staging"

ARGS=(
  --noconfirm --clean --windowed --onedir --noupx
  --name "$APP_NAME"
  --osx-bundle-identifier "$BUNDLE_ID"
  --target-architecture "$ARCH"
  --collect-all customtkinter
  --collect-all pyautogui
  --collect-all pyscreeze
  --collect-all mouseinfo
  --collect-all pynput
  --collect-submodules pynput
  --hidden-import pynput.keyboard._darwin
  --hidden-import pynput.mouse._darwin
  --hidden-import pynput._util.darwin
  --hidden-import Quartz
  --hidden-import AppKit
  --hidden-import Foundation
  --hidden-import objc
  --hidden-import cv2
  --hidden-import multiprocessing
  --hidden-import multiprocessing.spawn
  --hidden-import multiprocessing.popen_spawn_posix
  --hidden-import multiprocessing.resource_tracker
)

[[ -f "$ICON_FILE" ]] && ARGS+=(--icon "$ICON_FILE")
[[ -n "$CODESIGN_IDENTITY" ]] && ARGS+=(--codesign-identity "$CODESIGN_IDENTITY")

info "Build ứng dụng"
python -m PyInstaller "${ARGS[@]}" "$SCRIPT_NAME"
[[ -d "$APP_PATH" ]] || fail "Không tạo được $APP_PATH"

if [[ -z "$CODESIGN_IDENTITY" ]]; then
  codesign --force --deep --sign - "$APP_PATH"
fi
codesign --verify --deep --strict --verbose=2 "$APP_PATH"
xattr -cr "$APP_PATH" || true

info "Tạo DMG kéo-thả"
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"
ditto "$APP_PATH" "$STAGING_DIR/${APP_NAME}.app"
ln -s /Applications "$STAGING_DIR/Applications"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGING_DIR" -ov -format UDZO "$DMG_PATH"

if [[ -n "$CODESIGN_IDENTITY" ]]; then
  codesign --force --sign "$CODESIGN_IDENTITY" "$DMG_PATH"
fi

if [[ -n "$NOTARY_PROFILE" ]]; then
  [[ -n "$CODESIGN_IDENTITY" ]] || fail "Notarize yêu cầu CODESIGN_IDENTITY."
  xcrun notarytool submit "$DMG_PATH" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG_PATH"
fi

hdiutil verify "$DMG_PATH"

cat <<OUT

✅ Build hoàn tất
APP: $APP_PATH
DMG: $DMG_PATH
Bundle ID: $BUNDLE_ID

Bản V5.4 dùng tên và Bundle ID mới. Hãy cấp quyền lại cho đúng app V5.4.
Kiểm tra app không bị văng:
  ./run_app_debug_v4.sh "$APP_PATH"
OUT
