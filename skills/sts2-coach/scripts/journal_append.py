#!/usr/bin/env python3
"""
Append a line to the current run's journal at .run-state/current-run.md.

The journal is the persistent context that survives /clear and new
sessions. The agent reads it at session start (alongside knowledge.md)
to know what's been happening in this run.

Per-line format: `- F{floor} ({screen}): {message}`
The floor/screen are auto-fetched from the live mod (or --state-file).

If the journal doesn't exist yet, this creates it with a header
(character + start time). End-of-run handoff lives in journal_archive.py.

Usage:
    journal_append.py "TOOK Setup Strike (Strength scaling start)"
    journal_append.py --tag pick "TOOK Bash+ at floor 4 reward"
    journal_append.py --tag lesson "Enemy intent damage is post-multiplier — don't re-apply Vuln"
    journal_append.py --state-file fixture.json "TOOK Bouncing Flask"
    journal_append.py --show       # Print the current journal and exit
    journal_append.py --path       # Print the journal's filesystem path and exit
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

import _lib


# Project root = repo containing .run-state/
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
JOURNAL_DIR = REPO_ROOT / ".run-state"
JOURNAL_FILE = JOURNAL_DIR / "current-run.md"


def _now_iso() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _ensure_header(state: dict) -> None:
    """Create the journal file with a header if it doesn't exist."""
    if JOURNAL_FILE.exists():
        return
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    player = state.get("player") if isinstance(state.get("player"), dict) else {}
    run = state.get("run") if isinstance(state.get("run"), dict) else {}
    character = player.get("character") or "unknown"
    asc = run.get("ascension")
    asc_str = f" · A{asc}" if asc is not None else ""

    header = f"""# Run journal — {character}{asc_str} · started {_now_iso()}

Persistent narrative for this run. Survives `/clear` and new sessions.
Compact at act boundaries via `journal_compact` (or just edit this file).
Archive at end of run via `journal_archive.py`.

"""
    JOURNAL_FILE.write_text(header, encoding="utf-8")


def append_line(message: str, tag: str | None, state: dict) -> str:
    """Compose and append a single line. Returns the line written."""
    _ensure_header(state)

    run = state.get("run") if isinstance(state.get("run"), dict) else {}
    floor = run.get("floor")
    screen = state.get("state_type") or "unknown"
    floor_str = f"F{floor}" if floor is not None else "F?"
    tag_str = f"[{tag.upper()}] " if tag else ""

    line = f"- {floor_str} ({screen}): {tag_str}{message}\n"

    with JOURNAL_FILE.open("a", encoding="utf-8") as f:
        f.write(line)

    return line


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _lib.add_common_args(parser)
    parser.add_argument(
        "message",
        nargs="?",
        default=None,
        help="Journal line to append (omit to use --show or --path).",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help=(
            "Optional tag for the entry. Common: pick, skip, elite, boss, "
            "shop, event, rest, lesson, archetype, note. Helps later parsing."
        ),
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Print the current journal to stdout and exit.",
    )
    parser.add_argument(
        "--path",
        action="store_true",
        help="Print the journal's absolute path and exit.",
    )
    args = parser.parse_args()

    if args.path:
        print(JOURNAL_FILE)
        return 0

    if args.show:
        if not JOURNAL_FILE.exists():
            print("(no journal yet — call journal_append with a message first)")
            return 0
        sys.stdout.write(JOURNAL_FILE.read_text(encoding="utf-8"))
        return 0

    if not args.message:
        parser.error("message is required unless --show or --path is given")

    state = _lib.load_state(args)
    if "error" in state:
        # Still append, but flag the unknown context
        state = {"state_type": "offline", "run": {}, "player": {}}

    line = append_line(args.message, args.tag, state)
    sys.stdout.write(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
