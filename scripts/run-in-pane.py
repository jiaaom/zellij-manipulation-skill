#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from zellij_common import (
    current_pane_id,
    find_current_session,
    find_session_metadata_file,
    format_terminal_pane_summary,
    list_terminal_panes,
    parse_metadata,
    restore_origin,
    run,
    select_target_pane,
    zellij_action_cmd,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a shell command in a specific zellij pane by sending text followed by Enter.",
        epilog=(
            "Examples:\n"
            "  run-in-pane.py --tab work --pane-id 2 -- command\n"
            "  run-in-pane.py --tab work --pane-id 2 -- htop\n"
            "  run-in-pane.py --tab work --pane-id 5 -- ls -la"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--session",
        help="optional zellij session name; otherwise uses the current session or the only live session",
    )
    parser.add_argument("-t", "--tab", required=True, help="tab name filter (case-insensitive substring)")
    parser.add_argument("-p", "--pane-id", required=True, help="target pane id, eg. 2 or terminal_2")
    parser.add_argument("-q", "--title-query", help="optional pane title filter")
    parser.add_argument(
        "--no-restore",
        action="store_true",
        help="leave focus on the target pane instead of restoring the origin pane",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command to run after --")
    return parser


def print_default_overview(parser: argparse.ArgumentParser) -> None:
    try:
        session = find_current_session()
        metadata = parse_metadata(find_session_metadata_file(session))
        terminal_panes = list_terminal_panes(metadata)
        if terminal_panes:
            print(f"Session: {session}", file=sys.stderr)
            print("Terminal panes:", file=sys.stderr)
            for line in format_terminal_pane_summary(metadata):
                print(line, file=sys.stderr)
            print("", file=sys.stderr)
    except Exception:
        pass
    parser.print_help(sys.stderr)
    raise SystemExit(0)


def parse_args() -> argparse.Namespace:
    return build_arg_parser().parse_args()


def normalized_command(parts: list[str]) -> str:
    if parts and parts[0] == "--":
        parts = parts[1:]
    if not parts:
        raise SystemExit("No command provided. Pass it after --, eg. run-in-pane.py --tab work --pane-id 2 -- htop")
    return " ".join(parts)


def main() -> None:
    if len(sys.argv) == 1:
        print_default_overview(build_arg_parser())
    args = parse_args()

    session = args.session or find_current_session()
    metadata = parse_metadata(find_session_metadata_file(session))
    target = select_target_pane(
        metadata,
        kind="terminal",
        tab_query=args.tab,
        pane_id=args.pane_id,
        title_query=args.title_query,
        require_pane_id_for_multi=False,
    )
    command = normalized_command(args.command)

    origin_id = current_pane_id(session)
    try:
        if origin_id != target.normalized_id:
            from zellij_common import focus_pane

            focus_pane(session, metadata, target)
        run(zellij_action_cmd(session, "write-chars", command))
        run(zellij_action_cmd(session, "write", "10"))
    finally:
        if not args.no_restore and origin_id != target.normalized_id:
            restore_origin(session, metadata, origin_id)

    print(f"Ran command in {target.normalized_id} in tab '{args.tab}': {command}")


if __name__ == "__main__":
    main()
