#!/usr/bin/env bash
set -euo pipefail

LABEL="com.scribed.app"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
REPO_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HOME/Library/Logs/MeetingNotes"
LOG_FILE="$LOG_DIR/watcher.log"
UV_BIN="$(command -v uv || true)"

if [ "${1:-}" = "--uninstall" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Uninstalled $LABEL"
    exit 0
fi

if [ -z "$UV_BIN" ]; then
    echo "Error: uv not found on PATH. Install uv first."
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$LOG_DIR"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${UV_BIN}</string>
        <string>run</string>
        <string>python</string>
        <string>menubar_app.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${REPO_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_FILE}</string>
    <key>StandardErrorPath</key>
    <string>${LOG_FILE}</string>
</dict>
</plist>
PLISTEOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Installed and loaded $LABEL"
echo "The menu-bar app will start now and at every login."
echo "To stop: ./install-login-item.sh --uninstall"
