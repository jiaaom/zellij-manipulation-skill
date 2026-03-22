#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from zellij_common import (
    current_pane_id,
    fail,
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


CONTROL_KEY_BYTES = {
    "ctrl-c": [3],
    "enter": [10],
    "esc": [27],
    "tab": [9],
    "up": [27, 91, 65],
    "down": [27, 91, 66],
    "right": [27, 91, 67],
    "left": [27, 91, 68],
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send text, bytes, or a control key to a specific zellij pane.",
        epilog=(
            "Examples:\n"
            "  send-keys.py --tab scratch --text 'echo hello'\n"
            "  send-keys.py --tab work --pane-id 2 --text 'htop'\n"
            "  send-keys.py --tab work --pane-id 2 --control enter\n"
            "  send-keys.py --tab work --pane-id 2 --control ctrl-c\n"
            "  send-keys.py --tab work --pane-id 2 --control up\n"
            "  send-keys.py --tab work --pane-id 2 --bytes 104 116 111 112 10"
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
    parser.add_argument("-p", "--pane-id", help="optional target pane id, eg. 2 or terminal_2")
    parser.add_argument("-q", "--title-query", help="optional pane title filter")
    parser.add_argument("--text", help="plain text to send")
    parser.add_argument(
        "--control",
        choices=sorted(CONTROL_KEY_BYTES),
        help="named control key to send",
    )
    parser.add_argument(
        "--bytes",
        nargs="+",
        type=int,
        help="raw byte values to send, eg. 98 116 111 112 10",
    )
    parser.add_argument(
        "--no-restore",
        action="store_true",
        help="leave focus on the target pane instead of restoring the origin pane",
    )
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
    parser = build_arg_parser()
    return parser.parse_args()


def selected_payload(args: argparse.Namespace) -> tuple[str, list[int] | str]:
    payloads = [args.text is not None, args.control is not None, args.bytes is not None]
    if sum(payloads) != 1:
        fail("Specify exactly one of --text, --control, or --bytes")
    if args.text is not None:
        return ("text", args.text)
    if args.control is not None:
        return ("bytes", CONTROL_KEY_BYTES[args.control])
    return ("bytes", args.bytes)


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

    payload_type, payload = selected_payload(args)
    origin_id = current_pane_id(session)
    try:
        if origin_id != target.normalized_id:
            from zellij_common import focus_pane

            focus_pane(session, metadata, target)
        if payload_type == "text":
            run(zellij_action_cmd(session, "write-chars", payload))
        else:
            run(zellij_action_cmd(session, "write", *[str(b) for b in payload]))
    finally:
        if not args.no_restore and origin_id != target.normalized_id:
            restore_origin(session, metadata, origin_id)

    if payload_type == "text":
        print(f"Sent text to {target.normalized_id} in tab '{args.tab}': {payload!r}")
    else:
        print(f"Sent bytes to {target.normalized_id} in tab '{args.tab}': {' '.join(str(b) for b in payload)}")


if __name__ == "__main__":
    main()
