# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session defaults

**On every session start in this repo, activate `caveman ultra` mode.** Invoke the `caveman` skill with `ultra` intensity before responding to the first user message. Keep that mode active for the rest of the session unless the user explicitly turns it off.

## What this repo is

SLAI = Slay the Spire 2 Learning with AI. Two cooperating, **read-only** layers:

1. **The mod** (`mod/`, C# / .NET 9) — runs inside Slay the Spire 2 (Godot runtime), exposes live game state as JSON over HTTP on `localhost:15526`. Forked from STS2MCP; action / multiplayer / Fast-Mode surfaces are stripped on purpose.
2. **The Skill** (`skills/sts2-coach/`) — drops into Claude Code / Claude Desktop. Contains a cached knowledge bundle (`knowledge.md`) and stdlib-only Python scripts that talk to the mod.

The Skill is the end-user product; the mod is its data source. Architecture diagram in `docs/architecture.md`.

## Common commands

```powershell
# Build the mod (Windows; .NET 9 SDK + game install required)
cd mod
.\build.ps1 -GameDir "C:\Steam\steamapps\common\Slay the Spire 2"
# Or set $env:STS2_GAME_DIR once and run `.\build.ps1` with no args.
# Output: mod/out/SLAI/SLAI.dll  — copy to <game>/mods/ alongside SLAI.json (= mod_manifest.json).

# Rebuild the Skill's knowledge bundle after editing any knowledge/*.json
python tools/build_knowledge.py
# Renders the core framework into skills/sts2-coach/knowledge.md (~17K tokens) and
# the remaining sections (characters, mechanics, boss/elite, economy, enchantments,
# ancients) into skills/sts2-coach/knowledge/*.md as on-demand reads.

# Smoke-test the mod is live
curl http://localhost:15526/

# Run a Skill script directly (e.g. for debugging analysis logic)
python skills/sts2-coach/scripts/analyze_deck.py            # live mod
python skills/sts2-coach/scripts/analyze_deck.py --state-file fixtures/foo.json  # replay
python skills/sts2-coach/scripts/<name>.py --help           # always works
```

No test suite, no linter, no CI. Scripts are stdlib-only — no `pip install` step anywhere. The mod has no separate test target; verify by launching STS2 with the DLL installed.

## Architecture notes that aren't obvious from file listing

**Knowledge is CAG, not RAG.** The JSON files under `knowledge/` are the *source of truth*; `tools/build_knowledge.py` renders them into a small always-resident **core** bundle (`skills/sts2-coach/knowledge.md`, ~17K tokens: framework, pathing, combat micro, common mistakes) plus **on-demand** sections (`skills/sts2-coach/knowledge/*.md`: per-character guides, mechanics, boss/elite tactics, economy, enchantments, ancients). The core carries an index of the on-demand sections. The Skill `Read`s the core on the first turn and pulls on-demand sections only when a question needs them; Anthropic's prompt cache keeps whatever's loaded for the rest of the session. **Never edit `knowledge.md` or `knowledge/*.md` by hand** — your edits will be wiped the next time the bundle is rebuilt. Edit the JSONs, then run `python tools/build_knowledge.py`.

**The C# mod is split into partial classes by responsibility.** All `mod/McpMod.*.cs` files extend `partial class McpMod`:
- `McpMod.cs` — HTTP scaffolding, request routing, port config (refuses POST by design).
- `McpMod.StateBuilder.cs` — reflection-based read of Player / RunState / combat → JSON. The bulk of the work.
- `McpMod.Helpers.cs` — safe reflection, node finding, UI visibility.
- `McpMod.Formatting.cs` — markdown rendering for `?format=markdown`.
- `McpMod.Compendium.cs`, `McpMod.Wiki.cs`, `McpMod.Profile.cs` — endpoints of the same name.

The mod's defining SLAI-specific change vs upstream STS2MCP is that `master_deck` is exposed on every screen (not just combat).

**Skill scripts share `_lib.py`.** `skills/sts2-coach/scripts/_lib.py` holds the HTTP client, the deck analyzer, and the card-grading logic. Pillar math is a line-for-line port of the now-removed MCP server's `deck_analyzer.py` — pillar scores are identical to historical scores. Treat `_lib.py` as a black box unless you're intentionally changing the analysis math; the SKILL.md tells the model not to read it.

**Why no MCP server?** There used to be one. It was removed (commit `b87effa`) once Skills could run Bash. The folder layout still mirrors the old separation (Skill = orchestration prose; `scripts/` = analyzers) but everything runs in-process to the Skill now.

## Constraints worth knowing

- **Read-only by design.** The mod cannot send game inputs. Don't add endpoints that mutate state — that's the whole product premise.
- **Port 15526 conflicts with STS2MCP.** They can't run simultaneously. If a user has both installed, disable one or change `DefaultPort` in `mod/McpMod.cs` and pass `--port` to the scripts.
- **Mod links against game DLLs.** `sts2.dll`, `GodotSharp.dll`, `0Harmony.dll` are referenced from the local game install (resolved per-OS in `SLAI.csproj`); none are vendored. `dotnet build` will fail without a real STS2 install path.
- **Windows is the only tested build target** for the mod. The csproj has macOS/Linux paths but they aren't exercised.

## Where to look first when something breaks

- Skill can't reach the mod → `skills/sts2-coach/scripts/check_connection.py` and the mod's `[SLAI]`-prefixed stdout in the game console.
- Pillar scores look wrong → `skills/sts2-coach/scripts/_lib.py` (analyzer + grader).
- Knowledge content wrong → edit the JSON under `knowledge/`, rerun `python tools/build_knowledge.py`. Never patch `skills/sts2-coach/knowledge.md` directly.
- Mod build fails on "Could not find sts2.dll" → `-GameDir` is wrong; see `docs/mod-build.md`.
