# The 4 Pillars of Deckbuilding

SLAI's coaching is built around Baalorlord's **4 Pillars** framework. Every deck-analysis tool scores your deck on these four axes (0–100) and uses the scores to drive insights, warnings, and reward grading.

## 1. Damage Output

How quickly you can kill things, before they kill you or scale against you.

- **Frontloaded** damage (Bash, Heavy Blade, Pommel Strike): kills enemies in turn 1–2 of hallway fights. Ironclad's starter Strikes are weak frontload.
- **Scaling** damage (Demon Form, Limit Break, Noxious Fumes, Inflame): pays off in longer fights, especially elites and bosses. Slow in hallways.

A good deck balances both. Pure scaling decks die to Act 1 hallways before scaling matters; pure frontload decks fall off vs scaling bosses.

## 2. Cycle Time

How many turns it takes you to see every card in your deck (= deck_size ÷ effective_draw_per_turn).

- Baalorlord targets **20–25 cards**. At 5 draw/turn, that's 4–5 turn cycle.
- Lean decks see their best cards more often. A 30-card deck draws Bash once in 6 turns; a 20-card deck draws it once in 4.
- Draw cards (Acrobatics, Pommel Strike, Wraith Form) accelerate cycle but cost slots.

When in doubt, **skip**. A smaller, more consistent deck beats a bloated deck full of "good" cards.

## 3. Block Density

What % of your **playable** cards (excluding curses/statuses) generate Block.

- **Target: ~33%** (Baalorlord's recommendation). A 21-card deck with 7 block-generating cards is balanced.
- **<20%**: you'll bleed HP every fight. Look for defensive cards or block-enabling powers.
- **>50%**: you'll struggle to kill things before they scale. Common newer-player overcorrection.

Quality matters too. Footwork (3 perm Dex) multiplies every other block card in the deck — one Footwork is worth multiple Defends.

## 4. Upgrade Density

What % of your deck is upgraded (`+1` version).

- Upgrades are usually **bigger power spikes than new cards**. A +1 Bash = 50% more damage on demand; adding a new Strike adds 6 damage to one slot.
- Baalorlord: upgrade > rest when HP > 50%. Pick the upgrade that saves the most HP across the rest of the act.
- Late game, upgrade density should be 50%+. Most boss losses correlate with low upgrade density.

## How SLAI scores

Each pillar gets a 0–100 score:

| Pillar | What pushes the score up |
|---|---|
| Damage Output | Attack density + powers (for scaling) |
| Cycle Time | 20–25 cards = peak; deviation in either direction loses points; draw cards add bonus |
| Block Density | Closeness to 33% is the peak; <10% or >50% scores poorly |
| Upgrade Density | Linear with % upgraded |

The `evaluate_card_reward` tool uses these scores to grade reward options: a card that fills your weakest pillar gets a higher grade than one that piles onto your strongest.

## See also

- [`knowledge/general_strategy.json`](../knowledge/general_strategy.json) — full encoding of the 4 Pillars
- [`knowledge/common_mistakes.json`](../knowledge/common_mistakes.json) — what happens when you ignore the pillars
- [`mcp-server/deck_analyzer.py`](../mcp-server/deck_analyzer.py) — the scoring implementation
