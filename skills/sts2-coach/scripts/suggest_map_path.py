#!/usr/bin/env python3
"""
Compute HP-aware pathing context from the current state.

Outputs JSON with act, floor, current_hp, max_hp, hp_pct, and hp_warning.
The Skill should combine this with the cached pathing knowledge in
knowledge.md (Look Ahead Method, elite risk, campfire prioritization)
to produce an actual pathing recommendation.

Equivalent to the HP-aware portion of the old MCP tool `suggest_map_path`.
The knowledge portion is no longer duplicated here — it lives in the
CAG-cached knowledge.md.
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

    # Real paths in SLAI mod state are state.run.act / state.run.floor.
    # Top-level act/floor are kept as fallbacks for older fixtures.
    run = state.get("run") if isinstance(state.get("run"), dict) else {}
    act_raw = run.get("act", state.get("act", 1))
    act = int(act_raw) if isinstance(act_raw, (int, float)) else 1
    floor_raw = run.get("floor", state.get("floor", state.get("current_floor", 1)))
    floor = int(floor_raw) if isinstance(floor_raw, (int, float)) else 1

    hp, max_hp = _lib.extract_hp(state)
    hp_pct = (hp / max_hp * 100) if max_hp > 0 else 100.0

    _lib.emit_json(
        {
            "situation": _lib.build_situation(state),
            "act": act,
            "floor": floor,
            "current_hp": hp,
            "max_hp": max_hp,
            "hp_pct": round(hp_pct, 1),
            "hp_warning": _lib.hp_warning(hp_pct),
            "character": _lib._extract_character(state),
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
