# dump-pane.py

`dump-pane.py` dumps scrollback or the current visible screen from a target zellij pane by:

1. locating the target pane from `session-metadata.kdl`
2. switching focus to that pane
3. running `zellij action dump-screen`
4. restoring focus to the original pane

This is the current OpenClaw-compatible way to read pane contents.

## When to use it

Use `dump-pane.py` when an agent needs to inspect:

- another shell pane
- build/test output in another tab
- a full-screen TUI such as `btop`
- the current visible state of an interactive program

Do not call `zellij attach` directly. `dump-pane.py` automatically starts a hidden PTY-backed attach helper when a live session is detached.

## Requirement

`dump-pane.py` must run in the real user context where `zellij action ...` works.

Inside the OpenClaw sandbox, the same commands can fail with:

```text
There is no active session!
```

So the script is intended for the approved, non-interactive execution path outside the sandbox.

## Usage

Recommended workflow:

1. run `find-panes.py` first to discover the current tabs and pane ids
2. use `--tab` by itself when the target tab has one terminal pane
3. only use `--pane-id` when `find-panes.py` shows multiple terminal panes in the same tab
4. never guess pane ids; reuse the returned `terminal_*` id literally

Basic:

```bash
python3 {baseDir}/scripts/find-panes.py --session my-session
python3 {baseDir}/scripts/dump-pane.py --session my-session --tab work
```

Target a tab explicitly:

```bash
python3 {baseDir}/scripts/dump-pane.py --session my-session --tab work
```

Target a specific pane inside a tab:

```bash
python3 {baseDir}/scripts/dump-pane.py --session my-session --tab work --pane-id terminal_20
```

Limit output:

```bash
python3 {baseDir}/scripts/dump-pane.py --session my-session --tab work --pane-id terminal_20 --lines 80
```

Dump full scrollback:

```bash
python3 {baseDir}/scripts/dump-pane.py --session my-session --tab work --pane-id terminal_20 --full
```

Resolve by title:

```bash
python3 {baseDir}/scripts/dump-pane.py --session my-session --tab work --title-query htop
```

## Arguments

- `--session`: optional target zellij session; when omitted the script uses the current session, or the only live session, and otherwise fails. Detached live sessions are handled automatically; `EXITED - attach to resurrect` sessions are still unsupported.
- `--pane-id`: target pane id, eg. `2` or `terminal_2`
- `--kind`: `terminal` or `plugin`; default is `terminal`
- `--tab`: case-insensitive tab-name filter; preferred when tab names are stable
- `--title-query`: case-insensitive pane-title filter
- `--lines`: show the last N lines when `--full` is not set; default `100`
- `--full`: print the full dump instead of truncating to the last N lines

## Matching rules

- If `--pane-id 2` is used, the script interprets it as `terminal_2` unless `--kind plugin` is set.
- If `--tab work` matches a single terminal pane, the script can dump it without a pane title or pane id.
- If a tab contains multiple terminal panes, `--pane-id` is required. The script will refuse to guess.
- If `--tab` is provided, the script requires exactly one matching tab.
- If multiple panes match, the script prefers the focused one. Otherwise it fails rather than guessing.
- If a tab or pane id does not match, the script prints the available tabs or pane ids so the caller can retry with a real target.

## Interactive programs

For TUIs such as `btop`, `lazygit`, or editors:

- the dump is still useful
- the result is usually the current rendered screen
- it should be treated as a screen snapshot, not as structured program state

This was verified against a full-screen TUI in a dedicated work tab.

## Focus restoration

The script records the origin pane before switching away and attempts to restore focus after dumping.

Observed behavior during validation:

- dumping a target terminal pane succeeded
- focus returned to the origin pane afterward

If restoration fails, the dump may still succeed, but the operator should assume focus may have moved.

## Known limits

- This approach is focus-moving, not pane-addressed RPC.
- It depends on `zellij action go-to-tab-name`, `focus-next-pane`, `list-clients`, and `dump-screen`.
- Detached live sessions are handled through an automatic hidden PTY attach fallback.
- `EXITED - attach to resurrect` sessions are not supported.
- It reads what zellij can dump, which is ideal for visible screen state but not necessarily full semantic application state.
