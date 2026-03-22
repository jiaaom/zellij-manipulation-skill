#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: find-sessions.sh [-q pattern] [-c]

List zellij sessions visible to the local zellij installation.

Options:
  -q, --query       case-insensitive substring to filter session names
  -c, --current     print only the current session name
  -h, --help        show this help
USAGE
}

query=""
current_only=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -q|--query)   query="${2-}"; shift 2 ;;
    -c|--current) current_only=true; shift ;;
    -h|--help)    usage; exit 0 ;;
    *)            echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if ! command -v zellij >/dev/null 2>&1; then
  echo "zellij not found in PATH" >&2
  exit 1
fi

raw_sessions="$(zellij list-sessions --no-formatting 2>/dev/null || true)"
if [[ -z "$raw_sessions" ]]; then
  echo "No zellij sessions found" >&2
  exit 1
fi

printf '%s\n' "$raw_sessions" | awk -v q="$query" -v current_only="$current_only" '
  function lower(s) {
    return tolower(s)
  }
  {
    name = $0
    sub(/ \[Created.*/, "", name)
    current = index($0, "(current)") > 0 ? "yes" : "no"
    exited = index($0, "(EXITED") > 0 ? "yes" : "no"
    status = current == "yes" ? "current" : (exited == "yes" ? "exited" : "active")
    if (q != "" && index(lower(name), lower(q)) == 0) {
      next
    }
    if (current_only == "true" && current != "yes") {
      next
    }
    printf "%s\t%s\n", name, status
  }
'
