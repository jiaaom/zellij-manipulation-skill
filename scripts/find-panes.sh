#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: find-panes.sh -s session [-t tab-query] [-q pattern]

List tabs and panes in a zellij session by reading session-metadata.kdl.

Options:
  -s, --session     session name (required)
  -t, --tab         case-insensitive substring to filter tab names
  -q, --query       case-insensitive substring to filter pane title/plugin URL
  -h, --help        show this help
USAGE
}

session=""
tab_query=""
query=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--session)   session="${2-}"; shift 2 ;;
    -t|--tab)       tab_query="${2-}"; shift 2 ;;
    -q|--query)     query="${2-}"; shift 2 ;;
    -h|--help)      usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$session" ]]; then
  echo "session is required" >&2
  usage
  exit 1
fi

if ! command -v zellij >/dev/null 2>&1; then
  echo "zellij not found in PATH" >&2
  exit 1
fi

zellij_version="$(zellij --version | awk '{ print $2 }')"
candidate_dirs=(
  "${OPENCLAW_ZELLIJ_SESSION_INFO_DIR:-}"
  "$HOME/Library/Caches/org.Zellij-Contributors.zellij/$zellij_version/session_info"
  "${XDG_CACHE_HOME:-$HOME/.cache}/zellij/$zellij_version/session_info"
)

metadata_file=""
for candidate_dir in "${candidate_dirs[@]}"; do
  if [[ -n "$candidate_dir" && -f "$candidate_dir/$session/session-metadata.kdl" ]]; then
    metadata_file="$candidate_dir/$session/session-metadata.kdl"
    break
  fi
done

if [[ -z "$metadata_file" ]]; then
  echo "Could not find session-metadata.kdl for session '$session' (zellij $zellij_version)." >&2
  echo "Checked:" >&2
  for candidate_dir in "${candidate_dirs[@]}"; do
    [[ -n "$candidate_dir" ]] && echo "  - $candidate_dir/$session/session-metadata.kdl" >&2
  done
  exit 1
fi

records="$(
  awk '
    function reset_tab() {
      tab_position=""
      tab_active=""
      tab_name=""
    }
    function reset_pane() {
      pane_tab_position=""
      pane_id=""
      pane_is_plugin=""
      pane_is_focused=""
      pane_title=""
      pane_plugin_url=""
    }
    function flush_item() {
      if (item == "tab") {
        printf "TAB\t%s\t%s\t%s\n", tab_position, tab_active, tab_name
      } else if (item == "pane") {
        kind = pane_is_plugin == "true" ? "plugin" : "terminal"
        printf "PANE\t%s\t%s\t%s\t%s\t%s\t%s\n", pane_tab_position, kind, pane_id, pane_is_focused, pane_title, pane_plugin_url
      }
    }
    function unquote(value) {
      sub(/^"/, "", value)
      sub(/"$/, "", value)
      return value
    }
    {
      if ($0 ~ /^tabs[[:space:]]*{$/) {
        section="tabs"
        next
      }
      if ($0 ~ /^panes[[:space:]]*{$/) {
        section="panes"
        next
      }
      if (section == "tabs" && $0 ~ /^[[:space:]]*tab[[:space:]]*{$/) {
        item="tab"
        reset_tab()
        next
      }
      if (section == "panes" && $0 ~ /^[[:space:]]*pane[[:space:]]*{$/) {
        item="pane"
        reset_pane()
        next
      }
      if ($0 ~ /^[[:space:]]*}[[:space:]]*$/) {
        if (item != "") {
          flush_item()
          item=""
          next
        }
        if (section != "") {
          section=""
          next
        }
      }
      if (item == "tab") {
        if ($1 == "position") {
          tab_position=$2
        } else if ($1 == "active") {
          tab_active=$2
        } else if ($1 == "name") {
          line=$0
          sub(/^[[:space:]]*name[[:space:]]+/, "", line)
          tab_name=unquote(line)
        }
      } else if (item == "pane") {
        if ($1 == "tab_position") {
          pane_tab_position=$2
        } else if ($1 == "id") {
          pane_id=$2
        } else if ($1 == "is_plugin") {
          pane_is_plugin=$2
        } else if ($1 == "is_focused") {
          pane_is_focused=$2
        } else if ($1 == "title") {
          line=$0
          sub(/^[[:space:]]*title[[:space:]]+/, "", line)
          pane_title=unquote(line)
        } else if ($1 == "plugin_url") {
          line=$0
          sub(/^[[:space:]]*plugin_url[[:space:]]+/, "", line)
          pane_plugin_url=unquote(line)
        }
      }
    }
  ' "$metadata_file"
)"

declare -a tab_names=()
declare -a tab_active=()
declare -a tab_positions=()
declare -a pane_records=()

while IFS=$'\t' read -r record_type field1 field2 field3 field4 field5 field6; do
  [[ -z "$record_type" ]] && continue
  case "$record_type" in
    TAB)
      tab_names[$field1]="$field3"
      tab_active[$field1]="$field2"
      tab_positions+=("$field1")
      ;;
    PANE)
      pane_records+=("$field1"$'\t'"$field2"$'\t'"$field3"$'\t'"$field4"$'\t'"$field5"$'\t'"$field6")
      ;;
  esac
done <<< "$records"

matches_filter() {
  local haystack="$1"
  local needle="$2"
  if [[ -z "$needle" ]]; then
    return 0
  fi
  local haystack_lower needle_lower
  haystack_lower="$(printf '%s' "$haystack" | tr '[:upper:]' '[:lower:]')"
  needle_lower="$(printf '%s' "$needle" | tr '[:upper:]' '[:lower:]')"
  [[ "$haystack_lower" == *"$needle_lower"* ]]
}

declare -a show_tab=()
for tab_pos in "${tab_positions[@]}"; do
  if matches_filter "${tab_names[$tab_pos]-}" "$tab_query"; then
    show_tab[$tab_pos]="yes"
  fi
done

echo "Session: $session"
echo "Metadata: $metadata_file"
echo ""
echo "Tabs:"

printed_tabs=0
while IFS= read -r tab_pos; do
  [[ -z "$tab_pos" ]] && continue
  if [[ "${show_tab[$tab_pos]-}" != "yes" ]]; then
    continue
  fi
  printed_tabs=1
  printf '  - pos=%s active=%s name="%s"\n' "$tab_pos" "${tab_active[$tab_pos]}" "${tab_names[$tab_pos]}"
done < <(printf '%s\n' "${tab_positions[@]}" | sort -n | uniq)

if [[ "$printed_tabs" -eq 0 ]]; then
  echo "  (no matching tabs)"
fi

echo ""
echo "Panes:"

printed_panes=0
for pane_record in "${pane_records[@]}"; do
  IFS=$'\t' read -r pane_tab_pos pane_kind pane_id pane_focused pane_title pane_plugin_url <<< "$pane_record"
  if [[ "${show_tab[$pane_tab_pos]-}" != "yes" ]]; then
    continue
  fi
  if ! matches_filter "$pane_title $pane_plugin_url" "$query"; then
    continue
  fi
  printed_panes=1
  if [[ "$pane_kind" == "plugin" ]]; then
    printf '  - tab=%s name="%s" kind=%s id=%s focused=%s title="%s" plugin_url="%s"\n' \
      "$pane_tab_pos" "${tab_names[$pane_tab_pos]}" "$pane_kind" "$pane_id" "$pane_focused" "$pane_title" "$pane_plugin_url"
  else
    printf '  - tab=%s name="%s" kind=%s id=%s focused=%s title="%s"\n' \
      "$pane_tab_pos" "${tab_names[$pane_tab_pos]}" "$pane_kind" "$pane_id" "$pane_focused" "$pane_title"
  fi
done

if [[ "$printed_panes" -eq 0 ]]; then
  echo "  (no matching panes)"
fi
