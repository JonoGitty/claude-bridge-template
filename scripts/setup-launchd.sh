#!/bin/bash
# Setup persistent launch agents for Claude Bridge on macOS.
# This creates two launchd services that auto-start on login and auto-restart on crash:
#   1. Relay server (HTTP inbox on port 9111)
#   2. Watcher (auto-processes incoming prompts via claude -p)
#
# Usage:
#   cd /path/to/claude-bridge
#   bash scripts/setup-launchd.sh

set -e

BRIDGE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
CLAUDE_BIN=$(which claude 2>/dev/null || echo "$HOME/.local/bin/claude")
PYTHON_BIN=$(which python3 2>/dev/null || echo "/usr/bin/python3")

echo "Claude Bridge — macOS Launch Agent Setup"
echo "Bridge directory: $BRIDGE_DIR"
echo "Python: $PYTHON_BIN"
echo "Claude: $CLAUDE_BIN"
echo

# Relay server
cat > "$LAUNCH_AGENTS_DIR/com.claude.bridge-relay.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.bridge-relay</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$BRIDGE_DIR/relay/server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$BRIDGE_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$BRIDGE_DIR/relay/server.log</string>
    <key>StandardErrorPath</key>
    <string>$BRIDGE_DIR/relay/server.log</string>
</dict>
</plist>
EOF

echo "Created: $LAUNCH_AGENTS_DIR/com.claude.bridge-relay.plist"

# Watcher
cat > "$LAUNCH_AGENTS_DIR/com.claude.bridge-watcher.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.bridge-watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$BRIDGE_DIR/relay/watcher.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$BRIDGE_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>PATH</key>
        <string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$BRIDGE_DIR/relay/watcher.log</string>
    <key>StandardErrorPath</key>
    <string>$BRIDGE_DIR/relay/watcher.log</string>
</dict>
</plist>
EOF

echo "Created: $LAUNCH_AGENTS_DIR/com.claude.bridge-watcher.plist"

# Load both
launchctl load "$LAUNCH_AGENTS_DIR/com.claude.bridge-relay.plist" 2>/dev/null
launchctl load "$LAUNCH_AGENTS_DIR/com.claude.bridge-watcher.plist" 2>/dev/null

echo
echo "Both services loaded. Verify with:"
echo "  curl -s http://localhost:9111/ping"
echo "  tail -f $BRIDGE_DIR/relay/watcher.log"
