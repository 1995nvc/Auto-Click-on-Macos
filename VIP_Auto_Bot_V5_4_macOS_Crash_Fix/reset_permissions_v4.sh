#!/bin/bash
set -u
BUNDLE_ID="com.vipautobot.v54"
echo "Reset quyền cho $BUNDLE_ID"
tccutil reset Accessibility "$BUNDLE_ID" 2>/dev/null || true
tccutil reset ListenEvent "$BUNDLE_ID" 2>/dev/null || true
tccutil reset ScreenCapture "$BUNDLE_ID" 2>/dev/null || true
echo "Đã reset. Mở app V5.4 rồi bật lại quyền trong Privacy & Security."
