#!/usr/bin/env python3
"""
Grade the current card-reward options against the deck's needs.

Outputs JSON with a list of evaluations (card_name, grade S/A/B/C/D/F,
reasons[], card_type). If no card reward is currently being offered,
outputs an explanatory message and exits non-zero.

Equivalent to the old MCP tool `evaluate_card_reward`.
"""

from __future__ import annotations

import argparse
import sys

import _lib


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _lib.add_common_args(parser)
    args = parser.parse_args()

    state = _lib.load_state(args)
    if "error" in state:
        _lib.emit_json(state)
        return 1

    card_options = _lib.extract_card_rewards(state)
    if not card_options:
        _lib.emit_json(
            {
                "error": "no_card_reward",
                "message": (
                    "No card reward currently available. "
                    "This script is meaningful only at a card reward screen."
                ),
            }
        )
        return 2

    deck = _lib._extract_deck(state)
    evaluations = _lib.evaluate_card_options(card_options, deck)
    _lib.emit_json(
        {
            "evaluations": evaluations,
            "deck_size": len(deck),
            "reminder": (
                "Baalorlord: it's always okay to SKIP. A smaller, focused deck "
                "(20-25 cards) is usually stronger."
            ),
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
