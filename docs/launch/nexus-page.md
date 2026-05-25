# Nexus Mods page — SLAI

Copy/paste ready for the [Nexus STS2 mod listing](https://www.nexusmods.com/games/slaythespire2/mods). Markdown renders cleanly in Nexus's editor.

---

# SLAI — AI Coach for Slay the Spire 2

**SLAI is a real-time coaching tool, not a gameplay mod.** It reads your live game state and answers strategic questions in plain language using Baalorlord's framework. It is **read-only by design** — it cannot play cards, take actions, or interact with the game in any way you aren't initiating.

## What it does

While you're in a run, you can ask things like:

- *"How's my deck looking?"*
- *"Should I take Setup Strike or Pommel Strike?"*
- *"Worth fighting this elite at 64% HP?"*
- *"What does this enchantment do?"*
- *"How do I beat the Queen with this deck?"*

…and get answers grounded in your *actual* deck composition, HP, gold, screen state, and the boss the act is rolling. Card grades (S/A/B/C/D/F) come from deterministic deck-pillar math, not vibes.

## ⚠️ Important — Requirements

SLAI is **two pieces** and you need both:

1. **This mod** (`SLAI.dll` + `SLAI.json`) — runs inside STS2, exposes your game state on `localhost:15526`. **The mod alone does nothing visible.** It's a data source for a coaching client.
2. **The SLAI coach Skill** for any Skills-compatible AI coding agent — [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) (primary tested target), Claude Desktop, GitHub Copilot CLI, Gemini CLI / Google Antigravity, OpenAI Codex CLI, and other agents that load Anthropic-format skills. Download `sts2-coach-skill.zip` from the [GitHub releases page](https://github.com/brendon-colburn/slai/releases/latest).

**If you don't use a Skills-compatible AI agent, this mod will not be useful to you on its own.** (Devs: the HTTP API is exposed on `localhost:15526` if you want to build a different client — it's all JSON, fully documented in the source.)

## Install

1. Download `SLAI.dll` and `SLAI.json` (or `slai-mod-v0.1.0.zip` for both at once)
2. Copy both files into `<Slay the Spire 2 install>/mods/` (create the folder if it doesn't exist)
3. Launch the game → Settings → Mods → enable **SLAI** → accept the consent dialog
4. Verify in any browser or terminal: `http://localhost:15526/` should return a "Hello from SLAI" message
5. Install the [Skill from GitHub](https://github.com/brendon-colburn/slai/releases/latest), drop it in your agent's skills folder, invoke `sts2-coach`

Full setup walkthrough: <https://github.com/brendon-colburn/slai>

## Compatibility

- **Slay the Spire 2 patch 0.105.0+** (knowledge base reflects the current Aeonglass meta, not the removed Doormaker)
- **Windows tested**; macOS/Linux likely work but unverified
- **Single-player only** — multiplayer is not supported
- **Conflicts with STS2MCP** — both use port 15526. Disable one or change SLAI's port in its `SLAI.conf` (auto-generated on first launch)

## Credits

- **Baalorlord** ([Twitch](https://www.twitch.tv/baalorlord) / [YouTube](https://www.youtube.com/@baalorlord)) — the strategic framework SLAI's knowledge base encodes paraphrases his publicly available coaching content. SLAI is unaffiliated with Baalorlord; any misrepresentation is mine, not his. Please watch his streams — they will teach you more than any tool.
- **Yikun Ji (Kunologist)** — SLAI's mod is forked from [STS2MCP](https://github.com/Gennadiyev/STS2MCP), an MIT-licensed read-only game-state exposure mod. The state-observation core is theirs; I stripped the action endpoints and added coaching-specific fields.
- **Mega Crit** — for the game itself.

## Source / Issues

MIT licensed, source on [GitHub](https://github.com/brendon-colburn/slai). Bug reports and feature requests via [GitHub issues](https://github.com/brendon-colburn/slai/issues) (preferred) or Nexus comments.

## Changelog

**v0.1.0** — first public release. Knowledge base current to patch 0.105.0 (Aeonglass Act 3 boss). 15 source knowledge files covering 4 Pillars, character strategies for Ironclad / Silent / Defect / Necrobinder / Regent, enchantments, Ancient blessings, A6+ Inflation economy, elite + boss strategies, combat micro-decisions, common mistakes.
