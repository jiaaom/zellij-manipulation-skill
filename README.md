# Zellij Manipulation Skill

Minimal OpenClaw/Codex skill for working with an existing local Zellij session.

It includes helpers to:

- inspect tabs and panes
- dump pane output
- send keys and control input
- run commands in a pane
- create, rename, and focus tabs

Core entrypoints:

- `SKILL.md`
- `scripts/dump-pane.py`
- `scripts/send-keys.py`
- `scripts/run-in-pane.py`
- `scripts/new-tab.py`
- `scripts/rename-tab.py`
- `scripts/change-focus.py`

The scripts are designed for a real user context where `zellij action ...` works.

Install:

```bash
./install.sh
```
