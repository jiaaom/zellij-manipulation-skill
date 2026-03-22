#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: cleanup-sessions.sh [-y]

Delete all zellij sessions visible to the local zellij installation.

Options:
  -y, --yes         skip confirmation prompt
  -h, --help        show this help
USAGE
}

skip_confirm=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)   skip_confirm=true; shift ;;
    -h|--help)  usage; exit 0 ;;
    *)          echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if ! command -v zellij >/dev/null 2>&1; then
  echo "zellij not found in PATH" >&2
  exit 1
fi

raw_sessions="$(zellij list-sessions --no-formatting 2>/dev/null || true)"
if [[ -z "$raw_sessions" ]]; then
  echo "No zellij sessions found" >&2
  exit 0
fi

sessions="$(
  printf '%s\n' "$raw_sessions" | awk '
    {
      name = $0
      sub(/ \[Created.*/, "", name)
      print name
    }
  '
)"

session_count="$(printf '%s\n' "$sessions" | awk 'NF { count += 1 } END { print count + 0 }')"
if [[ "$session_count" -eq 0 ]]; then
  echo "No sessions to delete"
  exit 0
fi

echo "Sessions:"
printf '%s\n' "$sessions" | awk '{ printf "  - %s\n", $0 }'

if [[ "$skip_confirm" != true ]]; then
  echo ""
  read -p "Delete all ${session_count} sessions? [y/N] " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 0
  fi
fi

printf '%s\n' "$sessions" | while read -r session_name; do
  [[ -z "$session_name" ]] && continue
  echo "Deleting session: $session_name"
  zellij delete-session -f "$session_name" >/dev/null 2>&1 || true
done

echo "Done"
