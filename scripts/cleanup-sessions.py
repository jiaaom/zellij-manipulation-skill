#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re

from zellij_common import fail, run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete all zellij sessions visible to the local zellij installation."
    )
    parser.add_argument("-y", "--yes", action="store_true", help="skip confirmation prompt")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw = run(["zellij", "list-sessions", "--no-formatting"]).stdout.splitlines()
    sessions = [re.sub(r" \[Created.*", "", line).strip() for line in raw if line.strip()]
    if not sessions:
        print("No zellij sessions found")
        return

    print("Sessions:")
    for session in sessions:
        print(f"  - {session}")

    if not args.yes:
        answer = input(f"Delete all {len(sessions)} sessions? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted")
            return

    for session in sessions:
        run(["zellij", "delete-session", "-f", session], capture_output=True)
        print(f"Deleted: {session}")


if __name__ == "__main__":
    main()
