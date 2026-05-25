#!/usr/bin/env python3
"""
Check the current state for common deck-building mistakes.

Outputs JSON with a list of warnings (each prefixed with a mistake code
like CARD_BLOAT, NO_BLOCK, etc.). Empty list means no mistakes detected.

Equivalent to the old MCP tool `check_mistakes`.
"""

from __future__ import annotations

import argparse
import sys

import _lib


COMMON_MISTAKES = [
    "Card Bloat (deck > 27 cards)",
    "Forcing Archetypes Early",
    "Ignoring Pathing Strategy",
    "Playing on Autopilot",
    "Hoarding Potions",
    "Misunderstanding Card Value",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _lib.add_common_args(parser)
    args = parser.parse_args()

    state = _lib.load_state(args)
    if "error" in state:
        _lib.emit_json(state)
        return 1

    analysis = _lib.analyze(state)
    warnings = analysis.get("warnings", [])

    _lib.emit_json(
        {
            "warnings": warnings,
            "warning_count": len(warnings),
            "common_mistakes_reference": COMMON_MISTAKES,
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
