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
