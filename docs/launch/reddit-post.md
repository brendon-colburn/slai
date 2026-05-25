# r/slaythespire2 announcement post

Copy/paste ready. Tested for the subreddit's typical tone (technical, transparent, respectful of pro players' content).

---

**Title:** *I built an AI coach for STS2 — reads your live game state, gives Baalor-style advice. Read-only, doesn't play for you.*

---

Hey all — I've been playing too much STS2 and building this in parallel. Hopefully someone else gets use out of it.

**TL;DR:** Mod for STS2 + a Skill that drops into your AI agent (Claude Code, Copilot CLI, Gemini CLI / Antigravity, OpenAI Codex, etc — anything supporting the Anthropic Skills format, including DIY setups against local Ollama/llama.cpp models if you wrap them with a basic agent loop). You're in a run, you ask things like "should I take Setup Strike?" or "is this Desa Millipede worth fighting at 64%?", and you get specific answers grounded in your actual deck and HP. Card grades come from a deterministic 4-Pillar math implementation, not vibes.

**It does not play the game for you.** The mod's HTTP API is read-only — there's literally no endpoint to play a card. I only built the observation side. Every click is still yours.

**What it knows:**

- The 4 Pillars framework (Damage / Cycle / Block density / Upgrade density), grounded in Baalorlord's published content
- Per-character guides for all 5 (Ironclad / Silent / Defect / Necrobinder / Regent) with current STS2-specific reworks
- Current Act 3 boss meta — Aeonglass + Queen + Test Subject (it knows Doormaker is gone)
- A6+ Inflation economy implications, shop discipline, hard pool vs easy pool, Bonfires > Elites math
- Enchantments, Ancient blessings, the Anger exploit, the Pillage+Hellraiser+Perfected Strike combo, the Pale Blue Dot infinite, all the current grandmaster-level stuff

**Example coaching exchange** (real, from one of my runs):

> Me: *"what should I take here?"*
>
> Coach: *"Take Setup Strike. Your deck is 6 Strikes / 4 Defends — Setup Strike's +2 Strength on play makes every Strike hit harder, and you have no scaling yet. Pommel Strike is fine but redundant. Skip Inflame at 11/30 cycle time — dead draw in 3-turn fights and Act 1 elites die before scaling matters. Flip this if you already grabbed any +Strength source — then take the draw card instead."*

**Honest limits:**

- It can't see what's behind unknown doors or predict draw order (the mod exposes pile *contents* not *order*; the skill explicitly refuses "you'll draw Bash+ next" claims)
- It uses an AI agent. If you don't run Claude Code / Copilot CLI / Gemini CLI / etc, the mod still works as a data source but you won't get the coaching experience.
- Early access game — specific numbers drift with patches. Knowledge base needs updates over time. Currently synced to **0.105.0**.
- **This is not Baalorlord's tool.** I just paraphrase his publicly available teachings as a knowledge base. Watch his streams — they'll teach you more than any tool.

**Get it:**

- Mod: [Nexus link once it's up] or [GitHub release](https://github.com/brendon-colburn/slai/releases/latest)
- Skill (for your AI agent): same GitHub release page (`sts2-coach-skill.zip`)
- Source / docs / how it works: <https://github.com/brendon-colburn/slai>

MIT license, fork-friendly. Bug reports and ideas welcome.

Happy to answer questions about how it works, the design tradeoffs, or why a particular thing it told you was wrong.
