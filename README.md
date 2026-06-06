# SLAI — Slay the Spire 2 Learning with AI

A real-time coaching system for [Slay the Spire 2](https://store.steampowered.com/app/2868840/Slay_the_Spire_2/). Not a bot — a coach. SLAI reads your live game state and answers strategic questions grounded in **[Baalorlord's](https://www.twitch.tv/baalorlord)** teachings: the 4 Pillars of Deckbuilding, card evaluation, pathing philosophy, and character-specific strategies.

You ask the questions, you make every click. SLAI just makes you better at making those clicks.

## What you get

- **SLAI mod** (C#, `mod/`) — a read-only HTTP observer that runs inside Slay the Spire 2 and exposes live game state on `localhost:15526`. Cannot send game inputs by design.
- **`/sts2-coach` Skill** (`skills/sts2-coach/`) — drops into any agent that supports the Anthropic Skills format (built and tested with **Claude Code**; should also work with **Claude Desktop**, **GitHub Copilot CLI**, **Gemini CLI** / **Google Antigravity**, **OpenAI Codex CLI**, and other Skills-compatible agents). Triages questions, shells out to bundled stdlib-only Python scripts for deterministic analysis (4-pillar scoring, card-reward grading S/A/B/C/D/F, mistake detection, pathing context), and generates inline visual artifacts on demand.
- **Knowledge base** (~2,600 lines, `knowledge/`) — encodes Baalorlord's 4 Pillars framework, character strategies for all 5 characters, common mistakes, pathing philosophy, and STS2 mechanics. Built into a small always-resident `knowledge.md` core plus on-demand `knowledge/*.md` sections that the Skill loads as needed (CAG, not RAG).

## Architecture

```
┌──────────────────────┐      HTTP       ┌─────────────────────────────────┐
│  STS2 + SLAI mod     │ ──────────────► │  Any Skills-compatible agent    │
│  (game-side, .dll)   │  localhost:15526│  (Claude Code, Copilot CLI,     │
│                      │                 │   Gemini CLI/Antigravity, etc.) │
│                      │                 │  + sts2-coach Skill             │
│                      │                 │    └─ scripts/ (Python, stdlib) │
└──────────────────────┘                 └─────────────────────────────────┘
```

Two layers, read-only end-to-end. The mod exposes state; the Skill loads cached knowledge and shells out to bundled Python scripts that score the deck, grade card rewards, and detect common mistakes.

## Prerequisites

1. **Slay the Spire 2** on Steam.
2. **Python 3.10+** on `PATH` (the Skill scripts use only the standard library — no `pip install`).
3. **.NET 9 SDK** (only to build the mod from source — if you grab a release binary, skip this).
4. **An agent that can load the Skill.** The Skills format (markdown frontmatter + supporting files + Bash execution) is portable. Primary tested target is [Claude Code](https://docs.anthropic.com/claude/docs/claude-code); also works with Claude Desktop, GitHub Copilot CLI, Gemini CLI / Google Antigravity, OpenAI Codex CLI, and others that load Anthropic-format skills. **You can also run this against a local LLM** (Ollama, llama.cpp, vLLM) if you wrap it with an agent loop that (a) reads `SKILL.md` as system instructions, (b) loads `knowledge.md` on first message, (c) runs the `scripts/*.py` via shell. Capable models (Qwen 2.5 Coder 32B, Llama 3.3 70B, DeepSeek distills) handle the ~52K-token knowledge bundle and the structured-JSON tool-use loop fine; smaller models often won't.

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

### 2. The Skill

Copy `skills/sts2-coach/` into your project's `.claude/skills/` directory (or wherever your Claude client looks for skills). The folder is self-contained — the `scripts/` subfolder contains stdlib-only Python that talks to the mod directly; no `pip install` step.

## Use

1. Launch STS2 with the SLAI mod enabled.
2. Open your Skills-compatible agent (Claude Code, Copilot CLI, Gemini CLI/Antigravity, etc.) in a directory with the Skill installed.
3. Invoke the skill — typically `/sts2-coach` in Claude Code; other agents may vary.
4. Ask anything: *"how am I doing?"*, *"should I take Setup Strike?"*, *"path to the boss?"*

The coach pulls your live state and answers with Baalorlord-grounded reasoning. Specific card advice, deck-aware reward grading, HP-aware pathing — never generic.

See [`examples/example-prompts.md`](examples/example-prompts.md) for more.

## What the Skill knows

| Question type | Script the Skill runs | What it returns |
|---|---|---|
| "How am I doing?" | `get_state.py` + `analyze_deck.py` | Full state + pillar scores |
| Deck health | `analyze_deck.py` | 4-pillar scores, insights, warnings |
| Card reward | `evaluate_card_reward.py` | Per-card S/A/B/C/D/F with reasoning |
| Pathing | `suggest_map_path.py` | HP-aware context, combined with cached pathing knowledge |
| Mistakes | `check_mistakes.py` | Active warnings (bloat, low block, no upgrades, curses, etc.) |
| Mechanic ("what's Doom?") | *None — core, or `knowledge/mechanics.md` for exact numbers* | Knowledge-base lookup |
| Character guide | *None — `knowledge/<character>.md` on demand* | Full strategy for ironclad / silent / defect / necrobinder / regent |
| Connection | `check_connection.py` | Is the mod reachable? |

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
