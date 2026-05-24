# Building the SLAI Mod

The C# mod in [`mod/`](../mod/) is what runs inside the game and exposes the HTTP API on `localhost:15526`. This doc covers building it from source.

## Prerequisites

1. **Windows** (Linux/macOS builds technically work but aren't tested — see csproj for hints).
2. **.NET 9 SDK** — [download](https://dotnet.microsoft.com/download/dotnet/9.0).
3. **Slay the Spire 2** installed locally — the mod links against `sts2.dll`, `GodotSharp.dll`, and `0Harmony.dll` from the game's install directory.

Check your .NET version:

```powershell
dotnet --version  # should be 9.0.x or later
```

## Build

```powershell
cd mod
.\build.ps1 -GameDir "C:\Steam\steamapps\common\Slay the Spire 2"
```

The `-GameDir` argument is the Slay the Spire 2 install root (the folder that contains `SlayTheSpire2.exe`). On a default Steam install with the library on C:, that's usually `C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2`. On a non-default library, find it via Steam → right-click STS2 → Properties → Installed Files → Browse.

You can also set `$env:STS2_GAME_DIR` once in your PowerShell profile and run `.\build.ps1` with no args.

Build output lands at `mod/out/SLAI/SLAI.dll`.

## Install

Copy two files into the game's `mods/` directory (create it if it doesn't exist):

```
<game_install>/mods/
  ├── SLAI.dll               # from mod/out/SLAI/
  └── SLAI.json              # rename mod/mod_manifest.json
```

Launch Slay the Spire 2. Go to **Settings → Mods** and enable **SLAI**. On first launch you'll see a one-time consent dialog about loading the mod; accept it.

## Verify

With the game running, check the HTTP endpoint:

```bash
curl http://localhost:15526/
```

Expected:

```json
{
  "message": "Hello from SLAI v0.1.0",
  "status": "ok",
  "role": "read-only-observer",
  "upstream": "forked from STS2MCP by Yikun Ji (Kunologist)"
}
```

## What gets built

| File | What it is |
|---|---|
| `McpMod.cs` | HTTP server scaffolding; routes GET requests to handlers. Refuses POST. |
| `McpMod.StateBuilder.cs` | Reads game state via reflection on Player / RunState / combat objects and serializes to JSON. The bulk of the work. |
| `McpMod.Helpers.cs` | Utility methods: safe reflection, node finding, UI visibility checks, etc. |
| `McpMod.Formatting.cs` | Markdown rendering of game state (for `?format=markdown` queries). |
| `McpMod.Compendium.cs` | `/api/v1/compendium` endpoint. |
| `McpMod.Wiki.cs` | `/api/v1/wiki?query=...` fuzzy search. |
| `McpMod.Profile.cs` | `/api/v1/profile` and `/api/v1/profiles` endpoints (read-only). |

## Coexistence with STS2MCP

SLAI listens on the same port as STS2MCP (15526). You can't run both at once. If you previously had STS2MCP installed:

1. Disable STS2MCP in **Settings → Mods**, OR
2. Delete `STS2_MCP.dll` and `STS2_MCP.json` from `<game>/mods/`.

If you want them to coexist (for example, you also use STS2MCP for AI agents that play the game), edit `mod/McpMod.cs` to change `DefaultPort` to e.g. 15527 and rebuild. Then update the Python MCP server's [`game_client.py`](../mcp-server/game_client.py) `DEFAULT_PORT` to match.

## Troubleshooting

**"Could not find sts2.dll"** — `-GameDir` is wrong. Verify the path exists and contains `data_sts2_windows_x86_64/sts2.dll`.

**"`dotnet` not found"** — install [.NET 9 SDK](https://dotnet.microsoft.com/download/dotnet/9.0) and restart your shell.

**Mod doesn't show up in-game** — confirm `SLAI.dll` and `SLAI.json` are both in the `mods/` folder, both have content, and the JSON parses (open it in a text editor).

**HTTP server doesn't start (no port 15526)** — check the game's stdout (Godot's `--debug` flag, or look in Steam's logs). Common causes: another process is bound to 15526, or the mod failed to load. The mod logs all errors with the `[SLAI]` prefix.
