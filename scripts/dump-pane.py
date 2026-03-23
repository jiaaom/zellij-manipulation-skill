#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from zellij_common import (
    current_pane_id,
    fail,
    find_current_session,
    format_terminal_pane_summary,
    list_terminal_panes,
    load_session_metadata,
    find_session_metadata_file,
    parse_metadata,
    restore_origin,
    run_zellij_action,
    select_target_pane,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Dump scrollback from a zellij pane by temporarily focusing it and then restoring "
            "focus to the original pane."
        ),
        epilog=(
            "Examples:\n"
            "  dump-pane.py --session my-session --tab work --lines 80\n"
            "  dump-pane.py --session my-session --tab work --pane-id terminal_20 --lines 80\n"
            "  dump-pane.py --session my-session --tab work --title-query htop --full"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--session",
        help="optional zellij session name; otherwise uses the only discovered session and fails if multiple sessions exist",
    )
    parser.add_argument(
        "-p",
        "--pane-id",
        help="target pane id returned by find-panes.py, eg. terminal_20 or 20",
    )
    parser.add_argument(
        "-k",
        "--kind",
        default="terminal",
        choices=("terminal", "plugin"),
        help="pane kind when --pane-id is a bare integer (default: terminal)",
    )
    parser.add_argument(
        "-t",
        "--tab",
        help="tab name filter (case-insensitive substring); recommended when tab names are stable",
    )
    parser.add_argument(
        "-q", "--title-query", help="pane title filter (case-insensitive substring)"
    )
    parser.add_argument("--full", action="store_true", help="print full scrollback")
    parser.add_argument(
        "--lines",
        type=int,
        default=100,
        help="last N lines to print when --full is not set (default: 100)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="timeout for the zellij dump-screen command (default: 5.0)",
    )
    return parser


def parse_args() -> argparse.Namespace:
    return build_arg_parser().parse_args()


def print_default_overview(parser: argparse.ArgumentParser) -> None:
    try:
        session = find_current_session()
        metadata = parse_metadata(find_session_metadata_file(session))
        terminal_panes = list_terminal_panes(metadata)
        if terminal_panes:
            print(f"Session: {session}", file=sys.stderr)
            print("Multiple panes matched:", file=sys.stderr)
            for line in format_terminal_pane_summary(metadata):
                print(line, file=sys.stderr)
            print("", file=sys.stderr)
    except Exception:
        # Usage is still valuable even if discovery fails in the current context.
        pass
    parser.print_help(sys.stderr)
    raise SystemExit(0)


def dump_current_pane(session: str, timeout_seconds: float) -> str:
    dump_path = Path(tempfile.gettempdir()) / f"openclaw-zellij-dump-{os.getpid()}.txt"
    # --full is useful even for TUIs because it captures the current rendered screen buffer.
    run_zellij_action(
        session,
        "dump-screen",
        "--full",
        str(dump_path),
        timeout_seconds=timeout_seconds,
    )
    if not dump_path.exists():
        fail(
            "zellij action dump-screen returned without creating the dump file. "
            "This can happen when the target session is detached or the pane does not expose a dumpable screen buffer."
        )
    return dump_path.read_text()


def limit_lines(content: str, lines: int) -> str:
    split_lines = content.splitlines()
    while split_lines and not split_lines[-1].strip():
        split_lines.pop()
    if len(split_lines) <= lines:
        return "\n".join(split_lines) + ("\n" if split_lines else "")
    omitted = len(split_lines) - lines
    tail = split_lines[-lines:]
    return (
        f"[... {omitted} lines omitted, showing last {lines} lines ...]\n\n"
        + "\n".join(tail)
        + "\n"
    )


def main() -> None:
    if len(sys.argv) == 1:
        print_default_overview(build_arg_parser())
    args = parse_args()
    if args.lines <= 0:
        fail("--lines must be a positive integer")
    if args.timeout_seconds <= 0:
        fail("--timeout-seconds must be a positive number")

    session = args.session or find_current_session()
    metadata = load_session_metadata(session)
    target = select_target_pane(
        metadata,
        kind=args.kind,
        tab_query=args.tab,
        pane_id=args.pane_id,
        title_query=args.title_query,
        require_pane_id_for_multi=True,
    )

    origin_id = current_pane_id(session, timeout_seconds=args.timeout_seconds)
    try:
        if origin_id != target.normalized_id:
            from zellij_common import focus_pane

            focus_pane(
                session,
                metadata,
                target,
                timeout_seconds=args.timeout_seconds,
            )
        content = dump_current_pane(session, args.timeout_seconds)
    finally:
        if origin_id != target.normalized_id:
            restore_origin(
                session,
                metadata,
                origin_id,
                timeout_seconds=args.timeout_seconds,
            )

    output = content if args.full else limit_lines(content, args.lines)
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
