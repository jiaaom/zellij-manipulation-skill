#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from zellij_common import (
    find_current_session,
    find_session_metadata_file,
    parse_metadata,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List tabs and panes in a zellij session by reading session-metadata.kdl.",
        epilog=(
            "Examples:\n"
            "  find-panes.py\n"
            "  find-panes.py --session my-session\n"
            "  find-panes.py --tab work\n"
            "  find-panes.py --tab work --query htop"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--session",
        help="optional zellij session name; otherwise uses the current session or the only live session",
    )
    parser.add_argument("-t", "--tab", help="case-insensitive substring to filter tab names")
    parser.add_argument(
        "-q",
        "--query",
        help="case-insensitive substring to filter pane title or plugin URL",
    )
    return parser


def parse_args() -> argparse.Namespace:
    return build_arg_parser().parse_args()


def matches_filter(haystack: str, needle: str | None) -> bool:
    if not needle:
        return True
    return needle.lower() in haystack.lower()


def main() -> None:
    args = parse_args()

    session = args.session or find_current_session()
    metadata_file = find_session_metadata_file(session)
    metadata = parse_metadata(metadata_file)

    visible_tab_positions = [
        tab.position
        for tab in sorted(metadata.tabs_by_position.values(), key=lambda tab: tab.position)
        if matches_filter(tab.name, args.tab)
    ]

    print(f"Session: {session}")
    print(f"Metadata: {metadata_file}")
    print("")
    print("Tabs:")

    if visible_tab_positions:
        for tab_position in visible_tab_positions:
            tab = metadata.tabs_by_position[tab_position]
            print(f'  - pos={tab.position} active={tab.active} name="{tab.name}"')
    else:
        print("  (no matching tabs)")

    print("")
    print("Panes:")

    visible_panes = [
        pane
        for pane in metadata.panes
        if pane.tab_position in visible_tab_positions
    ]
    visible_panes = [
        pane
        for pane in visible_panes
        if matches_filter(
            f"{pane.title} {getattr(pane, 'plugin_url', '')}",
            args.query,
        )
    ]

    if not visible_panes:
        print("  (no matching panes)")
        return

    for pane in visible_panes:
        tab = metadata.tabs_by_position.get(pane.tab_position)
        tab_name = tab.name if tab else str(pane.tab_position)
        if pane.kind == "plugin":
            print(
                f'  - tab={pane.tab_position} name="{tab_name}" kind={pane.kind} '
                f'id={pane.pane_id} focused={pane.focused} title="{pane.title}"'
            )
        else:
            print(
                f'  - tab={pane.tab_position} name="{tab_name}" kind={pane.kind} '
                f'id={pane.pane_id} focused={pane.focused} title="{pane.title}"'
            )


if __name__ == "__main__":
    main()
