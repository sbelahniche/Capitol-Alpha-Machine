#!/bin/zsh
set -euo pipefail

LABEL="com.capitolalpha.weekly-refresh"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
rm -f "$PLIST_PATH"
echo "Uninstalled $LABEL. The managed clone and logs were preserved."
