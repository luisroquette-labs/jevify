#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
install_root="$HOME/.local/share/jeviphy-outreach"
launch_agents="$HOME/Library/LaunchAgents"
label="com.luisroquette.jeviphy-outreach"
plist="$launch_agents/$label.plist"

mkdir -p "$install_root/docs/outreach" "$launch_agents"
cp "$repo_root/scripts/jeviphy_outreach_scheduler.py" "$install_root/scheduler.py"
cp "$repo_root/docs/outreach/graphify-pr-4530.md" "$install_root/docs/outreach/graphify-pr-4530.md"
cp "$repo_root/docs/outreach/claude-mem-discussion.md" "$install_root/docs/outreach/claude-mem-discussion.md"

cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array><string>/usr/bin/python3</string><string>$install_root/scheduler.py</string></array>
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>900</integer>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key><string>$HOME</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StandardOutPath</key><string>$install_root/outreach.log</string>
  <key>StandardErrorPath</key><string>$install_root/outreach-error.log</string>
</dict>
</plist>
EOF

plutil -lint "$plist"
launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$plist"
launchctl kickstart -k "gui/$(id -u)/$label"
echo "installed: $label"
