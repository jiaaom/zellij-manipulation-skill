#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from zellij_common import (
    find_current_session,
    find_session_metadata_file,
    format_terminal_pane_summary,
    parse_metadata,
    run_zellij_action,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a new zellij tab in an existing session, optionally naming it.",
        epilog=(
            "Examples:\n"
            "  new-tab.py\n"
            "  new-tab.py --session my-session\n"
            "  new-tab.py --session my-session --name scratch"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--session",
        help="optional zellij session name; otherwise uses the only discovered session and fails if multiple sessions exist",
    )
    parser.add_argument("-n", "--name", help="optional tab name")
    parser.add_argument("--cwd", help="optional working directory for the new tab")
    return parser


def print_default_overview(parser: argparse.ArgumentParser) -> None:
    try:
        session = find_current_session()
        metadata = parse_metadata(find_session_metadata_file(session))
        print(f"Session: {session}", file=sys.stderr)
        print("Current terminal panes:", file=sys.stderr)
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
    action_args = ["new-tab"]
    if args.cwd:
        action_args.extend(["--cwd", args.cwd])
    if args.name:
        action_args.extend(["--name", args.name])

    run_zellij_action(session, *action_args)

    if args.name:
        print(f"Created new tab '{args.name}' in session '{session}'")
    else:
        print(f"Created new unnamed tab in session '{session}'")


if __name__ == "__main__":
    main()
