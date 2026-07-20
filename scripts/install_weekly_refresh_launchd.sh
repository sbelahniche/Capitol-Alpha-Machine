#!/bin/zsh
set -euo pipefail

LABEL="com.capitolalpha.weekly-refresh"
SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUTOMATION_HOME="${CAPITOL_ALPHA_AUTOMATION_HOME:-$HOME/Library/Application Support/CapitolAlphaWeekly}"
REPO_DIR="$AUTOMATION_HOME/repo"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs"
STDOUT_LOG="$LOG_DIR/CapitolAlphaWeeklyRefresh.log"
STDERR_LOG="$LOG_DIR/CapitolAlphaWeeklyRefresh.error.log"
PYTHON_BIN="$(command -v python3)"
REMOTE_URL="$(git -C "$SOURCE_ROOT" remote get-url origin)"

mkdir -p "$AUTOMATION_HOME" "$HOME/Library/LaunchAgents" "$LOG_DIR"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone --branch main --single-branch "$REMOTE_URL" "$REPO_DIR"
else
  git -C "$REPO_DIR" restore --staged --worktree .
  git -C "$REPO_DIR" fetch origin main
  git -C "$REPO_DIR" switch main
  if ! git -C "$REPO_DIR" pull --ff-only origin main; then
    git -C "$REPO_DIR" reset --hard origin/main
  fi
fi

git -C "$REPO_DIR" config user.name "Capitol Alpha Weekly Automation"
git -C "$REPO_DIR" config user.email "41898282+github-actions[bot]@users.noreply.github.com"

if [[ ! -f "$SOURCE_ROOT/.vercel/project.json" ]]; then
  echo "Missing $SOURCE_ROOT/.vercel/project.json; link the Vercel project first." >&2
  exit 1
fi
mkdir -p "$REPO_DIR/.vercel"
cp "$SOURCE_ROOT/.vercel/project.json" "$REPO_DIR/.vercel/project.json"

"$PYTHON_BIN" - "$PLIST_PATH" "$LABEL" "$PYTHON_BIN" "$REPO_DIR" "$AUTOMATION_HOME" "$STDOUT_LOG" "$STDERR_LOG" <<'PY'
import os
import plistlib
import sys

plist_path, label, python_bin, repo_dir, state_dir, stdout_log, stderr_log = sys.argv[1:]
payload = {
    "Label": label,
    "ProgramArguments": [
        python_bin,
        os.path.join(repo_dir, "scripts", "run_weekly_automation.py"),
        "--repo",
        repo_dir,
        "--state-dir",
        state_dir,
        "--managed-clone",
    ],
    "WorkingDirectory": repo_dir,
    "RunAtLoad": True,
    "StartCalendarInterval": {"Minute": 25},
    "ProcessType": "Background",
    "LowPriorityIO": True,
    "StandardOutPath": stdout_log,
    "StandardErrorPath": stderr_log,
    "EnvironmentVariables": {
        "HOME": os.path.expanduser("~"),
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONUNBUFFERED": "1",
    },
}
with open(plist_path, "wb") as handle:
    plistlib.dump(payload, handle, sort_keys=False)
PY

DOMAIN="gui/$(id -u)"
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST_PATH"
launchctl enable "$DOMAIN/$LABEL"
launchctl kickstart -k "$DOMAIN/$LABEL"

echo "Installed $LABEL"
echo "Managed clone: $REPO_DIR"
echo "Runs every hour at minute 25 and acts only when the current Monday is stale."
echo "Log: $STDOUT_LOG"
echo "Errors: $STDERR_LOG"
