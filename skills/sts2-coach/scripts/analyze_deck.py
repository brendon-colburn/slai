#!/usr/bin/env python3
"""
Analyze the current deck against Baalorlord's 4 Pillars.

Outputs JSON with pillar_scores (0-100 per pillar), deck_stats, insights,
warnings, and character. Equivalent to the old MCP tool `analyze_deck`.
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

    out = _lib.analyze(state)
    # Embed the situational picture (screen/HP/boss + deck composition, relics,
    # potions, path ahead) as a delta vs the previous call, so repeated turns
    # don't pile up identical copies of unchanged state. --full-situation forces
    # the complete block (e.g. after a /clear).
    out["situation"] = _lib.build_situation_output(state, force_full=args.full_situation)
    _lib.emit_json(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
