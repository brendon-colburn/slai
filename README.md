# SLAI — Slay the Spire 2 Learning with AI

A real-time coaching system for [Slay the Spire 2](https://store.steampowered.com/app/2868840/Slay_the_Spire_2/). Not a bot — a coach. SLAI reads your live game state and answers strategic questions grounded in **[Baalorlord's](https://www.twitch.tv/baalorlord)** teachings: the 4 Pillars of Deckbuilding, card evaluation, pathing philosophy, and character-specific strategies.

You ask the questions, you make every click. SLAI just makes you better at making those clicks.

## What you get

- **SLAI mod** (C#, `mod/`) — a read-only HTTP observer that runs inside Slay the Spire 2 and exposes live game state on `localhost:15526`. Cannot send game inputs by design.
- **Coaching MCP server** (Python, `mcp-server/`) — 10 tools that wrap live game data with structured analysis: 4-pillar scoring, card-reward grading (S/A/B/C/D/F), mistake detection, pathing advice.
- **`/sts2-coach` Skill** (`skills/sts2-coach/`) — drops into Claude Code / Claude Desktop. Triages questions to the right MCP tool and generates inline visual artifacts on demand.
- **Knowledge base** (~2,600 lines, `knowledge/`) — encodes Baalorlord's 4 Pillars framework, character strategies for all 5 characters, common mistakes, pathing philosophy, and STS2 mechanics.

## Architecture

```
┌──────────────────────┐      HTTP       ┌──────────────────┐    MCP    ┌──────────────────────┐
│  STS2 + SLAI mod     │ ──────────────► │  SLAI MCP server │ ────────► │  Claude Code /       │
│  (game-side, .dll)   │  localhost:15526│  (Python)        │           │  Claude Desktop      │
│                      │                 │                  │           │  + sts2-coach Skill  │
└──────────────────────┘                 └──────────────────┘           └──────────────────────┘
```

Everything is read-only end-to-end. The mod exposes state; the Python server adds coaching intelligence; the Skill ties it together with natural language.

## Prerequisites

1. **Slay the Spire 2** on Steam.
2. **Python 3.11+** (3.13 recommended).
3. **.NET 9 SDK** (only to build the mod from source — if you grab a release binary, skip this).
4. **Claude Code** or Claude Desktop — for using the Skill.

## Install

### 1. The mod

Either grab a `SLAI.dll` + `SLAI.json` from the [Releases](https://github.com/brendon-colburn/slai/releases) page (once we cut one), or build from source:

```powershell
cd mod
.\build.ps1 -GameDir "C:\Steam\steamapps\common\Slay the Spire 2"
```

Then copy both files into the game's mods directory:

```
<Slay the Spire 2 install>/mods/
  ├── SLAI.dll
  └── SLAI.json     # copy of mod/mod_manifest.json
```

Launch the game once, go to **Settings → Mods**, enable **SLAI**, accept the consent dialog. Verify the server is up:

```
curl http://localhost:15526/
# {"message": "Hello from SLAI v0.1.0", "status": "ok", "role": "read-only-observer", ...}
```

### 2. The Python MCP server

```bash
pip install mcp httpx pydantic
```

Add it to your Claude Code MCP config (`.mcp.json` in any project you want to use SLAI from):

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

### 3. The Skill

Copy `skills/sts2-coach/` into your project's `.claude/skills/` directory, or wherever your Claude client looks for skills.

## Use

1. Launch STS2 with the SLAI mod enabled.
2. Open Claude Code in a directory with SLAI configured.
3. Type `/sts2-coach`.
4. Ask anything: *"how am I doing?"*, *"should I take Setup Strike?"*, *"path to the boss?"*

The coach pulls your live state and answers with Baalorlord-grounded reasoning. Specific card advice, deck-aware reward grading, HP-aware pathing — never generic.

See [`examples/example-prompts.md`](examples/example-prompts.md) for more.

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
| Connection | `check_connection` | Is the mod reachable? |

## Visual breakdowns

Ask for visuals and Claude will generate them as one-shot artifacts using your live data — radar charts, cost curves, type breakdowns, exhaust pile contents. No static dashboard; each visualization is shaped to the question. *"Show me my deck as a cost curve"* → fresh chart from current state.

## Status

Early. Built mid-run as a coaching tool for one player; published in case others want to use or extend it. The knowledge base in particular benefits from corrections — if you spot Baalorlord advice that's misrepresented, open an issue or PR.

## Acknowledgments

- **Baalorlord** ([Twitch](https://www.twitch.tv/baalorlord) / [YouTube](https://www.youtube.com/@baalorlord)) — the strategic teachings encoded in `knowledge/` paraphrase his publicly-available coaching content. SLAI is unaffiliated with Baalorlord; any misrepresentation is ours, not his.
- **[STS2MCP](https://github.com/Gennadiyev/STS2MCP)** by Yikun Ji (Kunologist) — SLAI's mod (`mod/`) is forked from STS2MCP. The state-observation core (StateBuilder, Helpers, Formatting, Compendium, Wiki, Profile) is theirs; SLAI strips the action/multiplayer/Fast-Mode surfaces and adds coaching-specific fields (e.g. `master_deck` exposed on every screen).
- **Mega Crit** — for [Slay the Spire 2](https://store.steampowered.com/app/2868840/Slay_the_Spire_2/).

See [`ATTRIBUTION.md`](ATTRIBUTION.md) for details.

## License

MIT. See [`LICENSE`](LICENSE). The forked mod code retains its original [`mod/LICENSE.STS2MCP`](mod/LICENSE.STS2MCP).
