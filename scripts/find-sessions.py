#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re

from zellij_common import fail, run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List zellij sessions visible to the local zellij installation."
    )
    parser.add_argument("-q", "--query", help="case-insensitive substring filter")
    parser.add_argument("-c", "--current", action="store_true", help="print only the current session")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw = run(["zellij", "list-sessions", "--no-formatting"]).stdout.splitlines()
    if not raw:
        fail("No zellij sessions found")

    for line in raw:
        name = re.sub(r" \[Created.*", "", line).strip()
        if "(current)" in line:
            status = "current"
        elif "(EXITED" in line:
            status = "exited"
        else:
            status = "active"

        if args.query and args.query.lower() not in name.lower():
            continue
        if args.current and status != "current":
            continue
        print(f"{name}\t{status}")


if __name__ == "__main__":
    main()
