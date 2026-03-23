from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path


STATE_DIR = Path(tempfile.gettempdir()) / "openclaw-zellij-hidden-attach"
DEFAULT_TTL_SECONDS = 60.0
DEFAULT_START_TIMEOUT_SECONDS = 5.0
DEFAULT_PTY_COLS = 120
DEFAULT_PTY_ROWS = 40
DEFAULT_READY_SETTLE_SECONDS = 0.5
LOCK_POLL_SECONDS = 0.1


class HiddenAttachError(RuntimeError):
    pass


@dataclass(frozen=True)
class HelperState:
    version: int
    session_name: str
    backend: str
    state: str
    helper_pid: int
    started_at: float
    last_used_at: float
    ttl_seconds: float


def _run(
    args: list[str],
    *,
    capture_output: bool = True,
    timeout_seconds: float | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=check,
        text=True,
        capture_output=capture_output,
        timeout=timeout_seconds,
    )


def _session_token(session: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", session)


def _state_file(session: str) -> Path:
    return STATE_DIR / f"{_session_token(session)}.json"


def _lock_file(session: str) -> Path:
    return STATE_DIR / f"{_session_token(session)}.lock"


def _daemon_script() -> Path:
    return Path(__file__).with_name("zellij_hidden_attach_daemon.py")


def _metadata_candidates(version: str, session: str) -> list[Path]:
    home = Path.home()
    xdg_cache_home = Path(os.environ.get("XDG_CACHE_HOME", str(home / ".cache")))
    session_info_dir = os.environ.get("OPENCLAW_ZELLIJ_SESSION_INFO_DIR")
    candidates: list[Path] = []
    if session_info_dir:
        candidates.append(Path(session_info_dir) / session / "session-metadata.kdl")
    mac_cache_variants = [
        home / "Library" / "Caches" / "org.Zellij-Contributors.Zellij",
        home / "Library" / "Caches" / "org.Zellij-Contributors.zellij",
    ]
    for base in mac_cache_variants:
        candidates.append(
            base / version / "session_info" / session / "session-metadata.kdl"
        )
    candidates.append(
        xdg_cache_home
        / "zellij"
        / version
        / "session_info"
        / session
        / "session-metadata.kdl"
    )
    return candidates


def _metadata_file(session: str) -> Path | None:
    version = _run(["zellij", "--version"]).stdout.strip().split()[-1]
    for candidate in _metadata_candidates(version, session):
        if candidate.is_file():
            return candidate
    return None


def _connected_clients(session: str) -> int | None:
    metadata_file = _metadata_file(session)
    if metadata_file is None:
        return None
    for raw_line in metadata_file.read_text().splitlines():
        line = raw_line.strip()
        if line.startswith("connected_clients "):
            _, _, raw_value = line.partition(" ")
            try:
                return int(raw_value)
            except ValueError:
                return None
    return None


def _read_sessions() -> list[tuple[str, str]]:
    result = _run(["zellij", "list-sessions", "--no-formatting"]).stdout.splitlines()
    parsed: list[tuple[str, str]] = []
    for line in result:
        name = re.sub(r" \[Created.*", "", line).strip()
        if "(EXITED" in line:
            status = "exited"
        else:
            status = "active"
        parsed.append((name, status))
    return parsed


def session_exists(session: str) -> bool:
    return any(name == session for name, _ in _read_sessions())


def session_is_exited(session: str) -> bool:
    for name, status in _read_sessions():
        if name == session:
            return status == "exited"
    return False


def session_has_attached_client(session: str) -> bool:
    connected_clients = _connected_clients(session)
    return connected_clients is not None and connected_clients > 0


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_state(session: str) -> HelperState | None:
    state_file = _state_file(session)
    if not state_file.is_file():
        return None
    try:
        payload = json.loads(state_file.read_text())
        return HelperState(**payload)
    except (OSError, ValueError, TypeError):
        return None


def _write_state(state: HelperState) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = _state_file(state.session_name)
    temp_file = state_file.with_suffix(".tmp")
    temp_file.write_text(json.dumps(asdict(state), sort_keys=True, indent=2))
    temp_file.replace(state_file)


def _clear_state(session: str) -> None:
    state_file = _state_file(session)
    if state_file.exists():
        state_file.unlink()


def _terminate_process(pid: int) -> None:
    if not _pid_is_alive(pid):
        return
    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if not _pid_is_alive(pid):
            return
        time.sleep(0.05)
    if _pid_is_alive(pid):
        os.kill(pid, signal.SIGKILL)


@contextmanager
def _session_lock(session: str, *, timeout_seconds: float = 5.0):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = _lock_file(session)
    deadline = time.time() + timeout_seconds
    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except FileExistsError:
            if time.time() >= deadline:
                raise HiddenAttachError(
                    f"Timed out while waiting for hidden attach lock for session '{session}'."
                )
            time.sleep(LOCK_POLL_SECONDS)
    try:
        yield
    finally:
        os.close(fd)
        if lock_file.exists():
            lock_file.unlink()


def _spawn_daemon(session: str, ttl_seconds: float) -> int:
    cols = int(os.environ.get("OPENCLAW_ZELLIJ_HELPER_COLS", DEFAULT_PTY_COLS))
    rows = int(os.environ.get("OPENCLAW_ZELLIJ_HELPER_ROWS", DEFAULT_PTY_ROWS))
    command = [
        sys.executable,
        str(_daemon_script()),
        "--session",
        session,
        "--ttl-seconds",
        str(ttl_seconds),
        "--cols",
        str(cols),
        "--rows",
        str(rows),
    ]
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
        text=False,
    )
    return process.pid


def _reap_if_stale(session: str, state: HelperState | None) -> None:
    if state is None:
        return
    if not _pid_is_alive(state.helper_pid):
        _clear_state(session)
        return
    if time.time() - state.last_used_at <= state.ttl_seconds:
        return
    _terminate_process(state.helper_pid)
    _clear_state(session)


def ensure_hidden_attach(session: str) -> None:
    if not session_exists(session):
        raise HiddenAttachError(f"No zellij session named '{session}' exists.")
    if session_is_exited(session):
        raise HiddenAttachError(
            f"Session '{session}' is in EXITED/attach-to-resurrect state. "
            "The hidden attach helper only supports live sessions."
        )
    if session_has_attached_client(session):
        return

    ttl_seconds = float(
        os.environ.get("OPENCLAW_ZELLIJ_HELPER_TTL_SECONDS", DEFAULT_TTL_SECONDS)
    )
    start_timeout_seconds = float(
        os.environ.get(
            "OPENCLAW_ZELLIJ_HELPER_START_TIMEOUT_SECONDS",
            DEFAULT_START_TIMEOUT_SECONDS,
        )
    )

    with _session_lock(session):
        existing_state = _read_state(session)
        _reap_if_stale(session, existing_state)

        if session_has_attached_client(session):
            return

        existing_state = _read_state(session)
        if existing_state is not None and _pid_is_alive(existing_state.helper_pid):
            helper_pid = existing_state.helper_pid
            started_at = existing_state.started_at
        else:
            helper_pid = _spawn_daemon(session, ttl_seconds)
            started_at = time.time()
            _write_state(
                HelperState(
                    version=1,
                    session_name=session,
                    backend="python-pty",
                    state="starting",
                    helper_pid=helper_pid,
                    started_at=started_at,
                    last_used_at=started_at,
                    ttl_seconds=ttl_seconds,
                )
            )

        deadline = time.time() + start_timeout_seconds
        ready_settle_seconds = float(
            os.environ.get(
                "OPENCLAW_ZELLIJ_HELPER_READY_SETTLE_SECONDS",
                DEFAULT_READY_SETTLE_SECONDS,
            )
        )
        while time.time() < deadline:
            if (
                _pid_is_alive(helper_pid)
                and time.time() - started_at >= ready_settle_seconds
            ):
                now = time.time()
                _write_state(
                    HelperState(
                        version=1,
                        session_name=session,
                        backend="python-pty",
                        state="ready",
                        helper_pid=helper_pid,
                        started_at=started_at,
                        last_used_at=now,
                        ttl_seconds=ttl_seconds,
                    )
                )
                return
            if not _pid_is_alive(helper_pid):
                _clear_state(session)
                break
            time.sleep(0.1)

        _terminate_process(helper_pid)
        _clear_state(session)
        raise HiddenAttachError(
            f"Failed to establish a hidden attached client for session '{session}' within {start_timeout_seconds:.1f}s."
        )


def touch_hidden_attach(session: str) -> None:
    state = _read_state(session)
    if state is None or not _pid_is_alive(state.helper_pid):
        return
    _write_state(
        HelperState(
            version=state.version,
            session_name=state.session_name,
            backend=state.backend,
            state="ready",
            helper_pid=state.helper_pid,
            started_at=state.started_at,
            last_used_at=time.time(),
            ttl_seconds=state.ttl_seconds,
        )
    )


def cleanup_hidden_attach(session: str) -> None:
    with _session_lock(session):
        state = _read_state(session)
        if state is not None:
            _terminate_process(state.helper_pid)
        _clear_state(session)
