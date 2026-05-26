#!/usr/bin/env python3
"""
Archive the current run journal at end of run.

Moves .run-state/current-run.md to .run-state/runs/{stamp}-{character}-{outcome}.md
and clears the slate so the next run starts fresh.

Outcome is inferred:
    - If --outcome is passed, use that.
    - Otherwise infer from state: state_type 'game_over' → 'loss', else 'unknown'.
    - Acceptable outcomes: victory, loss, abandon, unknown.

Usage:
    journal_archive.py                       # auto-infer outcome from state
    journal_archive.py --outcome victory     # explicit
    journal_archive.py --outcome abandon     # quit-the-run case
"""

from __future__ import annotations

import argparse
import datetime
import shutil
import sys
from pathlib import Path

import _lib


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
JOURNAL_DIR = REPO_ROOT / ".run-state"
JOURNAL_FILE = JOURNAL_DIR / "current-run.md"
RUNS_DIR = JOURNAL_DIR / "runs"

VALID_OUTCOMES = {"victory", "loss", "abandon", "unknown"}


def _safe_slug(s: str) -> str:
    """Lowercase, strip 'The ', replace non-alnum with hyphens."""
    s = (s or "unknown").strip().lower()
    if s.startswith("the "):
        s = s[4:]
    out: list[str] = []
    prev_hyphen = False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_hyphen = False
        elif not prev_hyphen:
            out.append("-")
            prev_hyphen = True
    return "".join(out).strip("-") or "unknown"


def infer_outcome(state: dict) -> str:
    """Best-effort outcome inference from live state."""
    screen = str(state.get("state_type", "")).lower()
    if "game_over" in screen or "death" in screen or "loss" in screen:
        return "loss"
    if "victory" in screen or "win" in screen:
        return "victory"
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _lib.add_common_args(parser)
    parser.add_argument(
        "--outcome",
        choices=sorted(VALID_OUTCOMES),
        default=None,
        help="Override outcome detection. Default: infer from live state.",
    )
    parser.add_argument(
        "--character",
        default=None,
        help="Override character (default: read from live state).",
    )
    args = parser.parse_args()

    if not JOURNAL_FILE.exists():
        print("No active journal to archive (.run-state/current-run.md does not exist).")
        return 0

    state = _lib.load_state(args) if not args.outcome or not args.character else {}
    if "error" in state:
        state = {}

    outcome = args.outcome or infer_outcome(state)
    player = state.get("player") if isinstance(state.get("player"), dict) else {}
    character = args.character or player.get("character") or "unknown"

    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    char_slug = _safe_slug(character)
    archive_name = f"{stamp}-{char_slug}-{outcome}.md"

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = RUNS_DIR / archive_name

    # Avoid overwriting any existing archive (unlikely with HHMM stamp)
    counter = 1
    while archive_path.exists():
        archive_path = RUNS_DIR / f"{stamp}-{char_slug}-{outcome}-{counter}.md"
        counter += 1

    shutil.move(str(JOURNAL_FILE), str(archive_path))
    print(f"Archived journal to: {archive_path}")
    print("Next session starts with a clean slate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
