#!/usr/bin/env bash
# Install / update / uninstall the weather-poster skill.
#
# Usage:
#   ./install.sh claude              Install or update in Claude Code (~/.claude/skills/)
#   ./install.sh openclaw            Install or update in OpenClaw (/opt/openclaw/data/workspace/skills/)
#   ./install.sh claude uninstall    Remove from Claude Code
#   ./install.sh openclaw uninstall  Remove from OpenClaw

set -euo pipefail

SKILL_NAME="weather-poster"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
OPENCLAW_SKILLS_DIR="/opt/openclaw/data/workspace/skills"

usage() {
  echo "Usage: $0 [claude|openclaw] [uninstall]"
  echo ""
  echo "  claude              Install/update to ~/.claude/skills/"
  echo "  openclaw            Install/update to /opt/openclaw/data/workspace/skills/"
  echo "  claude uninstall    Remove from Claude Code"
  echo "  openclaw uninstall  Remove from OpenClaw"
  exit 1
}

install_skill() {
  local target_dir="$1"
  local dest="$target_dir/$SKILL_NAME"
  mkdir -p "$target_dir"
  if [ -d "$dest" ]; then
    echo "Updating: $dest"
    rm -rf "$dest"
  else
    echo "Installing to: $dest"
  fi
  cp -r "$SKILL_DIR" "$dest"
  echo "Done."
  echo ""
  echo "Remember to set your API key:"
  echo "  export GEMINI_API_KEY='your-key-here'"
}

uninstall_skill() {
  local target_dir="$1"
  local dest="$target_dir/$SKILL_NAME"
  if [ -d "$dest" ]; then
    rm -rf "$dest"
    echo "Removed: $dest"
  else
    echo "Not found at: $dest (nothing to remove)"
  fi
}

[ $# -lt 1 ] && usage

TARGET="$1"
ACTION="${2:-install}"

case "$TARGET" in
  claude)   SKILLS_DIR="$CLAUDE_SKILLS_DIR" ;;
  openclaw) SKILLS_DIR="$OPENCLAW_SKILLS_DIR" ;;
  *) usage ;;
esac

case "$ACTION" in
  install|update) install_skill "$SKILLS_DIR" ;;
  uninstall)      uninstall_skill "$SKILLS_DIR" ;;
  *) usage ;;
esac
