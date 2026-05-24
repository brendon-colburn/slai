"""
SLAI Knowledge Engine - Loads and queries the Baalorlord-grounded knowledge base.

Provides context-aware strategy retrieval based on current game state,
character, act position, deck composition, and player situation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("slai.knowledge_engine")

# Resolve the knowledge directory relative to this file
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


class KnowledgeEngine:
    """Loads and queries the SLAI coaching knowledge base."""

    def __init__(self, knowledge_dir: Path | None = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self.general_strategy: dict[str, Any] = {}
        self.pathing_strategy: dict[str, Any] = {}
        self.common_mistakes: dict[str, Any] = {}
        self.mechanics: dict[str, Any] = {}
        self.characters: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def load(self) -> bool:
        """Load all knowledge base files. Returns True if successful."""
        try:
            self.general_strategy = self._load_json("general_strategy.json")
            self.pathing_strategy = self._load_json("pathing_strategy.json")
            self.common_mistakes = self._load_json("common_mistakes.json")
            self.mechanics = self._load_json("mechanics.json")

            # Load character files
            characters_dir = self.knowledge_dir / "characters"
            if characters_dir.exists():
                for char_file in characters_dir.glob("*.json"):
                    char_name = char_file.stem
                    self.characters[char_name] = self._load_json(
                        f"characters/{char_file.name}"
                    )
                    logger.info(f"Loaded character knowledge: {char_name}")

            self._loaded = True
            logger.info(
                f"Knowledge base loaded: {len(self.characters)} characters, "
                f"{bool(self.general_strategy)} general, "
                f"{bool(self.pathing_strategy)} pathing"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            self._loaded = False
            return False

    def _load_json(self, filename: str) -> dict[str, Any]:
        """Load a JSON file from the knowledge directory."""
        filepath = self.knowledge_dir / filename
        if not filepath.exists():
            logger.warning(f"Knowledge file not found: {filepath}")
            return {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}")
            return {}

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def get_character_strategy(self, character: str) -> dict[str, Any]:
        """Get strategy guide for a specific character."""
        char_key = character.lower().strip().replace("the ", "")
        return self.characters.get(char_key, {})

    def get_four_pillars(self) -> dict[str, Any]:
        """Get the 4 Pillars of Deckbuilding framework."""
        return self.general_strategy.get("four_pillars", {})

    def get_pathing_advice(
        self,
        act: int = 1,
        hp_percentage: float = 100.0,
        character: str = "",
    ) -> dict[str, Any]:
        """
        Get contextual pathing advice.

        Args:
            act: Current act number (1-3)
            hp_percentage: Current HP as percentage of max
            character: Current character name
        """
        advice: dict[str, Any] = {
            "general": [],
            "act_specific": [],
            "hp_warning": None,
            "character_specific": [],
        }

        # General pathing principles
        pathing = self.pathing_strategy
        if pathing:
            advice["general"] = pathing.get("general_principles", [])

            # Act-specific advice
            act_key = f"act_{act}"
            if act_key in pathing:
                advice["act_specific"] = pathing[act_key]
            elif "act_guidance" in pathing:
                for act_data in pathing["act_guidance"]:
                    if act_data.get("act") == act:
                        advice["act_specific"] = act_data.get("tips", [])
                        break

        # HP-based warnings
        if hp_percentage < 30:
            advice["hp_warning"] = (
                "CRITICAL: HP is very low. Prioritize campfires for healing "
                "and avoid elites. Consider safer paths with events."
            )
        elif hp_percentage < 50:
            advice["hp_warning"] = (
                "CAUTION: HP is below 50%. Be selective about elite fights. "
                "Baalorlord recommends elites only above 50-60% HP."
            )
        elif hp_percentage < 60:
            advice["hp_warning"] = (
                "NOTE: HP is moderate. One more elite is fine if you have "
                "a strong deck, but plan for healing afterward."
            )

        # Character-specific pathing
        char_data = self.get_character_strategy(character)
        if char_data:
            advice["character_specific"] = char_data.get("pathing_notes", [])

        return advice

    def get_common_mistakes(self) -> list[dict[str, Any]]:
        """Get the list of common mistakes to check against."""
        mistakes = self.common_mistakes.get("mistakes", [])
        if not mistakes and isinstance(self.common_mistakes, list):
            mistakes = self.common_mistakes
        return mistakes

    def get_coaching_tip(
        self,
        game_screen: str = "",
        character: str = "",
        act: int = 1,
        floor: int = 1,
    ) -> str:
        """
        Get a contextual coaching tip based on current game state.

        Args:
            game_screen: Current screen type (combat, map, reward, shop, rest, event)
            character: Current character
            act: Current act
            floor: Current floor
        """
        tips = []

        # Screen-specific tips
        if game_screen == "combat":
            tips.extend(self._get_combat_tips(character))
        elif game_screen == "map":
            tips.extend(self._get_map_tips(act))
        elif game_screen in ("reward", "card_reward"):
            tips.extend(self._get_reward_tips(character))
        elif game_screen == "shop":
            tips.extend(self._get_shop_tips())
        elif game_screen in ("rest", "campfire"):
            tips.extend(self._get_rest_tips())
        elif game_screen == "event":
            tips.extend(self._get_event_tips())

        # Add general tips
        general = self.general_strategy
        if general:
            resource_tips = general.get("resource_management", {})
            if resource_tips:
                potion_advice = resource_tips.get("potion_usage", {})
                if isinstance(potion_advice, dict):
                    tips.append(
                        potion_advice.get(
                            "core_advice",
                            "Use potions aggressively on elites — don't hoard them.",
                        )
                    )

        if not tips:
            tips.append(
                "💡 Baalorlord's core advice: Focus on the 4 Pillars — "
                "Damage Output, Cycle Time, Block Density, and Upgrade Density."
            )

        # Return a single tip (cycle through them based on floor)
        return tips[floor % len(tips)] if tips else "Keep climbing the Spire!"

    def _get_combat_tips(self, character: str) -> list[str]:
        tips = [
            "🗡️ Think about energy efficiency: play high-impact cards first.",
            "🗡️ Check enemy intents — adjust between blocking and attacking.",
            "🗡️ If an enemy is about to die, don't over-invest in killing it.",
            "🗡️ Consider the order you play cards — buffs before multi-hit attacks.",
        ]
        char_data = self.get_character_strategy(character)
        if char_data:
            combat_tips = char_data.get("combat_tips", [])
            tips.extend(combat_tips)
        return tips

    def _get_map_tips(self, act: int) -> list[str]:
        tips = [
            "🗺️ Plan your entire path before committing. Look ahead!",
            "🗺️ Ensure a campfire before the boss fight.",
            "🗺️ Balance risk (elites) with safety (campfires, events).",
        ]
        if act == 1:
            tips.append(
                "🗺️ Act 1: Build your deck with frontloaded damage. "
                "1-2 elites if above 60% HP."
            )
        elif act == 2:
            tips.append(
                "🗺️ Act 2: Refine your deck. Be cautious with elites. "
                "Look for scaling and consistency."
            )
        return tips

    def _get_reward_tips(self, character: str) -> list[str]:
        return [
            "🃏 Ask: What JOB does this card do for my deck?",
            "🃏 It's okay to SKIP! A smaller, focused deck is often stronger.",
            "🃏 Don't chase archetypes — take cards that solve immediate problems.",
            "🃏 Baalorlord targets 20-25 card decks. Be selective.",
        ]

    def _get_shop_tips(self) -> list[str]:
        return [
            "🏪 Card removal is often the best purchase at shops.",
            "🏪 Buy potions if you're about to fight an elite.",
            "🏪 Relics at shops are expensive but can be game-changing.",
            "🏪 Don't buy cards just because they're available — skip is free.",
        ]

    def _get_rest_tips(self) -> list[str]:
        return [
            "🔥 Baalorlord says: Upgrade > Rest when above 50% HP.",
            "🔥 Upgrade your highest-impact card, not just the first one.",
            "🔥 Consider: which upgraded card will save the most HP over the act?",
        ]

    def _get_event_tips(self) -> list[str]:
        return [
            "❓ Read all event options carefully before choosing.",
            "❓ Some events offer card removal — highly valuable!",
            "❓ Events that offer max HP upgrades are generally worth the risk.",
        ]

    def get_mechanic_info(self, keyword: str) -> dict[str, Any]:
        """Look up information about a specific STS2 mechanic."""
        if not self.mechanics:
            return {"error": "Mechanics knowledge not loaded"}

        keyword_lower = keyword.lower().strip()
        mechanics_list = self.mechanics.get("mechanics", [])

        if isinstance(mechanics_list, list):
            for mech in mechanics_list:
                if mech.get("name", "").lower() == keyword_lower:
                    return mech
                if keyword_lower in [
                    k.lower() for k in mech.get("keywords", [])
                ]:
                    return mech

        # Also check top-level keys
        if keyword_lower in self.mechanics:
            return self.mechanics[keyword_lower]

        return {"error": f"No information found for mechanic: {keyword}"}

    def format_coaching_response(
        self,
        game_state: dict[str, Any],
        analysis: dict[str, Any],
    ) -> str:
        """
        Format a comprehensive coaching response combining game state
        analysis with knowledge base guidance.
        """
        parts = []

        # Character context
        character = analysis.get("character", "unknown")
        char_data = self.get_character_strategy(character)
        if char_data:
            identity = char_data.get("identity", "")
            if identity:
                parts.append(f"**{character.title()} Identity:** {identity}")

        # Pillar scores summary
        scores = analysis.get("pillar_scores", {})
        if scores:
            parts.append("\n**📊 4-Pillar Assessment:**")
            for pillar, score in scores.items():
                label = pillar.replace("_", " ").title()
                bar = "█" * (score // 10) + "░" * (10 - score // 10)
                parts.append(f"  {label}: {bar} {score}/100")

        # Insights
        insights = analysis.get("insights", [])
        if insights:
            parts.append("\n**💡 Insights:**")
            for insight in insights:
                parts.append(f"  {insight}")

        # Warnings
        warnings = analysis.get("warnings", [])
        if warnings:
            parts.append("\n**⚠️ Warnings:**")
            for warning in warnings:
                parts.append(f"  ⚠️ {warning}")

        return "\n".join(parts) if parts else "No coaching data available."
