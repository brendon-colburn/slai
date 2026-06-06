"""
Build the knowledge.md bundle for the sts2-coach Skill.

Reads every JSON file under knowledge/ and renders a single, LLM-friendly
markdown document at skills/sts2-coach/knowledge.md. Run this whenever you
edit a knowledge JSON file; the rendered bundle is what the Skill loads
into context at startup (CAG — see docs/architecture.md).

Usage (from repo root):
    python tools/build_knowledge.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
OUTPUT_PATH = REPO_ROOT / "skills" / "sts2-coach" / "knowledge.md"

# Keys that show up at the top of nearly every JSON file as metadata and
# shouldn't be rendered as content sections.
METADATA_KEYS = {"source", "version", "last_updated"}

# Ordering of top-level files in the bundle. Files not listed get appended
# alphabetically.
FILE_ORDER = [
    # Core framework — load this first so all later references make sense
    "general_strategy.json",
    "pathing_strategy.json",
    # Per-turn / per-fight micro-decisions
    "combat_micro.json",
    # Economy + meta layer
    "economy.json",
    # Reference material (cards/relics/mechanics that interact with everything else)
    "mechanics.json",
    "enchantments.json",
    "ancients.json",
    # Specific encounters — should reference everything above
    "elite_strategies.json",
    "boss_strategies.json",
    # Anti-patterns last so they reinforce what to NOT do after teaching what to do
    "common_mistakes.json",
]
CHARACTER_ORDER = [
    "ironclad.json",
    "silent.json",
    "defect.json",
    "necrobinder.json",
    "regent.json",
]

# Files that load into the always-resident core bundle (knowledge.md). Everything
# else is rendered to its own file under knowledge/ and read on demand, so the
# model isn't carrying ~55K tokens of character/boss/mechanics detail every turn.
# Core = the framework needed to reason about *any* situation.
CORE_FILES = {
    "general_strategy.json",
    "pathing_strategy.json",
    "combat_micro.json",
    "common_mistakes.json",
}

# Subdirectory (under the skill folder, beside knowledge.md) for on-demand sections.
ONDEMAND_DIRNAME = "knowledge"

# One-line "when to read this" hints for the index, keyed by display name.
# Files not listed get a generic hint derived from their title.
READ_HINTS: dict[str, str] = {
    "mechanics.json": "Keyword / status / mechanic definitions and exact numbers (Weak, Vulnerable, Poison, orbs, etc.) — read when you need precise mechanic behavior.",
    "economy.json": "Gold, shops, card-removal economy — read for shop and economy decisions.",
    "enchantments.json": "Enchantment effects — read when evaluating an enchantment.",
    "ancients.json": "Ancient mechanics — read when an Ancient is relevant.",
    "elite_strategies.json": "Per-elite tactics — read before or during a specific elite fight.",
    "boss_strategies.json": "Per-boss tactics — read when pathing toward or fighting an act boss.",
    "characters/ironclad.json": "Ironclad cards, archetypes, combos — read when coaching the Ironclad.",
    "characters/silent.json": "Silent cards, archetypes, combos — read when coaching the Silent.",
    "characters/defect.json": "Defect cards, orbs, archetypes — read when coaching the Defect.",
    "characters/necrobinder.json": "Necrobinder cards, archetypes — read when coaching the Necrobinder.",
    "characters/regent.json": "Regent cards, archetypes — read when coaching the Regent.",
}


def ondemand_filename(name: str) -> str:
    """Map a source JSON display name to its on-demand markdown filename."""
    return Path(name).stem + ".md"


def titleize(key: str) -> str:
    """Convert snake_case_key → 'Snake Case Key'."""
    return key.replace("_", " ").strip().title()


def render_value(value: Any, depth: int) -> list[str]:
    """Render a JSON value as markdown lines. depth = current heading level."""
    lines: list[str] = []

    if value is None:
        return []

    if isinstance(value, str):
        # Multi-line strings get rendered as paragraphs; short strings inline.
        text = value.strip()
        if text:
            lines.append(text)
            lines.append("")
        return lines

    if isinstance(value, (int, float, bool)):
        lines.append(str(value))
        lines.append("")
        return lines

    if isinstance(value, list):
        # If list of primitives → bullet list. If list of dicts → render each
        # as a sub-block separated by blank lines.
        if all(isinstance(item, (str, int, float, bool)) or item is None for item in value):
            for item in value:
                if item is None:
                    continue
                lines.append(f"- {item}")
            lines.append("")
            return lines
        for item in value:
            if isinstance(item, dict):
                # Use 'name' or 'title' as the sub-heading if present
                name = item.get("name") or item.get("title") or item.get("id")
                if name:
                    lines.append(f"{'#' * min(depth + 1, 6)} {name}")
                    lines.append("")
                    rest = {k: v for k, v in item.items() if k not in ("name", "title", "id")}
                    lines.extend(render_dict(rest, depth + 1))
                else:
                    lines.extend(render_dict(item, depth))
                lines.append("")
        return lines

    if isinstance(value, dict):
        return render_dict(value, depth)

    # Fallback
    lines.append(str(value))
    lines.append("")
    return lines


def render_dict(d: dict[str, Any], depth: int) -> list[str]:
    """Render a dict as markdown. Special-cases 'description', 'examples', etc."""
    lines: list[str] = []

    # Render 'description' first as a leading paragraph (no heading).
    if "description" in d and isinstance(d["description"], str):
        lines.append(d["description"].strip())
        lines.append("")

    for key, value in d.items():
        if key == "description":
            continue
        if key in METADATA_KEYS:
            continue
        if value is None:
            continue

        # Special inline keys — show as bold-tagged lines instead of subsections
        if isinstance(value, (str, int, float, bool)):
            lines.append(f"**{titleize(key)}:** {value}")
            lines.append("")
            continue

        # Lists or dicts → subsection
        heading_level = min(depth + 1, 6)
        lines.append(f"{'#' * heading_level} {titleize(key)}")
        lines.append("")
        lines.extend(render_value(value, heading_level))

    return lines


def render_file(name: str, data: Any) -> list[str]:
    """Render a single knowledge JSON file as a top-level section."""
    lines: list[str] = []
    title = titleize(Path(name).stem)
    # Character files start with "characters/" — keep just the character name
    if name.startswith("characters/"):
        title = "Character — " + titleize(Path(name).stem)
    lines.append(f"# {title}")
    lines.append("")
    if isinstance(data, dict):
        # Render any free-floating 'description' first
        if "description" in data and isinstance(data["description"], str):
            lines.append(data["description"].strip())
            lines.append("")
            data = {k: v for k, v in data.items() if k != "description"}
        lines.extend(render_dict(data, depth=1))
    else:
        lines.extend(render_value(data, depth=1))
    return lines


def collect_files() -> list[tuple[str, Path]]:
    """Return [(display_name, full_path), ...] in the desired bundle order."""
    files: list[tuple[str, Path]] = []
    for name in FILE_ORDER:
        path = KNOWLEDGE_DIR / name
        if path.exists():
            files.append((name, path))

    char_dir = KNOWLEDGE_DIR / "characters"
    if char_dir.exists():
        for name in CHARACTER_ORDER:
            path = char_dir / name
            if path.exists():
                files.append((f"characters/{name}", path))
        # Any character files we didn't explicitly order
        for path in sorted(char_dir.glob("*.json")):
            label = f"characters/{path.name}"
            if not any(f[0] == label for f in files):
                files.append((label, path))

    # Any other top-level files we missed
    for path in sorted(KNOWLEDGE_DIR.glob("*.json")):
        if not any(f[0] == path.name for f in files):
            files.append((path.name, path))

    return files


def _render_section(name: str, path: Path) -> str:
    """Render one source JSON to a standalone markdown string."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"FAIL parsing {path}: {e}")
    return "\n".join(render_file(name, data)).rstrip() + "\n"


def _read_hint(name: str) -> str:
    if name in READ_HINTS:
        return READ_HINTS[name]
    title = titleize(Path(name).stem)
    return f"{title} — read when relevant to the question."


def build_index(ondemand: list[tuple[str, Path]]) -> str:
    """Render the on-demand index that goes at the top of the core bundle."""
    lines = [
        "## On-demand knowledge sections",
        "",
        "The sections below are **not** in this bundle — Read them from "
        f"`{ONDEMAND_DIRNAME}/<file>` (beside this file) only when a question needs them, "
        "then rely on the prompt cache. Don't load them preemptively.",
        "",
    ]
    for name, _ in ondemand:
        title = titleize(Path(name).stem)
        if name.startswith("characters/"):
            title = "Character — " + titleize(Path(name).stem)
        lines.append(f"- **{title}** → `{ONDEMAND_DIRNAME}/{ondemand_filename(name)}` — {_read_hint(name)}")
    lines.append("")
    return "\n".join(lines)


def build_core_bundle(core: list[tuple[str, Path]], ondemand: list[tuple[str, Path]]) -> str:
    parts: list[str] = []
    parts.append(
        "<!-- Auto-generated by tools/build_knowledge.py — do not edit by hand. -->\n"
        "<!-- Source files live under knowledge/. To update, edit the JSON and re-run -->\n"
        "<!-- the build script, then commit the regenerated knowledge.md + knowledge/. -->\n"
    )
    parts.append("# SLAI Knowledge Bundle (core)\n")
    parts.append(
        "Always-resident strategic core for the `sts2-coach` Skill. Character guides, "
        "boss/elite tactics, mechanic definitions, and economy detail live in on-demand "
        "sections (see the index below) to keep this bundle small. Paraphrases publicly "
        "available content from **Baalorlord** "
        "([Twitch](https://www.twitch.tv/baalorlord), "
        "[YouTube](https://www.youtube.com/@baalorlord)). Any misrepresentation is "
        "ours, not his — see ATTRIBUTION.md.\n"
    )
    parts.append(build_index(ondemand))

    for name, path in core:
        parts.append("\n---\n")
        parts.append(_render_section(name, path))

    return "\n".join(parts) + "\n"


def _stats(text: str) -> str:
    chars = len(text)
    lines = text.count("\n")
    words = len(re.findall(r"\w+", text))
    return f"{lines} lines · {words} words · {chars} chars · ~{chars // 4} tokens (rough)"


def main() -> None:
    files = collect_files()
    core = [(n, p) for n, p in files if n in CORE_FILES]
    ondemand = [(n, p) for n, p in files if n not in CORE_FILES]

    # Core bundle → knowledge.md
    bundle = build_core_bundle(core, ondemand)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(bundle, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} (core, {len(core)} sections)")
    print(f"  {_stats(bundle)}")

    # On-demand sections → knowledge/<file>.md
    ondemand_dir = OUTPUT_PATH.parent / ONDEMAND_DIRNAME
    ondemand_dir.mkdir(parents=True, exist_ok=True)
    for name, path in ondemand:
        section = (
            "<!-- Auto-generated by tools/build_knowledge.py — do not edit by hand. -->\n"
            "<!-- On-demand knowledge section. Edit the source JSON and re-run the build. -->\n\n"
            + _render_section(name, path)
        )
        out = ondemand_dir / ondemand_filename(name)
        out.write_text(section, encoding="utf-8", newline="\n")
    print(f"Wrote {len(ondemand)} on-demand sections under "
          f"{ondemand_dir.relative_to(REPO_ROOT)}/")
    print(f"  Source: {len(files)} JSON files under {KNOWLEDGE_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
