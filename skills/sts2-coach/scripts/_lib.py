"""
Shared utilities for the sts2-coach Skill scripts.

This module is a stdlib-only port of what used to live in the
SLAI MCP server (game_client.py + deck_analyzer.py). The Skill
shells out to the scripts in this folder via Bash; this module
is the shared core they import.

No third-party dependencies on purpose: drop the folder into
.claude/skills/ and it works. Python 3.10+.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# ─── Defaults ────────────────────────────────────────────────────────────────

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 15526
DEFAULT_TIMEOUT_SEC = 10.0

# Card-text heuristics (kept identical to the old deck_analyzer.py so
# pillar scores don't drift between MCP and Skill-only deployments).
UNIVERSAL_BLOCK_KEYWORDS = ["block", "defend", "shield", "armor", "barrier"]
UNIVERSAL_ATTACK_KEYWORDS = ["damage", "attack", "strike", "hit"]
UNIVERSAL_DRAW_KEYWORDS = ["draw", "cycle", "scry"]

STARTING_DECK_SIZES = {
    "ironclad": 10,
    "silent": 12,
    "defect": 10,
    "necrobinder": 10,
    "regent": 10,
}

BASE_DRAW_PER_TURN = 5


# ─── HTTP client (stdlib) ────────────────────────────────────────────────────


def _base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _http_get(url: str, timeout: float = DEFAULT_TIMEOUT_SEC) -> tuple[int, bytes]:
    """GET a URL with stdlib urllib. Returns (status, body)."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read()
    except urllib.error.HTTPError as e:
        # Read the body so callers can inspect non-2xx (e.g. 404 fallback).
        body = e.read() if hasattr(e, "read") else b""
        return e.code, body


def check_connection(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> dict[str, Any]:
    """Check whether the SLAI mod's HTTP server is reachable."""
    url = _base_url(host, port) + "/"
    try:
        status, body = _http_get(url)
        if status != 200:
            return {
                "connected": False,
                "error": f"SLAI mod responded with HTTP {status}",
            }
        data = json.loads(body.decode("utf-8"))
        return {
            "connected": data.get("status") == "ok",
            "message": data.get("message", "Unknown"),
            "status": data.get("status", "unknown"),
        }
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        return {
            "connected": False,
            "error": f"Cannot connect to the SLAI mod at {_base_url(host, port)}: {e}",
            "hint": (
                "Make sure Slay the Spire 2 is running with the SLAI mod "
                "enabled (Settings -> Mods)."
            ),
        }
    except Exception as e:  # noqa: BLE001 — surface everything to the caller
        return {"connected": False, "error": str(e)}


def get_game_state(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    fmt: str = "json",
) -> dict[str, Any]:
    """
    Fetch the current game state from the SLAI mod.

    Tries /api/v1/singleplayer first, falls back to /api/v1/multiplayer on 404
    (matches STS2MCP v0.4.0+ behavior).
    """
    qs = urllib.parse.urlencode({"format": fmt})
    base = _base_url(host, port)
    try:
        status, body = _http_get(f"{base}/api/v1/singleplayer?{qs}")
        if status == 404:
            status, body = _http_get(f"{base}/api/v1/multiplayer?{qs}")
        if status != 200:
            return {"error": f"HTTP {status} from SLAI mod", "connected": False}

        if fmt == "json":
            return json.loads(body.decode("utf-8"))
        return {"markdown": body.decode("utf-8"), "format": "markdown"}

    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        return {"error": f"Not connected to the SLAI mod: {e}", "connected": False}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


# ─── Deck analyzer (port of mcp-server/deck_analyzer.py) ─────────────────────


def _extract_deck(game_state: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the master deck from a game state object.

    SLAI mod's canonical path is `player.master_deck` (exposed on every screen
    via our master_deck patch). Older STS2MCP responses use top-level keys
    instead; we check those as fallbacks for compatibility.
    """
    player = game_state.get("player") if isinstance(game_state.get("player"), dict) else {}

    # SLAI mod canonical path
    if isinstance(player.get("master_deck"), list):
        return player["master_deck"]

    # Compatibility fallbacks (older STS2MCP shapes / test fixtures)
    if isinstance(game_state.get("deck"), list):
        return game_state["deck"]
    if isinstance(game_state.get("master_deck"), list):
        return game_state["master_deck"]
    if isinstance(player.get("deck"), list):
        return player["deck"]
    run = game_state.get("run") if isinstance(game_state.get("run"), dict) else {}
    if isinstance(run.get("deck"), list):
        return run["deck"]
    return []


def _extract_character(game_state: dict[str, Any]) -> str:
    """Extract the character name as a normalized lowercase string."""
    char = game_state.get("character", "")
    if not char and "player" in game_state:
        char = game_state["player"].get("character", "")
    if not char and "run" in game_state:
        char = game_state["run"].get("character", "")
    return str(char).lower().strip()


def _extract_relics(game_state: dict[str, Any]) -> list[dict[str, Any]]:
    relics = game_state.get("relics", [])
    if not relics and "player" in game_state:
        relics = game_state["player"].get("relics", [])
    return relics if isinstance(relics, list) else []


def calculate_deck_stats(deck: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute raw deck stats. Pure function — no I/O."""
    total_cards = len(deck)
    attacks = skills = powers = curses = statuses = 0
    upgraded = block_cards = draw_cards = 0
    cost_distribution: dict[str, int] = {"0": 0, "1": 0, "2": 0, "3": 0, "X": 0}

    for card in deck:
        card_type = str(card.get("type", "")).lower()
        card_name = str(card.get("name", "")).lower()
        card_desc = str(card.get("description", "")).lower()
        is_upgraded = card.get("upgraded", False) or card.get("upgrade_count", 0) > 0

        if card_type == "attack":
            attacks += 1
        elif card_type == "skill":
            skills += 1
        elif card_type == "power":
            powers += 1
        elif card_type == "curse":
            curses += 1
        elif card_type == "status":
            statuses += 1

        if any(kw in card_name or kw in card_desc for kw in UNIVERSAL_BLOCK_KEYWORDS):
            block_cards += 1
        if any(kw in card_name or kw in card_desc for kw in UNIVERSAL_DRAW_KEYWORDS):
            draw_cards += 1
        if is_upgraded:
            upgraded += 1

        cost = str(card.get("cost", card.get("energy_cost", "1")))
        if cost in cost_distribution:
            cost_distribution[cost] += 1
        elif cost.upper() == "X":
            cost_distribution["X"] += 1

    playable_cards = total_cards - curses - statuses
    block_density = (block_cards / playable_cards * 100) if playable_cards > 0 else 0
    upgrade_density = (upgraded / playable_cards * 100) if playable_cards > 0 else 0
    attack_density = (attacks / playable_cards * 100) if playable_cards > 0 else 0

    effective_draw = BASE_DRAW_PER_TURN + (draw_cards * 0.5)
    cycle_time = total_cards / effective_draw if effective_draw > 0 else total_cards

    return {
        "total_cards": total_cards,
        "attacks": attacks,
        "skills": skills,
        "powers": powers,
        "curses": curses,
        "statuses": statuses,
        "upgraded": upgraded,
        "block_cards": block_cards,
        "draw_cards": draw_cards,
        "block_density_pct": round(block_density, 1),
        "upgrade_density_pct": round(upgrade_density, 1),
        "attack_density_pct": round(attack_density, 1),
        "cycle_time_turns": round(cycle_time, 1),
        "cost_distribution": cost_distribution,
        "playable_cards": playable_cards,
    }


def calculate_pillar_scores(stats: dict[str, Any]) -> dict[str, int]:
    """
    Score the deck against the 4 Pillars on a 0-100 scale.

    Identical math to the old mcp-server/deck_analyzer.py so historical
    scores remain comparable.
    """
    # Damage Output
    attack_score = min(stats["attack_density_pct"] * 1.5, 60)
    power_score = min(stats["powers"] * 10, 30)
    damage_score = int(min(attack_score + power_score + 10, 100))

    # Cycle Time
    total = stats["total_cards"]
    if total <= 15:
        size_score = 70
    elif total <= 20:
        size_score = 90
    elif total <= 25:
        size_score = 85
    elif total <= 30:
        size_score = 60
    elif total <= 35:
        size_score = 40
    else:
        size_score = max(20, 100 - total * 2)
    draw_bonus = min(stats["draw_cards"] * 8, 30)
    cycle_score = int(min(size_score + draw_bonus, 100))

    # Block Density (target ~33%)
    block_pct = stats["block_density_pct"]
    if block_pct < 10:
        block_score = 20
    elif block_pct < 20:
        block_score = 50
    elif block_pct < 28:
        block_score = 75
    elif block_pct <= 38:
        block_score = 95
    elif block_pct <= 50:
        block_score = 70
    else:
        block_score = 40

    # Upgrade Density
    upgrade_score = int(min(stats["upgrade_density_pct"] * 1.8, 100))

    return {
        "damage_output": max(0, min(100, damage_score)),
        "cycle_time": max(0, min(100, cycle_score)),
        "block_density": max(0, min(100, block_score)),
        "upgrade_density": max(0, min(100, upgrade_score)),
    }


def generate_insights(stats: dict[str, Any]) -> list[str]:
    """Human-readable insights about the deck composition."""
    insights: list[str] = []

    total = stats["total_cards"]
    if total == 0:
        return ["No deck data available. Start a run to see analysis."]
    if total <= 20:
        insights.append(f"Lean deck ({total} cards) — great cycle time.")
    elif total <= 25:
        insights.append(f"Healthy deck size ({total} cards) — good balance.")
    elif total <= 30:
        insights.append(
            f"Deck getting large ({total} cards) — consider skipping future card rewards."
        )
    else:
        insights.append(
            f"Bloated deck ({total} cards) — Baalorlord recommends 20-25 cards. "
            "Skip cards and look for removal opportunities."
        )

    block_pct = stats["block_density_pct"]
    if block_pct < 20:
        insights.append(
            f"Low block density ({block_pct:.0f}%) — Baalorlord targets ~33%."
        )
    elif 28 <= block_pct <= 38:
        insights.append(
            f"Block density ({block_pct:.0f}%) is in the sweet spot (~33% target)."
        )
    elif block_pct > 50:
        insights.append(
            f"Very high block density ({block_pct:.0f}%) — "
            "you might struggle to kill enemies fast enough."
        )

    upgrade_pct = stats["upgrade_density_pct"]
    if upgrade_pct < 20:
        insights.append(
            f"Low upgrade density ({upgrade_pct:.0f}%) — "
            "prioritize upgrading at campfires when above 50% HP."
        )
    elif upgrade_pct > 50:
        insights.append(
            f"Excellent upgrade density ({upgrade_pct:.0f}%) — well invested."
        )

    if stats["powers"] == 0:
        insights.append(
            "No Power cards — your deck lacks scaling. "
            "Powers provide permanent effects that grow stronger over long fights."
        )
    elif stats["powers"] >= 4:
        insights.append(
            f"Strong power presence ({stats['powers']} powers) — good scaling for bosses."
        )

    if stats["curses"] > 0:
        insights.append(
            f"{stats['curses']} curse(s) in deck — look for removal at shops or events."
        )

    return insights


def detect_warnings(
    stats: dict[str, Any],
    scores: dict[str, int],
    game_state: dict[str, Any],
) -> list[str]:
    """Detect common mistakes from Baalorlord's playbook."""
    warnings: list[str] = []

    if stats["total_cards"] > 27:
        warnings.append(
            f"CARD_BLOAT: Deck has {stats['total_cards']} cards. "
            "Baalorlord recommends 20-25. Skip more card rewards!"
        )

    floor_num = game_state.get("floor", game_state.get("current_floor", 0))
    if isinstance(floor_num, (int, float)) and floor_num > 15:
        if scores["damage_output"] < 40:
            warnings.append(
                "LOW_DAMAGE: Damage output is low for this point in the run. "
                "You may struggle with Act 2+ bosses."
            )

    if stats["block_density_pct"] < 15:
        warnings.append(
            "NO_BLOCK: Block density is dangerously low. "
            "Prioritize picking up block cards."
        )

    if stats["curses"] >= 3:
        warnings.append(
            f"CURSE_HEAVY: {stats['curses']} curses are severely hampering your deck. "
            "Remove them ASAP at shops."
        )

    if isinstance(floor_num, (int, float)) and floor_num > 10:
        if stats["upgrade_density_pct"] < 10:
            warnings.append(
                "NO_UPGRADES: Very few upgraded cards. "
                "Baalorlord says upgrading is usually better than resting at campfires."
            )

    return warnings


def analyze(game_state: dict[str, Any]) -> dict[str, Any]:
    """Top-level deck analysis. Returns pillar scores + insights + warnings."""
    deck = _extract_deck(game_state)
    character = _extract_character(game_state)

    if not deck:
        return {
            "pillar_scores": {
                "damage_output": 50,
                "cycle_time": 50,
                "block_density": 50,
                "upgrade_density": 50,
            },
            "deck_stats": {},
            "insights": ["No deck data available. Start a run to see analysis."],
            "warnings": [],
            "character": character,
        }

    stats = calculate_deck_stats(deck)
    scores = calculate_pillar_scores(stats)
    insights = generate_insights(stats)
    warnings = detect_warnings(stats, scores, game_state)

    return {
        "pillar_scores": scores,
        "deck_stats": stats,
        "insights": insights,
        "warnings": warnings,
        "character": character,
    }


# ─── Card-reward grading ─────────────────────────────────────────────────────

_GRADES = ["F", "D", "C", "B", "A", "S"]


def _upgrade_grade(grade: str) -> str:
    idx = _GRADES.index(grade) if grade in _GRADES else 2
    return _GRADES[min(idx + 1, len(_GRADES) - 1)]


def _downgrade_grade(grade: str) -> str:
    idx = _GRADES.index(grade) if grade in _GRADES else 2
    return _GRADES[max(idx - 1, 0)]


def evaluate_card_options(
    card_options: list[dict[str, Any]],
    deck: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Grade each offered card S/A/B/C/D/F against the current deck's needs."""
    stats = calculate_deck_stats(deck)
    scores = calculate_pillar_scores(stats)
    evaluations: list[dict[str, Any]] = []

    for card in card_options:
        card_name = str(card.get("name", "Unknown"))
        card_type = str(card.get("type", "")).lower()
        card_desc = str(card.get("description", "")).lower()
        grade = "C"
        reasons: list[str] = []

        if card_type == "attack" and scores["damage_output"] < 50:
            grade = _upgrade_grade(grade)
            reasons.append("Your deck needs more damage output")
        elif card_type == "skill" and scores["block_density"] < 50:
            grade = _upgrade_grade(grade)
            reasons.append("Your deck needs more block")
        elif card_type == "power":
            grade = _upgrade_grade(grade)
            reasons.append("Powers provide valuable scaling")

        if stats["total_cards"] > 25:
            grade = _downgrade_grade(grade)
            reasons.append("Deck is getting large — consider skipping")

        if "draw" in card_desc:
            grade = _upgrade_grade(grade)
            reasons.append("Card draw improves cycle time")

        evaluations.append(
            {
                "card_name": card_name,
                "grade": grade,
                "reasons": reasons,
                "card_type": card_type,
            }
        )

    return evaluations


def extract_card_rewards(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull the offered card-reward options out of a game state.

    SLAI mod canonical path is `state.card_reward.cards` (singular). Older
    code/fixtures used plural `card_rewards` or `rewards.cards`; kept as
    fallbacks for compatibility.
    """
    card_reward = state.get("card_reward")
    if isinstance(card_reward, dict) and isinstance(card_reward.get("cards"), list):
        return card_reward["cards"]
    if isinstance(state.get("card_rewards"), list):
        return state["card_rewards"]
    rewards = state.get("rewards")
    if isinstance(rewards, dict) and isinstance(rewards.get("cards"), list):
        return rewards["cards"]
    return []


# ─── HP / pathing helpers ────────────────────────────────────────────────────


def extract_hp(state: dict[str, Any]) -> tuple[int, int]:
    """Return (current_hp, max_hp), defaulting safely if absent."""
    player = state.get("player", {}) if isinstance(state.get("player"), dict) else {}
    hp = state.get("current_hp", player.get("hp", 50))
    max_hp = state.get("max_hp", player.get("max_hp", 80))
    try:
        return int(hp), int(max_hp)
    except (TypeError, ValueError):
        return 50, 80


def hp_warning(hp_pct: float) -> str | None:
    """Standard HP-based pathing warning text, or None if HP is fine."""
    if hp_pct < 30:
        return (
            "CRITICAL: HP is very low. Prioritize campfires for healing "
            "and avoid elites. Consider safer paths with events."
        )
    if hp_pct < 50:
        return (
            "CAUTION: HP is below 50%. Be selective about elite fights. "
            "Baalorlord recommends elites only above 50-60% HP."
        )
    if hp_pct < 60:
        return (
            "NOTE: HP is moderate. One more elite is fine if you have "
            "a strong deck, but plan for healing afterward."
        )
    return None


# ─── CLI helpers ─────────────────────────────────────────────────────────────


def add_common_args(parser) -> None:
    """Attach --host/--port/--state-file to an argparse parser."""
    parser.add_argument("--host", default=DEFAULT_HOST, help="SLAI mod host")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="SLAI mod port"
    )
    parser.add_argument(
        "--state-file",
        default=None,
        help="Read state from a JSON file instead of the live mod (for testing).",
    )


def load_state(args) -> dict[str, Any]:
    """
    Load game state honoring --state-file if set, otherwise hitting the mod.
    Exits with an explanatory message if the mod isn't reachable.
    """
    if args.state_file:
        with open(args.state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    state = get_game_state(host=args.host, port=args.port, fmt="json")
    if "error" in state:
        print(json.dumps(state, indent=2), file=sys.stderr)
        # Still return the error dict so callers can decide; non-zero exit
        # is the caller's choice.
    return state


def emit_json(obj: Any) -> None:
    """Write a JSON object to stdout, defaults stringified for safety."""
    json.dump(obj, sys.stdout, indent=2, default=str)


# ─── State projection (token-economy helpers) ────────────────────────────────
#
# The mod returns a thick JSON blob that includes the whole master deck,
# all relics, all potions, plus screen-specific data. Most coaching
# questions only need a small slice. project_state() lets callers (and
# the agent, via --fields on get_state.py) ask for exactly what they
# need; build_context() embeds a tiny situational summary into analysis
# outputs so the agent doesn't need a separate get_state.py call just to
# learn what screen it's on.


def _player_field(state: dict[str, Any], *keys: str) -> dict[str, Any]:
    """Pluck a subset of player.* fields if present."""
    player = state.get("player") if isinstance(state.get("player"), dict) else {}
    return {k: player[k] for k in keys if k in player}


def _run_field(state: dict[str, Any], *keys: str) -> dict[str, Any]:
    run = state.get("run") if isinstance(state.get("run"), dict) else {}
    return {k: run[k] for k in keys if k in run}


# Map of field-shortcut → (player_keys, run_keys, top_level_keys)
# Each tuple says what part of the source state contributes to the projection.
_FIELD_MAP: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "screen":      ((),                                                       (),                                        ("state_type",)),
    "hp":          (("hp", "max_hp", "block"),                                (),                                        ()),
    "gold":        (("gold",),                                                (),                                        ()),
    "status":      (("status",),                                              (),                                        ()),
    "relics":      (("relics",),                                              (),                                        ()),
    "potions":     (("potions", "max_potion_slots"),                          (),                                        ()),
    "deck":        (("master_deck", "master_deck_count", "character"),        (),                                        ()),
    "character":   (("character",),                                           (),                                        ()),
    "energy":      (("energy", "max_energy"),                                 (),                                        ()),
    "hand":        (("hand",),                                                (),                                        ()),
    "piles":       (("draw_pile", "discard_pile", "exhaust_pile",
                     "draw_pile_count", "discard_pile_count",
                     "exhaust_pile_count"),                                   (),                                        ()),
    "orbs":        (("orbs", "orb_slots", "orb_empty_slots"),                 (),                                        ()),
    "pets":        (("pets",),                                                (),                                        ()),
    "combat":      (("energy", "max_energy", "hand",
                     "draw_pile", "discard_pile", "exhaust_pile",
                     "draw_pile_count", "discard_pile_count",
                     "exhaust_pile_count",
                     "orbs", "orb_slots", "orb_empty_slots", "pets"),         (),                                        ("battle",)),
    "floor":       ((),                                                       ("act", "floor", "ascension"),             ()),
    "boss":        ((),                                                       ("boss", "boss_2"),                        ()),
    "run":         ((),                                                       ("act", "floor", "ascension",
                                                                                "boss", "boss_2"),                       ()),
    "card_reward": ((),                                                       (),                                        ("card_reward",)),
    "shop":        ((),                                                       (),                                        ("shop",)),
    "event":       ((),                                                       (),                                        ("event",)),
    "map":         ((),                                                       (),                                        ("map",)),
    "rest":        ((),                                                       (),                                        ("rest_site",)),
    "rewards":     ((),                                                       (),                                        ("rewards",)),
    # "summary" is the default cheap snapshot for "did anything change?"
    "summary":     (("character", "hp", "max_hp", "gold"),                    ("act", "floor", "ascension", "boss"),     ("state_type",)),
}


def available_fields() -> list[str]:
    """List the field shortcuts supported by project_state / --fields."""
    return sorted(_FIELD_MAP.keys()) + ["all"]


def project_state(state: dict[str, Any], field_spec: str) -> dict[str, Any]:
    """
    Filter a game-state dict to just the requested fields.

    `field_spec` is a comma-separated list of shortcuts (see available_fields()).
    "all" returns the whole state unchanged. Unknown shortcuts are ignored
    silently so the agent can be slightly sloppy without crashing.
    """
    if not field_spec or field_spec.strip().lower() == "all":
        return state

    requested = [f.strip().lower() for f in field_spec.split(",") if f.strip()]
    if "all" in requested:
        return state

    out: dict[str, Any] = {}
    player_keys: set[str] = set()
    run_keys: set[str] = set()
    top_keys: set[str] = set()

    for f in requested:
        if f not in _FIELD_MAP:
            continue
        p, r, t = _FIELD_MAP[f]
        player_keys.update(p)
        run_keys.update(r)
        top_keys.update(t)

    # Top-level
    for k in top_keys:
        if k in state:
            out[k] = state[k]

    # Player subset
    if player_keys:
        player_subset = _player_field(state, *player_keys)
        if player_subset:
            out["player"] = player_subset

    # Run subset
    if run_keys:
        run_subset = _run_field(state, *run_keys)
        if run_subset:
            out["run"] = run_subset

    return out


def build_context(state: dict[str, Any]) -> dict[str, Any]:
    """
    Tiny situational summary for embedding inside analysis-script outputs.

    Gives the agent state_type, hp string, gold, floor/act, and boss name
    so it doesn't need a separate get_state.py call to learn the
    surrounding situation. ~150-250 bytes regardless of run state.
    """
    player = state.get("player") if isinstance(state.get("player"), dict) else {}
    run = state.get("run") if isinstance(state.get("run"), dict) else {}

    ctx: dict[str, Any] = {
        "state_type": state.get("state_type"),
        "character": player.get("character"),
    }

    hp, max_hp = extract_hp(state)
    if hp or max_hp:
        ctx["hp"] = f"{hp}/{max_hp}"

    if "gold" in player:
        ctx["gold"] = player["gold"]

    floor = run.get("floor")
    act = run.get("act")
    if floor is not None and act is not None:
        ctx["floor"] = f"{floor}/Act {act}"
    elif floor is not None:
        ctx["floor"] = floor

    boss = run.get("boss")
    if isinstance(boss, dict):
        ctx["boss"] = boss.get("name") or boss.get("id")
    boss_2 = run.get("boss_2")
    if isinstance(boss_2, dict):
        ctx["boss_2"] = boss_2.get("name") or boss_2.get("id")

    # Drop nulls so the agent doesn't see noise
    return {k: v for k, v in ctx.items() if v is not None}


def summarize_path(state: dict[str, Any]) -> dict[str, Any] | None:
    """Compact path-ahead summary from state['map'], when a map is exposed.

    Returns the rooms the player can travel to right now (each with a 1-step
    lookahead of what it leads to) plus a tally of room types still ahead, so
    the agent can apply the Look Ahead Method without a separate map fetch.
    Returns None on screens with no map (most combat/event/shop screens).
    """
    m = state.get("map")
    if not isinstance(m, dict):
        return None

    out: dict[str, Any] = {}

    cur = m.get("current_position")
    cur_row = cur.get("row") if isinstance(cur, dict) else None

    # Rooms the player chooses between right now (with 1-step lookahead).
    options: list[dict[str, Any]] = []
    for opt in m.get("next_options") or []:
        if not isinstance(opt, dict):
            continue
        entry: dict[str, Any] = {"type": opt.get("type")}
        leads = [c.get("type") for c in (opt.get("leads_to") or []) if isinstance(c, dict)]
        if leads:
            entry["leads_to"] = leads
        options.append(entry)
    if options:
        out["next_options"] = options

    # Tally of room types in the rows still ahead — fuel for look-ahead planning
    # (e.g. "two campfires and an elite between here and the boss").
    nodes = m.get("nodes")
    if isinstance(nodes, list) and isinstance(cur_row, (int, float)):
        ahead: dict[str, int] = {}
        for n in nodes:
            if not isinstance(n, dict):
                continue
            row = n.get("row")
            if isinstance(row, (int, float)) and row > cur_row:
                t = n.get("type")
                if t:
                    ahead[str(t)] = ahead.get(str(t), 0) + 1
        if ahead:
            out["rooms_ahead"] = ahead

    return out or None


def build_situation(state: dict[str, Any]) -> dict[str, Any]:
    """Richer situational summary embedded in analysis-script output.

    Builds on build_context() to give the agent the whole interconnected
    picture in one block — screen/HP/gold/floor, this act's boss and the next,
    deck size & composition, owned relics and potions, and (on map screens)
    the path ahead. The point is holistic reasoning from a single call:
    synergies, deck needs, and pathing all draw on the same facts without
    stitching together multiple get_state.py fetches.

    Names-and-counts only — exact card/relic rules text still lives in the full
    state (get_state.py) and in the reward/shop offers, which stay verbatim.
    """
    sit = build_context(state)

    deck = _extract_deck(state)
    if deck:
        s = calculate_deck_stats(deck)
        sit["deck"] = {
            "size": s["total_cards"],
            "attacks": s["attacks"],
            "skills": s["skills"],
            "powers": s["powers"],
            "curses": s["curses"],
            "statuses": s["statuses"],
        }

    relics = _extract_relics(state)
    if relics:
        relic_names = [r.get("name") for r in relics if isinstance(r, dict) and r.get("name")]
        if relic_names:
            sit["relics"] = relic_names

    player = state.get("player") if isinstance(state.get("player"), dict) else {}
    potions = player.get("potions")
    if not isinstance(potions, list):
        potions = state.get("potions")
    if isinstance(potions, list):
        potion_names = [p.get("name") for p in potions if isinstance(p, dict) and p.get("name")]
        if potion_names:
            sit["potions"] = potion_names

    path = summarize_path(state)
    if path:
        sit["path_ahead"] = path

    return sit
