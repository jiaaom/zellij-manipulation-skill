#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from zellij_common import (
    fail,
    find_current_session,
    format_tab_summary,
    format_terminal_pane_summary,
    list_terminal_panes,
    load_session_metadata,
    find_session_metadata_file,
    parse_metadata,
    run_zellij_action,
    select_target_pane,
    unique_tab_position,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Change zellij focus to a specific tab, or to a specific pane inside a tab.",
        epilog=(
            "Examples:\n"
            "  change-focus.py --tab work\n"
            "  change-focus.py --tab work --pane-id terminal_20\n"
            "  change-focus.py --tab scratch\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--session",
        help="optional zellij session name; otherwise uses the only discovered session and fails if multiple sessions exist",
    )
    parser.add_argument(
        "-t",
        "--tab",
        required=True,
        help="tab name filter (case-insensitive substring)",
    )
    parser.add_argument(
        "-p",
        "--pane-id",
        help="optional pane id returned by find-panes.py, eg. terminal_20 or 20",
    )
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
    metadata = load_session_metadata(session)

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
    if tab_position is None:
        fail(f"No tab matched query '{args.tab}'")
    tab = metadata.tabs_by_position[tab_position]
    run_zellij_action(session, "go-to-tab-name", tab.name)

    print(f"Focused tab '{tab.name}'")


if __name__ == "__main__":
    main()
