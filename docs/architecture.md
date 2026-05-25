# Architecture

SLAI is two layers stacked on a dependency:

```
┌──────────────────────────────────────────────────────────┐
│  You (typing in any Skills-compatible agent —            │
│  Claude Code, Copilot CLI, Gemini CLI/Antigravity, etc.) │
│  + sts2-coach Skill loaded                               │
│    ├─ knowledge.md  (cached strategic knowledge)         │
│    └─ scripts/      (Python, stdlib only)                │
└────────────────────────────┬─────────────────────────────┘
                             │ HTTP GET (read-only)
                             │ localhost:15526
                             ▼
┌──────────────────────────────────────────────────────────┐
│  SLAI mod  (C# DLL, in the game's mods/ folder)          │
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
| Skill prose (`SKILL.md`) | Tells Claude how to coach; triages question type → script or cached knowledge | The *style* of coaching |
| Skill scripts (`scripts/`) | Pre-digest raw state into pillar scores, card grades, mistake warnings | Deterministic numeric analysis |
| `knowledge.md` (in skill) | Baalorlord's framework + per-character guides + mechanics + mistakes, cached for the session | Strategy facts |
| `knowledge/` source JSONs | The editable source for `knowledge.md`; rebuilt via `tools/build_knowledge.py` | Strategy facts (source of truth) |
| SLAI mod | Bridges game internals to HTTP | Game state observation |
| The game | Runs your run | The truth |

## Why a `scripts/` folder instead of an MCP server

The original SLAI shipped a Python MCP server that wrapped the mod's HTTP API and exposed ten MCP tools. That made sense in 2024 when Skills couldn't run code. Skills can now run arbitrary scripts via Bash, which makes the MCP layer redundant:

| | Skill + scripts | MCP server |
|---|---|---|
| Install steps | Drop the skill folder in place | `pip install` + edit `.mcp.json` + restart client |
| Processes | Just the mod | Mod + MCP server |
| Tool-list overhead | Each turn the model sees "Bash" once | Each turn the model sees 9–10 MCP tools |
| Iteration | Edit script, re-run | Edit, reload MCP client, hope it re-registers |
| Cross-client portability | Any agent that supports the Anthropic Skills format and can run Bash (Claude Code, Claude Desktop, GitHub Copilot CLI, Gemini CLI / Antigravity, OpenAI Codex CLI, etc.) | Anything that speaks MCP — broader on paper, but every client needs separate config |

For SLAI's actual audience (single player, any Skills-compatible coding agent, live coaching), the Skill-only model wins on every axis except "abstract MCP-ecosystem portability," which nobody was using.

## Why scripts and not pure-LLM analysis

Within the Skill we still keep pillar scoring, card classification, and mistake detection in Python (not in token-space reasoning). Why:

1. **Token efficiency.** Computing pillar scores in Python costs ~0 LLM tokens; doing them in Claude costs hundreds of input tokens per query (read raw state, classify each card, sum, score).
2. **Determinism.** A 4-pillar score should be the same for the same input. A pure-LLM implementation drifts.
3. **Reusability.** The same scripts are testable from a CLI with `--state-file fake.json`, useful for regression tests as the mod's schema evolves.

## Data flow per question

User asks *"should I take Setup Strike?"*:

1. **Skill** receives the question, triages: *card reward → run `scripts/evaluate_card_reward.py`*.
2. The script HTTP-GETs `/api/v1/singleplayer` on `localhost:15526` to fetch live state.
3. The mod returns JSON with `player.master_deck`, `card_rewards`, `run.floor`, etc.
4. `evaluate_card_reward.py` classifies each offered card, scores it against current deck composition, assigns S/A/B/C/D/F grade, and prints structured JSON to stdout.
5. **Claude** parses the JSON, integrates the grades with cached knowledge-base context ("Strength scaling needed because…"), and answers in natural language.

The structured grades survive across calls; the natural-language framing is generated fresh each time.

## Why we don't bundle a static dashboard

The original SLAI shipped a web dashboard (~2,800 lines of HTML/CSS/JS). It worked, and it taught us what was useful. The lesson: **proactive visualizations age into noise**. A radar chart that updates every 2 seconds becomes background; a 4-pillar score you can ask about when it matters becomes a tool.

So SLAI doesn't ship a dashboard. The Skill *can* generate one on demand — Claude artifacts give you a fresh radar / cost curve / pile breakdown whenever a question is fundamentally visual. The chart is shaped to the question; the question implies the chart.

## Knowledge: CAG, not RAG

The strategic knowledge base (~37K tokens, the encoded Baalorlord framework + per-character guides + mechanics + mistakes) is delivered to the Skill via **Cache-Augmented Generation (CAG)**, not Retrieval-Augmented Generation (RAG):

- **Source** of truth lives as 9 JSON files under [`knowledge/`](../knowledge/) (easy to diff, easy to edit per-character).
- A build step ([`tools/build_knowledge.py`](../tools/build_knowledge.py)) renders them into one big markdown bundle at [`skills/sts2-coach/knowledge.md`](../skills/sts2-coach/knowledge.md).
- The Skill instructs the agent to `Read` that bundle on first message of a session.
- Anthropic's prompt cache holds the ~37K tokens for the rest of the session, so the cost is paid once.

**Why CAG over RAG?**

| | CAG | RAG |
|---|---|---|
| Corpus size vs context window | ~37K tokens in a ~200K window — fits easily with room for live state and conversation | Required if corpus ≫ context |
| Cross-cutting reasoning | Agent sees the whole picture at once — can correlate ironclad.json with common_mistakes.json without explicit hops | Agent only sees the chunks the retriever picked |
| Infrastructure | Zero. JSON → markdown → file Read | Vector DB, embeddings, retrieval pipeline |
| Maintenance | Edit JSON, re-run one script | Re-embed every change, re-index, verify retrieval quality |
| Token economics | ~37K cached tokens per session (paid once via prompt caching) | ~3-5K per query, paid every query |

For a corpus this small, RAG would be over-engineering — pay more, get less reasoning, gain nothing. The threshold where RAG starts winning is when the corpus genuinely won't fit in the context window. We're nowhere near that.

## What we depend on upstream

- The SLAI mod's `master_deck` exposure on every screen (a SLAI-specific addition over the original STS2MCP fork).
- The SLAI mod's `/api/v1/singleplayer` and `/api/v1/multiplayer` endpoints (STS2MCP v0.4.0+ surface).

If the mod's HTTP schema changes, we surface a clear connection error from `scripts/check_connection.py` and ask the user to update.
