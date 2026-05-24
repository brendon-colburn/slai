# Architecture

SLAI is three layers stacked on a fourth dependency:

```
┌──────────────────────────────────────────────────────────┐
│  You (typing in Claude Code / Claude Desktop)            │
│  + sts2-coach Skill loaded                               │
└────────────────────────────┬─────────────────────────────┘
                             │ MCP tool calls
                             ▼
┌──────────────────────────────────────────────────────────┐
│  SLAI MCP Coaching Server  (Python, this repo)           │
│  • knowledge_engine — loads JSON, retrieves context      │
│  • deck_analyzer — scores 4 pillars, grades rewards      │
│  • game_client — HTTP wrapper around STS2MCP             │
│  • server — exposes 10 MCP tools                         │
└────────────────────────────┬─────────────────────────────┘
                             │ HTTP GET (read-only)
                             │ localhost:15526
                             ▼
┌──────────────────────────────────────────────────────────┐
│  STS2MCP mod  (C# DLL, in the game's mods/ folder)       │
│  • Lives inside Slay the Spire 2's Godot runtime         │
│  • Serializes live game state as JSON                    │
└────────────────────────────┬─────────────────────────────┘
                             │ Reflection / direct refs
                             ▼
┌──────────────────────────────────────────────────────────┐
│  Slay the Spire 2  (the game itself, on Steam)           │
└──────────────────────────────────────────────────────────┘
```

## What lives where

| Layer | What it does | Owns |
|---|---|---|
| Skill | Tells Claude how to coach; triages question type → tool | Prose: the *style* of coaching |
| MCP server | Pre-digests raw state into pillar scores and warnings | Deterministic numeric analysis |
| `knowledge/` | Baalorlord's framework encoded as queryable data | Strategy facts |
| STS2MCP mod | Bridges game internals to HTTP | Game state observation |
| The game | Runs your run | The truth |

## Why three layers and not two

You could imagine the Skill talking directly to STS2MCP and doing all reasoning in tokens. We *don't* because:

1. **Token efficiency.** Pillar scoring, card classification, and warning detection are deterministic. Computing them in Python costs ~0 LLM tokens; doing them in Claude costs hundreds of input tokens per query (read raw state, classify each card, sum, score).
2. **Determinism.** A 4-pillar score should be the same for the same input. A pure-LLM implementation drifts.
3. **Reusability.** The MCP server is useful from any MCP client, not just our Skill. If you want to script a deck-pillar regression test, you can call `analyze_deck` from a CLI.

## Data flow per question

User asks *"should I take Setup Strike?"*:

1. **Skill** receives the question, triages: "card reward → call `evaluate_card_reward`".
2. **MCP server**'s `evaluate_card_reward` tool calls **STS2MCP** for current state (`/api/v1/singleplayer`).
3. STS2MCP returns JSON with `player.master_deck`, `card_reward.cards`, `run.floor`, etc.
4. MCP server runs `deck_analyzer.get_card_reward_evaluation()`: classifies each offered card, scores it against current deck composition, assigns S/A/B/C/D/F grade.
5. MCP server returns structured grades + reasoning to the Skill.
6. **Claude** integrates the grades with knowledge-base context ("Strength scaling needed because…") and answers in natural language.

The structured grades survive across calls; the natural-language framing is generated fresh each time.

## Why we don't bundle a static dashboard

The original SLAI shipped a web dashboard (~2,800 lines of HTML/CSS/JS). It worked, and it taught us what was useful. The lesson: **proactive visualizations age into noise**. A radar chart that updates every 2 seconds becomes background; a 4-pillar score you can ask about when it matters becomes a tool.

So SLAI doesn't ship a dashboard. The Skill *can* generate one on demand — Claude artifacts give you a fresh radar / cost curve / pile breakdown whenever a question is fundamentally visual. The chart is shaped to the question; the question implies the chart.

## What we depend on upstream

- STS2MCP's `master_deck` exposure on every screen (contributed as a PR; until merged, users may need a fork).
- STS2MCP's `/api/v1/singleplayer` and `/api/v1/multiplayer` endpoints (v0.4.0+).

If STS2MCP makes breaking API changes, we pin to a known version in the MCP server's connection check and surface a clear "unsupported version" error to the user.
