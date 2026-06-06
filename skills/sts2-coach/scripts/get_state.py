#!/usr/bin/env python3
"""
Fetch the current game state from the SLAI mod.

Equivalent to the old MCP tool `get_coaching_state` minus the coaching
overlay — use `analyze_deck.py` to add pillar scores on top.

Use --format json for combat (structured), --format markdown for map/event
overviews (human-readable).

--fields filters the JSON response to only the slices you ask for.
This is the right move for "did anything change?" polls between turns —
don't drag the whole master_deck back across the wire every time.

Examples:
    get_state.py --fields screen,hp,gold        # tiny "what's the situation" poll
    get_state.py --fields summary               # one-stop default snapshot
    get_state.py --fields card_reward,hp        # at a reward screen
    get_state.py --fields combat                # full combat picture (hand+piles+orbs+enemies)
    get_state.py                                # full state (back-compat default)

Run with --list-fields to see every shortcut.
"""

from __future__ import annotations

import argparse
import json
import sys

import _lib


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _lib.add_common_args(parser)
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="json for combat, markdown for map/event overview",
    )
    parser.add_argument(
        "--fields",
        default="all",
        help=(
            "Comma-separated field shortcuts to project the state to "
            "(e.g. 'screen,hp,gold'). Default 'all' returns the full state. "
            "Run --list-fields to see options. Ignored when --format=markdown."
        ),
    )
    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="Print available field shortcuts and exit.",
    )
    args = parser.parse_args()

    if args.list_fields:
        for name in _lib.available_fields():
            print(name)
        return 0

    if args.state_file:
        with open(args.state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = _lib.get_game_state(host=args.host, port=args.port, fmt=args.format)

    if args.format == "markdown" and "markdown" in state:
        sys.stdout.write(state["markdown"])
        if not state["markdown"].endswith("\n"):
            sys.stdout.write("\n")
        return 0

    # Filter to requested fields (preserves errors so the agent still sees them)
    if "error" in state or not args.fields or args.fields.lower() == "all":
        _lib.emit_json(state)
    else:
        _lib.emit_json(_lib.project_state(state, args.fields))
    return 1 if "error" in state else 0


if __name__ == "__main__":
    sys.exit(main())
