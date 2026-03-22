#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from zellij_common import (
    active_tab,
    find_current_session,
    find_session_metadata_file,
    format_tab_summary,
    parse_metadata,
    run,
    unique_tab_position,
    zellij_action_cmd,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rename a zellij tab, optionally selecting it by the current tab name first.",
        epilog=(
            "Examples:\n"
            "  rename-tab.py --name scratch\n"
            "  rename-tab.py --session friendly-zebra --tab openclaw-probe --name openclaw-scratch\n"
            "  rename-tab.py --session friendly-zebra --tab test --name monitor"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--session",
        help="optional zellij session name; otherwise uses the current session or the only live session",
    )
    parser.add_argument("-t", "--tab", help="tab name filter (case-insensitive substring)")
    parser.add_argument("-n", "--name", required=True, help="new tab name")
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

    if args.tab:
        tab_position = unique_tab_position(metadata, args.tab)
        tab = metadata.tabs_by_position[tab_position]
    else:
        tab = active_tab(metadata)
        if tab is None:
            raise SystemExit("Could not determine the active tab")

    origin = active_tab(metadata)
    origin_name = origin.name if origin else None

    if origin_name != tab.name:
        run(zellij_action_cmd(session, "go-to-tab-name", tab.name))

    try:
        run(zellij_action_cmd(session, "rename-tab", args.name))
    finally:
        if origin_name and origin_name != tab.name:
            run(zellij_action_cmd(session, "go-to-tab-name", origin_name))

    print(f"Renamed tab {tab.name!r} to {args.name!r} in session '{session}'")


if __name__ == "__main__":
    main()
