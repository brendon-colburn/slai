"""
SLAI MCP Server - Slay the Spire 2 Learning with AI

An MCP server that provides AI coaching for Slay the Spire 2.
Reads game state from STS2MCP (read-only) and provides strategic advice
grounded in Baalorlord's expert teachings.

Usage:
    python server.py [--host HOST] [--port PORT]

    Or via MCP config:
    {
        "mcpServers": {
            "slai": {
                "command": "uv",
                "args": ["run", "--directory", "/path/to/slai/mcp-server", "python", "server.py"]
            }
        }
    }
"""

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from game_client import GameClient
from knowledge_engine import KnowledgeEngine
from deck_analyzer import DeckAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("slai")

# Parse command line arguments
parser = argparse.ArgumentParser(description="SLAI - STS2 AI Coach MCP Server")
parser.add_argument(
    "--host",
    default="localhost",
    help="STS2MCP host (default: localhost)",
)
parser.add_argument(
    "--port",
    type=int,
    default=15526,
    help="STS2MCP port (default: 15526)",
)
parser.add_argument(
    "--help-tools",
    action="store_true",
    help="Print available tools and exit",
)

# ─── Initialize Components ───────────────────────────────────────────────────

app = Server("slai")
game_client: GameClient | None = None
knowledge: KnowledgeEngine | None = None
analyzer: DeckAnalyzer | None = None


def _init_components(host: str = "localhost", port: int = 15526):
    """Initialize the game client, knowledge engine, and deck analyzer."""
    global game_client, knowledge, analyzer

    game_client = GameClient(host=host, port=port)

    knowledge = KnowledgeEngine()
    if knowledge.load():
        logger.info("Knowledge base loaded successfully")
    else:
        logger.warning(
            "Knowledge base not fully loaded — coaching quality may be reduced"
        )

    analyzer = DeckAnalyzer(knowledge=knowledge.general_strategy if knowledge else None)
    logger.info("SLAI components initialized")


# ─── Tool Definitions ────────────────────────────────────────────────────────

TOOLS = [
    Tool(
        name="get_coaching_state",
        description=(
            "Get the current game state enriched with coaching analysis. "
            "Returns the raw game state from STS2MCP plus deck pillar scores, "
            "insights, and contextual coaching tips from Baalorlord's teachings."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["json", "markdown"],
                    "default": "json",
                    "description": "Use 'json' for combat (structured), 'markdown' for map/events (overview)",
                }
            },
        },
    ),
    Tool(
        name="analyze_deck",
        description=(
            "Analyze the current deck against Baalorlord's 4 Pillars framework: "
            "Damage Output, Cycle Time, Block Density, and Upgrade Density. "
            "Returns scores (0-100), insights, and warnings."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="evaluate_card_reward",
        description=(
            "When the player is offered a card reward, evaluate the options "
            "based on what the deck currently needs. Returns grades (S/A/B/C/D/F) "
            "and reasoning for each card option."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="suggest_map_path",
        description=(
            "Provide pathing advice based on current HP, deck strength, and "
            "position in the act. Grounded in Baalorlord's pathing philosophy: "
            "Look Ahead Method, elite risk assessment, campfire prioritization."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_coaching_tip",
        description=(
            "[DEPRECATED for Skill use — prefer the CAG knowledge bundle at "
            "skills/sts2-coach/knowledge.md, which has full strategic context.] "
            "Get a contextual coaching tip from Baalorlord's knowledge base "
            "based on the current game screen (combat, map, reward, shop, rest, event). "
            "Tips are character-aware and situation-specific."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="check_mistakes",
        description=(
            "Review the current game state for common mistakes that "
            "Baalorlord identifies: Card Bloat, Forcing Archetypes Early, "
            "Ignoring Pathing, Playing on Autopilot, Hoarding Potions, "
            "Misunderstanding Card Value."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ask_coach",
        description=(
            "Ask the AI coach a free-form question about Slay the Spire 2 strategy. "
            "The coach will answer using the knowledge base grounded in "
            "Baalorlord's teachings, with full awareness of your current game state."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Your strategy question",
                }
            },
            "required": ["question"],
        },
    ),
    Tool(
        name="explain_mechanic",
        description=(
            "[DEPRECATED for Skill use — prefer the CAG knowledge bundle at "
            "skills/sts2-coach/knowledge.md, which has the same mechanic data "
            "and more. Kept for non-Skill MCP clients.] "
            "Look up and explain a Slay the Spire 2 mechanic or keyword. "
            "Covers: Sly, Forge, Doom, Stars, Souls, Enchantments, Afflictions, "
            "Orbs, Exhaust, Ethereal, Retain, and more."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "The mechanic or keyword to explain (e.g., 'Sly', 'Doom', 'Forge')",
                }
            },
            "required": ["keyword"],
        },
    ),
    Tool(
        name="get_character_guide",
        description=(
            "[DEPRECATED for Skill use — prefer the CAG knowledge bundle at "
            "skills/sts2-coach/knowledge.md, which contains every character guide "
            "in full. Kept for non-Skill MCP clients.] "
            "Get a comprehensive strategy guide for a specific character "
            "based on Baalorlord's teachings. Covers key archetypes, "
            "important cards, act-by-act plans, and common pitfalls."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "character": {
                    "type": "string",
                    "description": "Character name: ironclad, silent, defect, necrobinder, or regent",
                }
            },
            "required": ["character"],
        },
    ),
    Tool(
        name="check_connection",
        description=(
            "Check if STS2MCP is running and the game is connected. "
            "Returns connection status and version info."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available coaching tools."""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    assert game_client is not None
    assert knowledge is not None
    assert analyzer is not None

    try:
        if name == "check_connection":
            result = await game_client.check_connection()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_coaching_state":
            fmt = arguments.get("format", "json")
            state = await game_client.get_game_state(format=fmt)

            if "error" in state:
                return [TextContent(type="text", text=json.dumps(state, indent=2))]

            # Enrich with coaching analysis
            analysis = analyzer.analyze(state)
            character = analysis.get("character", "")

            # Get contextual tip
            screen = state.get("screen", state.get("current_screen", "unknown"))
            floor = state.get("floor", state.get("current_floor", 1))
            act = state.get("act", 1)
            tip = knowledge.get_coaching_tip(
                game_screen=str(screen),
                character=character,
                act=int(act) if isinstance(act, (int, float)) else 1,
                floor=int(floor) if isinstance(floor, (int, float)) else 1,
            )

            coaching_response = {
                "game_state": state,
                "coaching": {
                    "pillar_scores": analysis["pillar_scores"],
                    "deck_stats": analysis["deck_stats"],
                    "insights": analysis["insights"],
                    "warnings": analysis["warnings"],
                    "tip": tip,
                },
            }

            return [
                TextContent(
                    type="text",
                    text=json.dumps(coaching_response, indent=2, default=str),
                )
            ]

        elif name == "analyze_deck":
            state = await game_client.get_game_state(format="json")
            if "error" in state:
                return [TextContent(type="text", text=json.dumps(state, indent=2))]

            analysis = analyzer.analyze(state)
            formatted = knowledge.format_coaching_response(state, analysis)
            return [TextContent(type="text", text=formatted)]

        elif name == "evaluate_card_reward":
            state = await game_client.get_game_state(format="json")
            if "error" in state:
                return [TextContent(type="text", text=json.dumps(state, indent=2))]

            # Extract card reward options from state
            card_options = (
                state.get("card_rewards", [])
                or state.get("rewards", {}).get("cards", [])
                or []
            )
            deck = (
                state.get("deck", [])
                or state.get("master_deck", [])
                or state.get("player", {}).get("deck", [])
                or []
            )
            character = (
                state.get("character", "")
                or state.get("player", {}).get("character", "")
            )

            if not card_options:
                return [
                    TextContent(
                        type="text",
                        text="No card reward currently available. This tool works when you're at a card reward screen.",
                    )
                ]

            evaluations = analyzer.get_card_reward_evaluation(
                card_options, deck, str(character)
            )

            response_parts = ["**🃏 Card Reward Evaluation:**\n"]
            for ev in evaluations:
                grade_emoji = {
                    "S": "🌟",
                    "A": "💎",
                    "B": "✅",
                    "C": "➡️",
                    "D": "⬇️",
                    "F": "❌",
                }.get(ev["grade"], "❓")
                response_parts.append(
                    f"{grade_emoji} **{ev['card_name']}** — Grade: **{ev['grade']}**"
                )
                for reason in ev["reasons"]:
                    response_parts.append(f"    • {reason}")
                response_parts.append("")

            response_parts.append(
                "\n💡 **Baalorlord's reminder:** It's always okay to **SKIP**! "
                "A smaller, focused deck (20-25 cards) is usually stronger."
            )

            return [TextContent(type="text", text="\n".join(response_parts))]

        elif name == "suggest_map_path":
            state = await game_client.get_game_state(format="json")
            if "error" in state:
                return [TextContent(type="text", text=json.dumps(state, indent=2))]

            # Extract relevant info
            act = state.get("act", 1)
            hp = state.get("current_hp", state.get("player", {}).get("hp", 50))
            max_hp = state.get(
                "max_hp", state.get("player", {}).get("max_hp", 80)
            )
            hp_pct = (hp / max_hp * 100) if max_hp > 0 else 100

            character = (
                state.get("character", "")
                or state.get("player", {}).get("character", "")
            )

            advice = knowledge.get_pathing_advice(
                act=int(act) if isinstance(act, (int, float)) else 1,
                hp_percentage=hp_pct,
                character=str(character),
            )

            response_parts = [
                f"**🗺️ Pathing Advice (Act {act}, HP: {hp}/{max_hp} = {hp_pct:.0f}%):**\n"
            ]

            if advice["hp_warning"]:
                response_parts.append(f"⚠️ {advice['hp_warning']}\n")

            if advice["general"]:
                response_parts.append("**General Principles:**")
                for tip in advice["general"][:5]:
                    if isinstance(tip, str):
                        response_parts.append(f"  • {tip}")
                    elif isinstance(tip, dict):
                        response_parts.append(
                            f"  • {tip.get('tip', tip.get('description', str(tip)))}"
                        )

            if advice["act_specific"]:
                response_parts.append(f"\n**Act {act} Priorities:**")
                for tip in advice["act_specific"][:5]:
                    if isinstance(tip, str):
                        response_parts.append(f"  • {tip}")
                    elif isinstance(tip, dict):
                        response_parts.append(
                            f"  • {tip.get('tip', tip.get('description', str(tip)))}"
                        )

            return [TextContent(type="text", text="\n".join(response_parts))]

        elif name == "get_coaching_tip":
            state = await game_client.get_game_state(format="json")
            if "error" in state:
                return [TextContent(type="text", text=json.dumps(state, indent=2))]

            screen = str(
                state.get("screen", state.get("current_screen", "unknown"))
            )
            character = str(
                state.get("character", "")
                or state.get("player", {}).get("character", "")
            )
            act = state.get("act", 1)
            floor = state.get("floor", state.get("current_floor", 1))

            tip = knowledge.get_coaching_tip(
                game_screen=screen,
                character=character,
                act=int(act) if isinstance(act, (int, float)) else 1,
                floor=int(floor) if isinstance(floor, (int, float)) else 1,
            )

            return [TextContent(type="text", text=f"💡 **Coach's Tip:** {tip}")]

        elif name == "check_mistakes":
            state = await game_client.get_game_state(format="json")
            if "error" in state:
                return [TextContent(type="text", text=json.dumps(state, indent=2))]

            analysis = analyzer.analyze(state)
            warnings = analysis.get("warnings", [])

            if not warnings:
                response = (
                    "✅ **No common mistakes detected!** Keep up the great play.\n\n"
                    "Baalorlord's 6 common mistakes to watch for:\n"
                    "1. Card Bloat (deck > 27 cards)\n"
                    "2. Forcing Archetypes Early\n"
                    "3. Ignoring Pathing Strategy\n"
                    "4. Playing on Autopilot\n"
                    "5. Hoarding Potions\n"
                    "6. Misunderstanding Card Value"
                )
            else:
                response_parts = ["**⚠️ Common Mistakes Detected:**\n"]
                for w in warnings:
                    parts = w.split(":", 1)
                    mistake_type = parts[0].strip() if len(parts) > 1 else "WARNING"
                    detail = parts[1].strip() if len(parts) > 1 else w
                    response_parts.append(f"⚠️ **{mistake_type}**: {detail}")

                response_parts.append(
                    "\n💡 Review Baalorlord's advice on these topics to improve!"
                )
                response = "\n".join(response_parts)

            return [TextContent(type="text", text=response)]

        elif name == "ask_coach":
            question = arguments.get("question", "")
            if not question:
                return [
                    TextContent(type="text", text="Please provide a question to ask the coach.")
                ]

            # Get current game state for context
            state = await game_client.get_game_state(format="json")
            analysis = analyzer.analyze(state) if "error" not in state else {}

            # Build a contextual response from the knowledge base
            response_parts = [f'**🎓 Coach\'s Answer to: "{question}"**\n']

            question_lower = question.lower()

            # Match question to knowledge areas
            if any(
                kw in question_lower
                for kw in ["pillar", "damage", "block", "cycle", "upgrade", "deck"]
            ):
                pillars = knowledge.get_four_pillars()
                if pillars:
                    response_parts.append("**The 4 Pillars of Deckbuilding:**")
                    for pillar_key, pillar_data in pillars.items():
                        name_clean = pillar_key.replace("_", " ").title()
                        desc = (
                            pillar_data.get("description", "")
                            if isinstance(pillar_data, dict)
                            else str(pillar_data)
                        )
                        response_parts.append(f"  **{name_clean}:** {desc}")

            if any(
                kw in question_lower
                for kw in ["path", "map", "route", "elite", "campfire"]
            ):
                response_parts.append("\n**Pathing Philosophy:**")
                response_parts.append(
                    "• Plan your entire path through the act before committing"
                )
                response_parts.append(
                    "• Ensure a campfire before boss fights"
                )
                response_parts.append(
                    "• Fight elites when above 60% HP (Act 1) or 50% HP (Act 2)"
                )
                response_parts.append(
                    "• Aim for 1 shop per act, ideally late-act with 300+ gold"
                )

            if any(
                kw in question_lower
                for kw in [
                    "ironclad", "silent", "defect", "necrobinder", "regent",
                    "character",
                ]
            ):
                for char_name in [
                    "ironclad", "silent", "defect", "necrobinder", "regent",
                ]:
                    if char_name in question_lower or "character" in question_lower:
                        char_data = knowledge.get_character_strategy(char_name)
                        if char_data:
                            identity = char_data.get("identity", "")
                            response_parts.append(
                                f"\n**{char_name.title()}:** {identity}"
                            )

            if any(
                kw in question_lower
                for kw in [
                    "mistake", "wrong", "bad", "improve", "better", "tip",
                ]
            ):
                response_parts.append("\n**Common Mistakes (Baalorlord):**")
                response_parts.append("1. Card Bloat — take fewer cards, target 20-25")
                response_parts.append(
                    "2. Forcing Archetypes — stay flexible, adapt to what the game offers"
                )
                response_parts.append(
                    "3. Ignoring Pathing — plan the full act, not just next node"
                )
                response_parts.append(
                    "4. Playing on Autopilot — slow down and think each turn"
                )
                response_parts.append(
                    "5. Hoarding Potions — use on elites, don't save for bosses"
                )
                response_parts.append(
                    "6. Misunderstanding Card Value — evaluate by deck need, not tier lists"
                )

            if any(
                kw in question_lower
                for kw in [
                    "sly", "forge", "doom", "star", "soul", "enchant", "afflict",
                    "orb", "focus",
                ]
            ):
                for kw in [
                    "sly", "forge", "doom", "stars", "souls",
                    "enchantment", "affliction", "orb",
                ]:
                    if kw in question_lower:
                        mech = knowledge.get_mechanic_info(kw)
                        if "error" not in mech:
                            response_parts.append(
                                f"\n**{kw.title()}:** {json.dumps(mech, indent=2, default=str)}"
                            )

            # Add current state context if available
            if analysis:
                scores = analysis.get("pillar_scores", {})
                if scores:
                    response_parts.append("\n**Your Current Pillar Scores:**")
                    for pillar, score in scores.items():
                        label = pillar.replace("_", " ").title()
                        response_parts.append(f"  {label}: {score}/100")

            if len(response_parts) <= 1:
                # Generic fallback
                response_parts.append(
                    "Based on Baalorlord's teachings, focus on the fundamentals:\n"
                    "• Balance the 4 Pillars (Damage, Cycle Time, Block, Upgrades)\n"
                    "• Keep your deck lean (20-25 cards)\n"
                    "• Use potions aggressively on elites\n"
                    "• Plan your path through the entire act\n"
                    "• Take cards that solve problems, not just 'good' cards"
                )

            return [TextContent(type="text", text="\n".join(response_parts))]

        elif name == "explain_mechanic":
            keyword = arguments.get("keyword", "")
            if not keyword:
                return [
                    TextContent(
                        type="text",
                        text="Please specify a mechanic to explain (e.g., 'Sly', 'Doom', 'Forge').",
                    )
                ]

            info = knowledge.get_mechanic_info(keyword)
            if "error" in info:
                return [TextContent(type="text", text=info["error"])]

            return [
                TextContent(
                    type="text",
                    text=f"**📖 {keyword.title()}:**\n\n{json.dumps(info, indent=2, default=str)}",
                )
            ]

        elif name == "get_character_guide":
            character = arguments.get("character", "")
            if not character:
                return [
                    TextContent(
                        type="text",
                        text="Please specify a character: ironclad, silent, defect, necrobinder, or regent",
                    )
                ]

            char_data = knowledge.get_character_strategy(character)
            if not char_data:
                return [
                    TextContent(
                        type="text",
                        text=f"No guide available for '{character}'. "
                        f"Available: ironclad, silent, defect, necrobinder, regent",
                    )
                ]

            return [
                TextContent(
                    type="text",
                    text=f"**📖 {character.title()} Guide (Baalorlord's Teachings):**\n\n"
                    f"{json.dumps(char_data, indent=2, default=str)}",
                )
            ]

        else:
            return [
                TextContent(type="text", text=f"Unknown tool: {name}")
            ]

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [
            TextContent(type="text", text=f"Error: {e}")
        ]


# ─── Main Entry Point ────────────────────────────────────────────────────────

async def main():
    args = parser.parse_args()

    if args.help_tools:
        print("SLAI - Slay the Spire 2 Learning with AI")
        print("=" * 50)
        print("\nAvailable coaching tools:\n")
        for tool in TOOLS:
            print(f"  {tool.name}")
            print(f"    {tool.description}\n")
        return

    logger.info("Starting SLAI MCP Server...")
    logger.info(f"STS2MCP target: {args.host}:{args.port}")

    _init_components(host=args.host, port=args.port)

    async with stdio_server() as (read_stream, write_stream):
        logger.info("SLAI MCP Server running via stdio")
        await app.run(read_stream, write_stream, app.create_initialization_options())

    # Cleanup
    if game_client:
        await game_client.close()


if __name__ == "__main__":
    asyncio.run(main())
