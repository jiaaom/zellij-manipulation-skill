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

Do not use `zellij attach`.

## Requirement

`dump-pane.py` must run in the real user context where `zellij action ...` works.

Inside the OpenClaw sandbox, the same commands can fail with:

```text
There is no active session!
```

So the script is intended for the approved, non-interactive execution path outside the sandbox.

## Usage

Basic:

```bash
python3 {baseDir}/scripts/dump-pane.py --session friendly-zebra --pane-id 2
```

Target a tab explicitly:

```bash
python3 {baseDir}/scripts/dump-pane.py --session friendly-zebra --tab test
```

Target a specific pane inside a tab:

```bash
python3 {baseDir}/scripts/dump-pane.py --session friendly-zebra --tab test --pane-id 2
```

Limit output:

```bash
python3 {baseDir}/scripts/dump-pane.py --session friendly-zebra --tab test --pane-id 2 --lines 80
```

Dump full scrollback:

```bash
python3 {baseDir}/scripts/dump-pane.py --session friendly-zebra --tab test --pane-id 2 --full
```

Resolve by title:

```bash
python3 {baseDir}/scripts/dump-pane.py --session friendly-zebra --tab test --title-query btop
```

## Arguments

- `--session`: optional target zellij session; when omitted the script uses the current session, or the only live non-exited session, and otherwise fails
- `--pane-id`: target pane id, eg. `2` or `terminal_2`
- `--kind`: `terminal` or `plugin`; default is `terminal`
- `--tab`: case-insensitive tab-name filter; preferred when tab names are stable
- `--title-query`: case-insensitive pane-title filter
- `--lines`: show the last N lines when `--full` is not set; default `100`
- `--full`: print the full dump instead of truncating to the last N lines

## Matching rules

- If `--pane-id 2` is used, the script interprets it as `terminal_2` unless `--kind plugin` is set.
- If `--tab test` matches a single terminal pane, the script can dump it without a pane title or pane id.
- If a tab contains multiple terminal panes, `--pane-id` is required. The script will refuse to guess.
- If `--tab` is provided, the script requires exactly one matching tab.
- If multiple panes match, the script prefers the focused one. Otherwise it fails rather than guessing.

## Interactive programs

For TUIs such as `btop`, `lazygit`, or editors:

- the dump is still useful
- the result is usually the current rendered screen
- it should be treated as a screen snapshot, not as structured program state

This was verified against `btop` in the `test` tab of session `friendly-zebra`.

## Focus restoration

The script records the origin pane before switching away and attempts to restore focus after dumping.

Observed behavior during validation:

- dumping `friendly-zebra / test / terminal_2` succeeded
- focus returned to `terminal_1` (`codex`) afterward

If restoration fails, the dump may still succeed, but the operator should assume focus may have moved.

## Known limits

- This approach is focus-moving, not pane-addressed RPC.
- It depends on `zellij action go-to-tab-name`, `focus-next-pane`, `list-clients`, and `dump-screen`.
- It reads what zellij can dump, which is ideal for visible screen state but not necessarily full semantic application state.
