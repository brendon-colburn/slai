"""
SLAI Deck Analyzer - Evaluates decks against Baalorlord's 4 Pillars framework.

Provides quantitative analysis of deck composition to help players
understand their deck's strengths and weaknesses.
"""

import logging
from typing import Any

logger = logging.getLogger("slai.deck_analyzer")

# Cards that are generally considered "block" cards across all characters
UNIVERSAL_BLOCK_KEYWORDS = ["block", "defend", "shield", "armor", "barrier"]
UNIVERSAL_ATTACK_KEYWORDS = ["damage", "attack", "strike", "hit"]
UNIVERSAL_DRAW_KEYWORDS = ["draw", "cycle", "scry"]

# Default starting deck sizes per character
STARTING_DECK_SIZES = {
    "ironclad": 10,
    "silent": 12,
    "defect": 10,
    "necrobinder": 10,
    "regent": 10,
}

# Base draw per turn (most characters draw 5)
BASE_DRAW_PER_TURN = 5


class DeckAnalyzer:
    """Analyzes deck composition against the 4 Pillars framework."""

    def __init__(self, knowledge: dict[str, Any] | None = None):
        """
        Initialize the deck analyzer.

        Args:
            knowledge: Optional knowledge base data for enhanced analysis.
        """
        self.knowledge = knowledge or {}

    def analyze(self, game_state: dict[str, Any]) -> dict[str, Any]:
        """
        Perform a full deck analysis and return pillar scores + insights.

        Args:
            game_state: The current game state from STS2MCP.

        Returns:
            Dict with pillar_scores, deck_stats, insights, and warnings.
        """
        deck = self._extract_deck(game_state)
        character = self._extract_character(game_state)
        relics = self._extract_relics(game_state)

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
            }

        # Calculate individual metrics
        deck_stats = self._calculate_deck_stats(deck)
        pillar_scores = self._calculate_pillar_scores(deck, deck_stats, relics)
        insights = self._generate_insights(deck_stats, pillar_scores, character)
        warnings = self._detect_warnings(deck_stats, pillar_scores, character, game_state)

        return {
            "pillar_scores": pillar_scores,
            "deck_stats": deck_stats,
            "insights": insights,
            "warnings": warnings,
            "character": character,
        }

    def _extract_deck(self, game_state: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract the deck list from game state."""
        # STS2MCP stores deck in various locations depending on state
        deck = game_state.get("deck", [])
        if not deck:
            deck = game_state.get("master_deck", [])
        if not deck and "player" in game_state:
            deck = game_state["player"].get("deck", [])
        if not deck and "run" in game_state:
            deck = game_state["run"].get("deck", [])
        return deck if isinstance(deck, list) else []

    def _extract_character(self, game_state: dict[str, Any]) -> str:
        """Extract the character name from game state."""
        char = game_state.get("character", "")
        if not char and "player" in game_state:
            char = game_state["player"].get("character", "")
        if not char and "run" in game_state:
            char = game_state["run"].get("character", "")
        return str(char).lower().strip()

    def _extract_relics(self, game_state: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract relics from game state."""
        relics = game_state.get("relics", [])
        if not relics and "player" in game_state:
            relics = game_state["player"].get("relics", [])
        return relics if isinstance(relics, list) else []

    def _calculate_deck_stats(self, deck: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate raw deck statistics."""
        total_cards = len(deck)
        attacks = 0
        skills = 0
        powers = 0
        curses = 0
        statuses = 0
        upgraded = 0
        block_cards = 0
        draw_cards = 0
        cost_distribution: dict[str, int] = {"0": 0, "1": 0, "2": 0, "3": 0, "X": 0}

        for card in deck:
            card_type = str(card.get("type", "")).lower()
            card_name = str(card.get("name", "")).lower()
            card_desc = str(card.get("description", "")).lower()
            is_upgraded = card.get("upgraded", False) or card.get("upgrade_count", 0) > 0

            # Classify by type
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

            # Check for block
            if any(kw in card_name or kw in card_desc for kw in UNIVERSAL_BLOCK_KEYWORDS):
                block_cards += 1

            # Check for draw
            if any(kw in card_name or kw in card_desc for kw in UNIVERSAL_DRAW_KEYWORDS):
                draw_cards += 1

            # Upgraded
            if is_upgraded:
                upgraded += 1

            # Cost distribution
            cost = str(card.get("cost", card.get("energy_cost", "1")))
            if cost in cost_distribution:
                cost_distribution[cost] += 1
            elif cost.upper() == "X":
                cost_distribution["X"] += 1

        # Calculate densities
        playable_cards = total_cards - curses - statuses
        block_density = (block_cards / playable_cards * 100) if playable_cards > 0 else 0
        upgrade_density = (upgraded / playable_cards * 100) if playable_cards > 0 else 0
        attack_density = (attacks / playable_cards * 100) if playable_cards > 0 else 0

        # Estimate cycle time (turns to see full deck)
        effective_draw = BASE_DRAW_PER_TURN + (draw_cards * 0.5)  # rough estimate
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

    def _calculate_pillar_scores(
        self,
        deck: list[dict[str, Any]],
        stats: dict[str, Any],
        relics: list[dict[str, Any]],
    ) -> dict[str, int]:
        """
        Calculate 0-100 scores for each of the 4 Pillars.

        Scoring is based on Baalorlord's guidelines:
        - Damage Output: Attack density + power presence + scaling potential
        - Cycle Time: Deck size efficiency + draw card count
        - Block Density: Target ~33%, penalize too low or too high
        - Upgrade Density: Higher is better, especially early acts
        """
        # --- Damage Output (0-100) ---
        # Good: healthy mix of attacks with some scaling (powers)
        attack_score = min(stats["attack_density_pct"] * 1.5, 60)  # up to 60 pts from attacks
        power_score = min(stats["powers"] * 10, 30)  # up to 30 pts from powers (scaling)
        damage_score = int(min(attack_score + power_score + 10, 100))  # 10 base

        # --- Cycle Time (0-100) ---
        # Ideal deck size: 20-25 cards. Penalize bloat heavily.
        total = stats["total_cards"]
        if total <= 15:
            size_score = 70  # Tiny deck — very fast but may lack options
        elif total <= 20:
            size_score = 90  # Lean and efficient
        elif total <= 25:
            size_score = 85  # Good range
        elif total <= 30:
            size_score = 60  # Getting bloated
        elif total <= 35:
            size_score = 40  # Bloated
        else:
            size_score = max(20, 100 - total * 2)  # Very bloated

        draw_bonus = min(stats["draw_cards"] * 8, 30)  # Draw cards help cycle
        cycle_score = int(min(size_score + draw_bonus, 100))

        # --- Block Density (0-100) ---
        # Target: ~33% (Baalorlord's recommendation)
        block_pct = stats["block_density_pct"]
        if block_pct < 10:
            block_score = 20  # Dangerously low
        elif block_pct < 20:
            block_score = 50  # Below target
        elif block_pct < 28:
            block_score = 75  # Approaching target
        elif block_pct <= 38:
            block_score = 95  # Sweet spot around 33%
        elif block_pct <= 50:
            block_score = 70  # Slightly too defensive
        else:
            block_score = 40  # Way too defensive, not enough offense

        # --- Upgrade Density (0-100) ---
        upgrade_pct = stats["upgrade_density_pct"]
        upgrade_score = int(min(upgrade_pct * 1.8, 100))  # Linear scale

        return {
            "damage_output": max(0, min(100, damage_score)),
            "cycle_time": max(0, min(100, cycle_score)),
            "block_density": max(0, min(100, block_score)),
            "upgrade_density": max(0, min(100, upgrade_score)),
        }

    def _generate_insights(
        self,
        stats: dict[str, Any],
        scores: dict[str, int],
        character: str,
    ) -> list[str]:
        """Generate human-readable insights about the deck."""
        insights = []

        # Deck size insight
        total = stats["total_cards"]
        if total <= 20:
            insights.append(f"🎯 Lean deck ({total} cards) — great cycle time!")
        elif total <= 25:
            insights.append(f"📊 Healthy deck size ({total} cards) — good balance.")
        elif total <= 30:
            insights.append(
                f"📈 Deck getting large ({total} cards) — consider skipping future card rewards."
            )
        else:
            insights.append(
                f"⚠️ Bloated deck ({total} cards) — Baalorlord recommends 20-25 cards. "
                f"Skip cards and look for removal opportunities."
            )

        # Block density insight
        block_pct = stats["block_density_pct"]
        if block_pct < 20:
            insights.append(
                f"🛡️ Low block density ({block_pct:.0f}%) — Baalorlord targets ~33%. "
                f"Look for block cards to survive harder encounters."
            )
        elif 28 <= block_pct <= 38:
            insights.append(
                f"🛡️ Block density ({block_pct:.0f}%) is in the sweet spot (~33% target)."
            )
        elif block_pct > 50:
            insights.append(
                f"🛡️ Very high block density ({block_pct:.0f}%) — "
                f"you might struggle to kill enemies fast enough."
            )

        # Upgrade density insight
        upgrade_pct = stats["upgrade_density_pct"]
        if upgrade_pct < 20:
            insights.append(
                f"⬆️ Low upgrade density ({upgrade_pct:.0f}%) — "
                f"prioritize upgrading at campfires over resting when above 50% HP."
            )
        elif upgrade_pct > 50:
            insights.append(
                f"⬆️ Excellent upgrade density ({upgrade_pct:.0f}%) — well invested!"
            )

        # Powers insight
        if stats["powers"] == 0:
            insights.append(
                "⚡ No Power cards — your deck lacks scaling. "
                "Powers provide permanent effects that grow stronger over long fights."
            )
        elif stats["powers"] >= 4:
            insights.append(
                f"⚡ Strong power presence ({stats['powers']} powers) — "
                f"good scaling potential for boss fights."
            )

        # Curses/statuses
        if stats["curses"] > 0:
            insights.append(
                f"💀 {stats['curses']} curse(s) in deck — "
                f"look for removal opportunities at shops or events."
            )

        return insights

    def _detect_warnings(
        self,
        stats: dict[str, Any],
        scores: dict[str, int],
        character: str,
        game_state: dict[str, Any],
    ) -> list[str]:
        """Detect common mistakes based on Baalorlord's teachings."""
        warnings = []

        # Card Bloat (Mistake #1)
        if stats["total_cards"] > 27:
            warnings.append(
                f"CARD_BLOAT: Deck has {stats['total_cards']} cards. "
                f"Baalorlord recommends 20-25. Skip more card rewards!"
            )

        # Low damage in late game
        floor_num = game_state.get("floor", game_state.get("current_floor", 0))
        if isinstance(floor_num, (int, float)) and floor_num > 15:
            if scores["damage_output"] < 40:
                warnings.append(
                    "LOW_DAMAGE: Damage output is low for this point in the run. "
                    "You may struggle with Act 2+ bosses."
                )

        # No block
        if stats["block_density_pct"] < 15:
            warnings.append(
                "NO_BLOCK: Block density is dangerously low. "
                "Prioritize picking up block cards."
            )

        # Too many curses
        if stats["curses"] >= 3:
            warnings.append(
                f"CURSE_HEAVY: {stats['curses']} curses are severely hampering your deck. "
                f"Remove them ASAP at shops."
            )

        # No upgrades late
        if isinstance(floor_num, (int, float)) and floor_num > 10:
            if stats["upgrade_density_pct"] < 10:
                warnings.append(
                    "NO_UPGRADES: Very few upgraded cards. "
                    "Baalorlord says upgrading is usually better than resting at campfires."
                )

        return warnings

    def get_card_reward_evaluation(
        self,
        card_options: list[dict[str, Any]],
        deck: list[dict[str, Any]],
        character: str,
    ) -> list[dict[str, Any]]:
        """
        Evaluate card reward options based on current deck needs.

        Returns a list of evaluations with grade and reasoning.
        """
        stats = self._calculate_deck_stats(deck)
        scores = self._calculate_pillar_scores(deck, stats, [])
        evaluations = []

        for card in card_options:
            card_name = str(card.get("name", "Unknown"))
            card_type = str(card.get("type", "")).lower()
            grade = "C"
            reasons = []

            # Check if the deck NEEDS what this card provides
            if card_type == "attack" and scores["damage_output"] < 50:
                grade = self._upgrade_grade(grade)
                reasons.append("Your deck needs more damage output")
            elif card_type == "skill" and scores["block_density"] < 50:
                grade = self._upgrade_grade(grade)
                reasons.append("Your deck needs more block")
            elif card_type == "power":
                grade = self._upgrade_grade(grade)
                reasons.append("Powers provide valuable scaling")

            # Penalize if deck is already bloated
            if stats["total_cards"] > 25:
                grade = self._downgrade_grade(grade)
                reasons.append("Deck is getting large — consider skipping")

            # Draw cards are almost always good
            card_desc = str(card.get("description", "")).lower()
            if "draw" in card_desc:
                grade = self._upgrade_grade(grade)
                reasons.append("Card draw improves cycle time")

            evaluations.append({
                "card_name": card_name,
                "grade": grade,
                "reasons": reasons,
                "card_type": card_type,
            })

        return evaluations

    @staticmethod
    def _upgrade_grade(grade: str) -> str:
        grades = ["F", "D", "C", "B", "A", "S"]
        idx = grades.index(grade) if grade in grades else 2
        return grades[min(idx + 1, len(grades) - 1)]

    @staticmethod
    def _downgrade_grade(grade: str) -> str:
        grades = ["F", "D", "C", "B", "A", "S"]
        idx = grades.index(grade) if grade in grades else 2
        return grades[max(idx - 1, 0)]
