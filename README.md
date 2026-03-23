# Zellij Manipulation Skill

> Work together with an agent in Zellij!

Minimal OpenClaw/Codex skill for working with an existing local Zellij session.

Tested with:

- OpenClaw `2026.3.13` (`61d171a`)
- Zellij `0.43.1`

It includes helpers to:

- inspect tabs and panes
- dump pane output
- send keys and control input
- run commands in a pane
- create, rename, and focus tabs

The Python helpers automatically handle live detached sessions by starting a hidden PTY-backed attach helper when an attached client is needed. Callers do not need separate attached vs detached code paths.


## Install:


```bash
git clone git@github.com:jiaaom/zellij-manipulation-skill.git && cd zellij-manipulation-skill
./install.sh
```

## Core entrypoints:

- `SKILL.md`
- `scripts/dump-pane.py`
- `scripts/send-keys.py`
- `scripts/run-in-pane.py`
- `scripts/new-tab.py`
- `scripts/rename-tab.py`
- `scripts/change-focus.py`

The scripts are designed for a real user context where `zellij action ...` works.

## Detached live sessions

- live detached sessions are supported automatically through the Python helpers
- callers should keep using the normal script entrypoints; there is no separate `--detached` mode
- the hidden helper uses a default PTY size of `120x40`, which is large enough for common TUIs like `btop`
- the helper can be tuned with environment variables:
  - `OPENCLAW_ZELLIJ_HELPER_COLS`
  - `OPENCLAW_ZELLIJ_HELPER_ROWS`
  - `OPENCLAW_ZELLIJ_HELPER_TTL_SECONDS`
  - `OPENCLAW_ZELLIJ_HELPER_READY_SETTLE_SECONDS`
  - `OPENCLAW_ZELLIJ_LIST_CLIENTS_RETRY_SECONDS`
  - `OPENCLAW_ZELLIJ_LIST_CLIENTS_POLL_SECONDS`

Current limitation:

- the target zellij session must still be live; sessions in `EXITED - attach to resurrect` state are not supported
- the helpers still work by focusing the target pane, acting, then restoring focus
- `dump-pane.py` reads the rendered screen/scrollback snapshot, not structured application state
