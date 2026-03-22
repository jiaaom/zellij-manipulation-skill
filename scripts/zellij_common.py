from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TabInfo:
    position: int
    name: str
    active: bool


@dataclass(frozen=True)
class PaneInfo:
    pane_id: int
    kind: str
    title: str
    focused: bool
    tab_position: int

    @property
    def normalized_id(self) -> str:
        return f"{self.kind}_{self.pane_id}"


@dataclass(frozen=True)
class SessionMetadata:
    tabs_by_position: dict[int, TabInfo]
    panes: list[PaneInfo]


def fail(message: str) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(1)


def run(args: list[str], *, capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def zellij_action_cmd(session: str | None, *action_args: str) -> list[str]:
    cmd = ["zellij"]
    if session:
        cmd.extend(["-s", session])
    cmd.append("action")
    cmd.extend(action_args)
    return cmd


def find_current_session() -> str:
    # Session resolution policy for all Python zellij helpers:
    # 1. if ZELLIJ_SESSION_NAME is present, use it
    # 2. otherwise, if zellij marks one session as "(current)", use it
    # 3. otherwise, if exactly one live non-exited session exists, use it
    # 4. otherwise, fail and require the caller to pass --session explicitly
    if os.environ.get("ZELLIJ_SESSION_NAME"):
        return os.environ["ZELLIJ_SESSION_NAME"]

    raw = run(["zellij", "list-sessions", "--no-formatting"]).stdout.splitlines()
    if not raw:
        fail("No zellij sessions found")

    parsed: list[tuple[str, str]] = []
    for line in raw:
        name = re.sub(r" \[Created.*", "", line).strip()
        if "(current)" in line:
            status = "current"
        elif "(EXITED" in line:
            status = "exited"
        else:
            status = "active"
        parsed.append((name, status))

    for name, status in parsed:
        if status == "current":
            return name

    live = [name for name, status in parsed if status == "active"]
    if len(live) == 1:
        return live[0]

    fail(
        "Could not determine a unique current zellij session.\n"
        + "\n".join(f"  - {name} ({status})" for name, status in parsed)
    )


def find_session_metadata_file(session: str) -> Path:
    version = run(["zellij", "--version"]).stdout.strip().split()[-1]
    # Match zellij's per-version cache layout on macOS and Linux.
    candidates = [
        os.environ.get("OPENCLAW_ZELLIJ_SESSION_INFO_DIR"),
        f"{Path.home()}/Library/Caches/org.Zellij-Contributors.zellij/{version}/session_info",
        f"{os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))}/zellij/{version}/session_info",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate) / session / "session-metadata.kdl"
        if path.is_file():
            return path
    fail(
        f"Could not find session-metadata.kdl for session '{session}' (zellij {version})."
    )


def parse_metadata(path: Path) -> SessionMetadata:
    tabs_by_position: dict[int, TabInfo] = {}
    panes: list[PaneInfo] = []

    section: str | None = None
    item: str | None = None
    current: dict[str, str] = {}

    # Parse the small subset of KDL fields we need instead of depending on a KDL parser.
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if line == "tabs {":
            section = "tabs"
            continue
        if line == "panes {":
            section = "panes"
            continue
        if section == "tabs" and line == "tab {":
            item = "tab"
            current = {}
            continue
        if section == "panes" and line == "pane {":
            item = "pane"
            current = {}
            continue
        if line == "}":
            if item == "tab":
                position = int(current["position"])
                tabs_by_position[position] = TabInfo(
                    position=position,
                    name=current.get("name", ""),
                    active=current.get("active", "false") == "true",
                )
                item = None
                current = {}
                continue
            if item == "pane":
                panes.append(
                    PaneInfo(
                        pane_id=int(current["id"]),
                        kind="plugin" if current.get("is_plugin") == "true" else "terminal",
                        title=current.get("title", ""),
                        focused=current.get("is_focused") == "true",
                        tab_position=int(current["tab_position"]),
                    )
                )
                item = None
                current = {}
                continue
            if section in {"tabs", "panes"}:
                section = None
                continue

        if item is None or not line:
            continue

        key, _, value = line.partition(" ")
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        current[key] = value

    return SessionMetadata(tabs_by_position=tabs_by_position, panes=panes)


def current_pane_id(session: str) -> str:
    result = run(zellij_action_cmd(session, "list-clients")).stdout.strip().splitlines()
    if not result:
        fail("zellij action list-clients returned no output")
    last = result[-1].split()
    if len(last) < 2:
        fail("Could not parse current pane from zellij action list-clients")
    return last[1]


def list_terminal_panes(metadata: SessionMetadata) -> list[PaneInfo]:
    return [pane for pane in metadata.panes if pane.kind == "terminal"]


def format_terminal_pane_summary(metadata: SessionMetadata) -> list[str]:
    lines: list[str] = []
    for pane in list_terminal_panes(metadata):
        tab = metadata.tabs_by_position.get(pane.tab_position)
        tab_name = tab.name if tab else str(pane.tab_position)
        lines.append(
            f"  - {pane.normalized_id} tab={tab_name} title={pane.title!r} focused={pane.focused}"
        )
    return lines


def list_tabs(metadata: SessionMetadata) -> list[TabInfo]:
    return [metadata.tabs_by_position[pos] for pos in sorted(metadata.tabs_by_position)]


def active_tab(metadata: SessionMetadata) -> TabInfo | None:
    for tab in metadata.tabs_by_position.values():
        if tab.active:
            return tab
    return None


def format_tab_summary(metadata: SessionMetadata) -> list[str]:
    lines: list[str] = []
    for tab in list_tabs(metadata):
        lines.append(f"  - pos={tab.position} name={tab.name!r} active={tab.active}")
    return lines


def unique_tab_position(metadata: SessionMetadata, query: str | None) -> int | None:
    if not query:
        return None
    lowered = query.lower()
    matches = [
        tab.position
        for tab in metadata.tabs_by_position.values()
        if lowered in tab.name.lower()
    ]
    if not matches:
        fail(f"No tab matched query '{query}'")
    unique = sorted(set(matches))
    if len(unique) != 1:
        names = [metadata.tabs_by_position[pos].name for pos in unique]
        fail(f"Tab query '{query}' matched multiple tabs: {', '.join(names)}")
    return unique[0]


def normalize_target_id(raw: str | None, kind: str) -> str | None:
    if raw is None:
        return None
    if raw.startswith("terminal_") or raw.startswith("plugin_"):
        return raw
    if raw.isdigit():
        return f"{kind}_{raw}"
    fail(f"Unsupported pane id '{raw}'. Use eg. 2 or terminal_2.")


def select_target_pane(
    metadata: SessionMetadata,
    *,
    kind: str = "terminal",
    tab_query: str | None = None,
    pane_id: str | None = None,
    title_query: str | None = None,
    require_pane_id_for_multi: bool = False,
) -> PaneInfo:
    tab_position = unique_tab_position(metadata, tab_query)
    target_id = normalize_target_id(pane_id, kind)
    lowered_title_query = title_query.lower() if title_query else None

    candidates = [pane for pane in metadata.panes if pane.kind == kind]

    if require_pane_id_for_multi and tab_position is not None and target_id is None:
        tab_candidates = [pane for pane in candidates if pane.tab_position == tab_position]
        if len(tab_candidates) > 1:
            tab = metadata.tabs_by_position.get(tab_position)
            tab_name = tab.name if tab else str(tab_position)
            lines = [
                f"Tab '{tab_name}' has multiple {kind} panes. Re-run with --pane-id.",
                "Available panes:",
            ]
            for pane in tab_candidates:
                lines.append(
                    f"  - {pane.normalized_id} title={pane.title!r} focused={pane.focused}"
                )
            fail("\n".join(lines))

    if tab_position is not None:
        candidates = [pane for pane in candidates if pane.tab_position == tab_position]
    if target_id is not None:
        candidates = [pane for pane in candidates if pane.normalized_id == target_id]
    if lowered_title_query:
        candidates = [pane for pane in candidates if lowered_title_query in pane.title.lower()]

    if not candidates and target_id is not None and tab_position is None:
        fail(f"No {kind} pane matched '{target_id}'")
    if not candidates:
        fail("No panes matched the requested filters")
    if len(candidates) == 1:
        return candidates[0]

    focused = [pane for pane in candidates if pane.focused]
    if len(focused) == 1:
        return focused[0]

    summary = []
    for pane in candidates:
        tab = metadata.tabs_by_position.get(pane.tab_position)
        summary.append(
            f"  - {pane.normalized_id} tab={tab.name if tab else pane.tab_position} title={pane.title!r} focused={pane.focused}"
        )
    fail("Multiple panes matched:\n" + "\n".join(summary))


def focus_pane(session: str, metadata: SessionMetadata, target: PaneInfo) -> None:
    target_tab = metadata.tabs_by_position.get(target.tab_position)
    if target_tab is None:
        fail(f"Could not resolve tab for target pane {target.normalized_id}")

    run(zellij_action_cmd(session, "go-to-tab-name", target_tab.name))

    tab_panes = [
        pane
        for pane in metadata.panes
        if pane.kind == "terminal" and pane.tab_position == target.tab_position
    ]
    max_steps = max(len(tab_panes) + 1, 2)
    first_seen: str | None = None

    # Walk panes until we either land on the target or wrap back to where we started.
    for _ in range(max_steps):
        current = current_pane_id(session)
        if current == target.normalized_id:
            return
        if first_seen is None:
            first_seen = current
        elif current == first_seen:
            break
        run(zellij_action_cmd(session, "focus-next-pane"))

    fail(f"Could not focus target pane {target.normalized_id} in tab '{target_tab.name}'")


def restore_origin(session: str, metadata: SessionMetadata, origin_id: str) -> None:
    pane_map = {pane.normalized_id: pane for pane in metadata.panes}
    origin = pane_map.get(origin_id)
    if origin is None:
        return
    try:
        focus_pane(session, metadata, origin)
    except SystemExit:
        print(f"Warning: failed to restore focus to {origin_id}", file=sys.stderr)
