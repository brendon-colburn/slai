# SLAI — Slay the Spire 2 Learning with AI

A real-time coaching layer for [Slay the Spire 2](https://store.steampowered.com/app/2868840/Slay_the_Spire_2/). Not a bot — a coach. SLAI reads your live game state and answers strategic questions grounded in **[Baalorlord's](https://www.twitch.tv/baalorlord)** teachings: the 4 Pillars of Deckbuilding, card evaluation, pathing philosophy, and character-specific strategies.

You ask the questions, you make every click. SLAI just makes you better at making those clicks.

## What you get

- **`/sts2-coach` Skill** for Claude Code / Claude Desktop — ask anything mid-run ("should I take this card?", "how am I doing?", "what's the boss?") and get an answer grounded in your actual deck, HP, gold, floor, and screen state.
- **Coaching MCP server** (Python) — 10 tools that wrap live STS2MCP data with structured analysis: 4-pillar scoring, card-reward grading (S/A/B/C/D/F), mistake detection, pathing advice.
- **Knowledge base** (~2,600 lines of structured JSON) — encodes Baalorlord's 4 Pillars framework, character strategies for all 5 characters, common mistakes, pathing philosophy, and STS2 mechanics.

## Architecture

```
┌──────────────────────┐      HTTP       ┌──────────────────┐    MCP    ┌──────────────────────┐
│  STS2 + STS2MCP mod  │ ──────────────► │  SLAI MCP server │ ────────► │  Claude Code /       │
│  (game-side, .dll)   │  localhost:15526│  (Python, this   │           │  Claude Desktop      │
│                      │                 │   repo)          │           │  + sts2-coach Skill  │
└──────────────────────┘                 └──────────────────┘           └──────────────────────┘
```

SLAI is a *pure read-only client* of STS2MCP. It never plays the game; you do. SLAI only reads your state and gives you advice.

## Prerequisites

1. **Slay the Spire 2** on Steam.
2. **[STS2MCP](https://github.com/Gennadiyev/STS2MCP)** mod installed — this is what exposes the game's state via HTTP. See its README for install steps. Tested against v0.4.0+.
3. **Python 3.11+** (3.13 recommended).
4. **Claude Code** or Claude Desktop — for using the Skill.

## Install

```bash
# 1. Clone
git clone https://github.com/brendoncolburn/slai.git
cd slai

# 2. Install Python deps
pip install mcp httpx pydantic

# 3. Add SLAI to your Claude Code MCP config (.mcp.json in any project you want to use it from)
```

`.mcp.json` example (Windows; adjust paths):

```json
{
  "mcpServers": {
    "slai": {
      "command": "C:\\path\\to\\python.exe",
      "args": ["C:\\path\\to\\slai\\mcp-server\\server.py"]
    }
  }
}
```

The skill at `skills/sts2-coach/SKILL.md` is auto-discovered by Claude Code when placed under `.claude/skills/sts2-coach/` in your project root or your user-level skills directory.

## Use

1. Launch Slay the Spire 2 with STS2MCP enabled.
2. Open Claude Code in a directory with SLAI configured (`.mcp.json` + skill present).
3. Type `/sts2-coach`.
4. Ask anything: *"how am I doing?"*, *"should I take Setup Strike?"*, *"path to the boss?"*

The coach pulls your live state and answers with Baalorlord-grounded reasoning. Specific card advice, deck-aware reward grading, HP-aware pathing — never generic.

## What the Skill knows

| Question type | Tool the Skill calls | What it returns |
|---|---|---|
| "How am I doing?" | `get_coaching_state` | Full state + pillar scores + contextual tip |
| Deck health | `analyze_deck` | 4-pillar scores, insights, warnings |
| Card reward | `evaluate_card_reward` | Per-card S/A/B/C/D/F with reasoning |
| Pathing | `suggest_map_path` | HP-aware advice grounded in act phase |
| Mistakes | `check_mistakes` | Active warnings (bloat, low block, gold hoarding, etc.) |
| Mechanic ("what's Doom?") | `explain_mechanic` | Knowledge-base lookup + context |
| Character guide | `get_character_guide` | Full strategy for ironclad / silent / defect / necrobinder / regent |
| Free-form | `ask_coach` | Contextual answer using all knowledge |
| Connection | `check_connection` | Is STS2MCP reachable? |

## Visual breakdowns

Ask for visuals and Claude will generate them as one-shot artifacts using your live data — radar charts, cost curves, type breakdowns, exhaust pile contents. No static dashboard; each visualization is shaped to the question. *"Show me my deck as a cost curve"* → fresh chart from current state.

## Status

Early. Built mid-run as a coaching tool for one player; published in case others want to use or extend it. The Knowledge base in particular benefits from corrections — if you spot Baalorlord advice that's misrepresented, open an issue or PR.

## Acknowledgments

- **Baalorlord** ([Twitch](https://www.twitch.tv/baalorlord) / [YouTube](https://www.youtube.com/@baalorlord)) — the strategic teachings encoded in `knowledge/` paraphrase his publicly-available coaching content. SLAI is unaffiliated with Baalorlord; any misrepresentation is ours, not his.
- **[STS2MCP](https://github.com/Gennadiyev/STS2MCP)** by Yikun Ji (Kunologist) — the in-game mod that makes any of this possible.
- **Mega Crit** — for [Slay the Spire 2](https://store.steampowered.com/app/2868840/Slay_the_Spire_2/).

See [ATTRIBUTION.md](ATTRIBUTION.md) for details.

## License

MIT. See [LICENSE](LICENSE).
