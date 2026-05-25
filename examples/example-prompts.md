# Example Prompts

Once you have SLAI installed and the `sts2-coach` skill loaded in your agent (Claude Code, Copilot CLI, Gemini CLI/Antigravity, OpenAI Codex, or any other Skills-compatible agent), here's what you can ask. The Skill picks the right script automatically — you just talk to it. Examples below show Claude Code's `/skill-name` syntax; invocation may differ slightly per agent.

## Mid-run, asked naturally

- *"How am I doing?"* — pulls full state, summarizes pillars + screen-specific advice
- *"Should I take this card?"* — grades each card reward option S/A/B/C/D/F with reasoning
- *"What about that elite path — worth it?"* — HP-aware pathing call
- *"Should I rest or upgrade?"* — rest-site decision with deck-aware reasoning
- *"What's the worst card in my deck right now?"* — pillar-aware diagnosis
- *"How am I going to do against the boss this act?"* — boss-prep evaluation
- *"What did I pick at floor 3?"* (if you've been logging) — run journal lookup

## Knowledge questions

- *"What does Doom do?"* / *"Explain Sly"* — mechanic lookup
- *"How does the Necrobinder work?"* — character guide
- *"What are the 4 pillars again?"* — framework recap
- *"What are the most common Ironclad mistakes?"* — mistake patterns
- *"Why is 33% block density the target?"* — strategic reasoning

## Visual asks (Claude generates artifacts)

- *"Show me my deck as a cost curve"*
- *"Visualize my 4 pillars"*
- *"Draw me a breakdown of what's in my deck right now"*
- *"What does my exhaust pile look like compared to my draw pile?"*
- *"Pillar comparison vs the average winning Ironclad deck"*

## Multi-step strategic conversations

- *"I'm leaning into a Strength build. Pick my next 5 cards as they appear."* (Skill remembers context within the session)
- *"Help me decide my path through Act 2. I'm at full HP, deck is strong, 200 gold."*
- *"I keep losing to the Act 1 boss. Walk me through what's going wrong."*

## What SLAI won't do

- **Play the game for you.** The Skill is deliberately read-only — the SLAI mod exposes no `combat_play_card` equivalent. STS2MCP's own MCP wrapper exposes those tools if you want them, but they're not in SLAI's surface.
- **Reveal information you shouldn't see.** SLAI only sees what the mod exposes to you. No "what's behind the unknown room" or "what cards will the next reward offer."
- **Replace watching Baalorlord.** The knowledge base is a paraphrase. His streams will always teach more than our JSON files.
