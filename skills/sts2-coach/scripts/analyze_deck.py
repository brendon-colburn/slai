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

    _lib.emit_json(_lib.analyze(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
