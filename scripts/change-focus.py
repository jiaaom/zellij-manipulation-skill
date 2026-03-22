#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from zellij_common import (
    fail,
    find_current_session,
    find_session_metadata_file,
    format_tab_summary,
    format_terminal_pane_summary,
    list_terminal_panes,
    parse_metadata,
    run,
    select_target_pane,
    unique_tab_position,
    zellij_action_cmd,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Change zellij focus to a specific tab, or to a specific pane inside a tab.",
        epilog=(
            "Examples:\n"
            "  change-focus.py --tab test\n"
            "  change-focus.py --tab test --pane-id 2\n"
            "  change-focus.py --tab openclaw-renamed\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--session",
        help="optional zellij session name; otherwise uses the current session or the only live session",
    )
    parser.add_argument(
        "-t",
        "--tab",
        required=True,
        help="tab name filter (case-insensitive substring)",
    )
    parser.add_argument("-p", "--pane-id", help="optional pane id, eg. 2 or terminal_2")
    parser.add_argument("-q", "--title-query", help="optional pane title filter")
    return parser


def print_default_overview(parser: argparse.ArgumentParser) -> None:
    try:
        session = find_current_session()
        metadata = parse_metadata(find_session_metadata_file(session))
        print(f"Session: {session}", file=sys.stderr)
        print("Tabs:", file=sys.stderr)
        for line in format_tab_summary(metadata):
            print(line, file=sys.stderr)
        print("", file=sys.stderr)
        terminal_panes = list_terminal_panes(metadata)
        if terminal_panes:
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


def main() -> None:
    if len(sys.argv) == 1:
        print_default_overview(build_arg_parser())
    args = parse_args()

    session = args.session or find_current_session()
    metadata = parse_metadata(find_session_metadata_file(session))

    if args.pane_id or args.title_query:
        target = select_target_pane(
            metadata,
            kind="terminal",
            tab_query=args.tab,
            pane_id=args.pane_id,
            title_query=args.title_query,
            require_pane_id_for_multi=False,
        )
        from zellij_common import focus_pane

        focus_pane(session, metadata, target)
        print(f"Focused {target.normalized_id} in tab '{args.tab}'")
        return

    tab_position = unique_tab_position(metadata, args.tab)
    tab = metadata.tabs_by_position[tab_position]
    run(zellij_action_cmd(session, "go-to-tab-name", tab.name))

    print(f"Focused tab '{tab.name}'")


if __name__ == "__main__":
    main()
