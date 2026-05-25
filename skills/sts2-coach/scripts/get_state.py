#!/usr/bin/env python3
"""
Fetch the current game state from the SLAI mod.

Equivalent to the old MCP tool `get_coaching_state` minus the coaching
overlay — use `analyze_deck.py` to add pillar scores on top.

Use --format json for combat (structured), --format markdown for map/event
overviews (human-readable).
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
    args = parser.parse_args()

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

    _lib.emit_json(state)
    return 1 if "error" in state else 0


if __name__ == "__main__":
    sys.exit(main())
