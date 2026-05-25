# sts2-coach Skill scripts

Stdlib-only Python that the `sts2-coach` Skill shells out to via Bash. These
scripts replace what used to be the SLAI MCP server's analyzer tools — the
analysis is identical, but installation is now just "drop the Skill folder in
place; no `pip install` needed".

## Requirements

- Python 3.10+ on `PATH`. The Skill invokes scripts with paths relative to its own folder, e.g. `python scripts/analyze_deck.py`.
- The SLAI mod running inside Slay the Spire 2 on `localhost:15526`.

No third-party packages. Everything uses `urllib`, `json`, and `argparse` from
the standard library.

## Scripts

| Script | What it prints to stdout |
|---|---|
| `check_connection.py` | `{connected, message, status}` — is the mod reachable? |
| `get_state.py` | The raw game state (`--format json` or `--format markdown`) |
| `analyze_deck.py` | `{pillar_scores, deck_stats, insights, warnings, character}` |
| `evaluate_card_reward.py` | `{evaluations[], deck_size, reminder}` — S/A/B/C/D/F per offered card |
| `check_mistakes.py` | `{warnings[], warning_count, common_mistakes_reference}` |
| `suggest_map_path.py` | `{act, floor, current_hp, max_hp, hp_pct, hp_warning, character}` |

All scripts:

- Accept `--host` (default `localhost`) and `--port` (default `15526`) to point
  at a different SLAI mod instance.
- Accept `--state-file path.json` to read state from a file instead of the live
  mod — useful for testing and for replaying captured states.
- Exit `0` on success, non-zero on connection failure or expected-missing data
  (e.g. `evaluate_card_reward.py` exits `2` when no card reward is being
  offered).
- Print errors as JSON to stderr where they originate, and as JSON to stdout
  for the caller to consume.

## Shared core

`_lib.py` holds the HTTP client, the deck analyzer, and the card-grading
logic. The math is a line-for-line port of what used to live in
`mcp-server/deck_analyzer.py`, so pillar scores computed by this Skill are
identical to scores computed by the old MCP server.

## Why not MCP?

The MCP server existed because, when SLAI was first built, Skills couldn't
run code. Skills can now run arbitrary scripts via Bash, which collapses the
three-layer architecture (Skill → MCP server → mod) down to two (Skill → mod)
with one fewer process to start, one fewer install step, and no MCP config
file to edit. See [`docs/architecture.md`](../../../docs/architecture.md).
