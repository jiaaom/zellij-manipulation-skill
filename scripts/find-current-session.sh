#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: find-current-session.sh

Print the current zellij session name.

If zellij does not mark a current session but there is exactly one live non-exited
session, that session is returned as a fallback.
USAGE
}

if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v zellij >/dev/null 2>&1; then
  echo "zellij not found in PATH" >&2
  exit 1
fi

raw_sessions="$(zellij list-sessions --no-formatting 2>/dev/null || true)"
if [[ -z "$raw_sessions" ]]; then
  echo "No zellij sessions found" >&2
  exit 1
fi

parsed_sessions="$(
  printf '%s\n' "$raw_sessions" | awk '
    {
      name=$0
      sub(/ \[Created.*/, "", name)
      current = (index($0, "(current)") > 0) ? "current" : ""
      exited = (index($0, "(EXITED") > 0) ? "exited" : ""
      status = current != "" ? current : (exited != "" ? exited : "active")
      printf "%s\t%s\n", name, status
    }
  '
)"

current_session="$(printf '%s\n' "$parsed_sessions" | awk -F'\t' '$2 == "current" { print $1; exit }')"
if [[ -n "$current_session" ]]; then
  printf '%s\n' "$current_session"
  exit 0
fi

live_sessions="$(printf '%s\n' "$parsed_sessions" | awk -F'\t' '$2 == "active" { print $1 }')"
live_count="$(printf '%s\n' "$live_sessions" | awk 'NF { count += 1 } END { print count + 0 }')"

if [[ "$live_count" -eq 1 ]]; then
  printf '%s\n' "$live_sessions"
  exit 0
fi

echo "Could not determine a unique current zellij session." >&2
echo "Sessions:" >&2
printf '%s\n' "$parsed_sessions" | awk -F'\t' '{ printf "  - %s (%s)\n", $1, $2 }' >&2
exit 1
