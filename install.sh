#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
DEST_DIR="$OPENCLAW_HOME/skills/zellij-manipulation-skill"

mkdir -p "$DEST_DIR"
rm -rf "$DEST_DIR/scripts" "$DEST_DIR/references"
cp "$SCRIPT_DIR/SKILL.md" "$DEST_DIR/"
cp -R "$SCRIPT_DIR/scripts" "$DEST_DIR/"
cp -R "$SCRIPT_DIR/references" "$DEST_DIR/"

echo "Installed skill to: $DEST_DIR"
