# Attribution

## Baalorlord

The strategic content encoded in [`knowledge/`](knowledge/) — the 4 Pillars of Deckbuilding, the "Jobs" framework for card evaluation, pathing philosophy, character-specific strategies, common mistakes, and similar — paraphrases publicly available coaching content from **Baalorlord**:

- Twitch: <https://www.twitch.tv/baalorlord>
- YouTube: <https://www.youtube.com/@baalorlord>

SLAI is **unaffiliated** with Baalorlord. He has not reviewed or endorsed this project. Any errors, misrepresentations, or oversimplifications of his teachings are ours alone. If you spot something wrong, open an issue.

We encourage SLAI users to watch his streams and videos directly — this knowledge base is no substitute for his actual coaching.

## STS2MCP

The C# mod in [`mod/`](mod/) is forked from **[STS2MCP](https://github.com/Gennadiyev/STS2MCP)** by **Yikun Ji (Kunologist)**, licensed under MIT. The original license is preserved at [`mod/LICENSE.STS2MCP`](mod/LICENSE.STS2MCP).

**What's preserved from STS2MCP:**
- `McpMod.StateBuilder.cs` — game-state serialization (their core contribution; massive)
- `McpMod.Helpers.cs` — utility methods for safe reflection, node finding, etc.
- `McpMod.Formatting.cs` — markdown formatting of game state
- `McpMod.Compendium.cs` — compendium endpoint (cards/relics/potions discovered)
- `McpMod.Wiki.cs` — fuzzy search of cards/relics
- `McpMod.Profile.cs` — profile slots & active profile
- `McpMod.cs` HTTP server scaffolding

**What's removed:**
- `McpMod.Actions.cs` — all "play the game" endpoints (combat_play_card, rewards_pick_card, shop_purchase, menu_select, etc.)
- `McpMod.MultiplayerActions.cs` / `McpMod.MultiplayerState.cs` — multiplayer surface
- `McpMod.SettingsUI.cs` — Fast Mode UI (automation-related)
- `mcp/` (Python wrapper) — SLAI's Skill talks to the mod directly via stdlib HTTP from `skills/sts2-coach/scripts/`; no separate MCP server
- All POST handlers — SLAI is read-only by design and refuses non-GET requests

**What's added:**
- `player.master_deck` field exposed on every screen (not just during combat) — needed for coaching tools that reason about deck composition between fights
- `player.master_deck_count` companion field
- Self-identification on `/` endpoint as a read-only observer fork

## Mega Crit

[Slay the Spire 2](https://store.steampowered.com/app/2868840/Slay_the_Spire_2/) is © Mega Crit. SLAI is fan-made software that reads game state via its own mod. It does not modify the game's executable, automate gameplay, or interact with the game in any way the player isn't initiating.
