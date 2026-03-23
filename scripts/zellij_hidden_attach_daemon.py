#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time

from zellij_hidden_attach import clear_helper_state_if_owner, read_helper_state


STATE_FILE_GRACE_SECONDS = 2.0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Internal helper that keeps a hidden PTY-backed zellij attach client alive."
    )
    parser.add_argument("--session", required=True, help="target zellij session name")
    parser.add_argument(
        "--ttl-seconds",
        type=float,
        required=True,
        help="unused runtime hint for parent state",
    )
    parser.add_argument("--cols", type=int, required=True, help="hidden PTY width")
    parser.add_argument("--rows", type=int, required=True, help="hidden PTY height")
    return parser


def parse_args() -> argparse.Namespace:
    return build_arg_parser().parse_args()


def main() -> None:
    args = parse_args()
    helper_pid = os.getpid()
    daemon_started_at = time.monotonic()
    master_fd, slave_fd = pty.openpty()
    window_size = struct.pack("HHHH", args.rows, args.cols, 0, 0)
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, window_size)
    child = subprocess.Popen(
        ["zellij", "attach", args.session],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        start_new_session=True,
        close_fds=True,
        text=False,
    )
    os.close(slave_fd)

    def stop_child(_signum: int, _frame: object) -> None:
        if child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, stop_child)
    signal.signal(signal.SIGINT, stop_child)

    try:
        while True:
            if child.poll() is not None:
                raise SystemExit(child.returncode or 0)
            state = read_helper_state(args.session)
            if state is None:
                if time.monotonic() - daemon_started_at >= STATE_FILE_GRACE_SECONDS:
                    raise SystemExit(0)
            elif state.helper_pid != helper_pid:
                raise SystemExit(0)
            elif time.time() - state.last_used_at > state.ttl_seconds:
                raise SystemExit(0)
            readable, _, _ = select.select([master_fd], [], [], 0.5)
            if master_fd in readable:
                try:
                    if not os.read(master_fd, 65536):
                        raise SystemExit(0)
                except OSError:
                    raise SystemExit(0)
    finally:
        clear_helper_state_if_owner(args.session, helper_pid)
        try:
            os.close(master_fd)
        except OSError:
            pass
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                child.kill()


if __name__ == "__main__":
    main()
