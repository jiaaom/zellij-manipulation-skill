---
name: Zellij-Manipulation
description: Inspect and control an existing local zellij session from OpenClaw. Use for reading panes, sending keys, running commands in panes, and managing tabs without using attach.
homepage: https://zellij.dev
metadata: {"moltbot":{"emoji":"🪟","os":["darwin","linux"],"requires":{"bins":["zellij","python3"]},"install":[{"id":"brew","kind":"brew","formula":"zellij","bins":["zellij"],"label":"Install Zellij (brew)"},{"id":"cargo","kind":"cargo","crate":"zellij","bins":["zellij"],"label":"Install Zellij (Cargo)"}]}}
---

# Zellij Skill

Use this skill to work with an already-running zellij session.

Do not use `zellij attach` from an agent.

## Session resolution

For the Python helpers, `--session` is optional:

- use `--session` if you know the target
- otherwise use the current session
- otherwise use the only live non-exited session
- otherwise fail and require `--session`

## Discover

Find the session:

```bash
{baseDir}/scripts/find-current-session.sh
```

List tabs and panes:

```bash
python3 {baseDir}/scripts/find-panes.py [--session session]
```

## Targeting

Prefer `--tab` because tab names are more stable than pane titles.

Rules:

- if a tab has one terminal pane, `--tab` is enough
- if a tab has multiple terminal panes, `--pane-id` is required
- use `--title-query` only as a fallback

## Read

Dump a pane:

```bash
python3 {baseDir}/scripts/dump-pane.py --tab work --pane-id 2 --lines 80
python3 {baseDir}/scripts/dump-pane.py --tab work --pane-id 2 --full
```

Detailed notes:

- See `{baseDir}/references/dump-pane.md`

## Write

Run a shell command in a pane:

```bash
python3 {baseDir}/scripts/run-in-pane.py --tab work --pane-id 5 -- pwd
python3 {baseDir}/scripts/run-in-pane.py --tab work --pane-id 2 -- btop
python3 {baseDir}/scripts/run-in-pane.py --tab scratch -- pwd
```

Send keys or control input:

```bash
python3 {baseDir}/scripts/send-keys.py --tab work --pane-id 2 --text "hello"
python3 {baseDir}/scripts/send-keys.py --tab work --pane-id 2 --control enter
python3 {baseDir}/scripts/send-keys.py --tab work --pane-id 2 --control ctrl-c
python3 {baseDir}/scripts/send-keys.py --tab work --pane-id 2 --control up
python3 {baseDir}/scripts/send-keys.py --tab scratch --text "echo hello"
```

Supported named control keys:

- `ctrl-c`
- `enter`
- `esc`
- `tab`
- `up`
- `down`
- `left`
- `right`

## Tabs

Create a tab:

```bash
python3 {baseDir}/scripts/new-tab.py --name scratch
```

Rename a tab:

```bash
python3 {baseDir}/scripts/rename-tab.py --tab old-name --name new-name
```

Change focus:

```bash
python3 {baseDir}/scripts/change-focus.py --tab work
python3 {baseDir}/scripts/change-focus.py --tab work --pane-id 2
```

## Caveats

- These helpers work by focusing the target pane, acting, then restoring focus.
- They read screen/scrollback, not structured application state.
- `dump-pane.py` is useful for TUIs like `btop`, but treat the result as a screen snapshot.
- In the sandboxed exec context, raw `zellij action ...` can fail with `There is no active session!`.
- The Python helpers are intended for the approved real-user execution path outside the sandbox.
