# Living with Thoreau — Design

Status: first playable slice, Spring 1845 → Summer 1845: 8 anchor beats, plus any side scenes the game master invents. Conversational, with Gemini as the game master. See [research.md](research.md) for the sources.

## Decisions so far

| Topic | Decision |
|---|---|
| Premise | You inhabit Thoreau's body. Thoreau is a second, inner voice who can talk but can't act. |
| Interaction | **Text first.** You type what you do or say. An LLM game master narrates, plays everyone else, and changes the world through tools. Buttons survive only as **suggested chips** that the game master chooses to show. |
| Story | A fixed **backbone of beats** (situation, goal, Thoreau's stance, what's on offer). Within a beat the game master decides how things go, and the beat ends when its goal is met. It may also invent **side scenes** between beats (2 per season at most). |
| Creativity | Full creative freedom in narration: new people, events, places, side stories. Anything that should *count* (money, hours, materials, items, the house, location) goes through a tool, and the rules decide. |
| Voices | **Game master/narrator**: second person, plays every other character. **Thoreau**: passionate, funny, stubborn, defensive about his contradictions. He speaks modern English. His ideas come from *Walden*, though he says plenty the book doesn't. After each turn he decides whether to speak, and he always answers when you talk to him. |
| Talking to Thoreau | The game master works it out from your wording (`pass_to_thoreau`). A misread is accepted. |
| Pacing | Season by season over 10 seasons (Spring 1845 → Summer 1847), **20 to 80 scenes**. |
| Visuals | **Direction C, living atmosphere.** Direction B (pencil journal) may come later as a skin. |
| House | The **lighter version**: real materials with real prices, tracked against Thoreau's $28.12½. A fuller puzzle may come later. |
| Widgets | Suggested chips, ledger, material card, house blueprint, trip planner. The journal page is a nice-to-have. |
| Model | Gemini on Vertex. Real play needs it. The tests script the model. |

## How a turn works

1. `POST /{sid}/next` opens the next beat. The game master gets the beat brief in its system prompt and sets the scene. Then Thoreau says what he wants here.
2. `POST /{sid}/act` with one of three actions:
   - `say` (free text);
   - `trip` (from the trip planner);
   - `approve` (yes or no to a pending purchase).
3. **The game master loop** works like the reference's agent loop. Each round streams narration and collects tool calls. The server runs the tools and sends back the results, and this repeats until the model has nothing left to do (at most 10 tool calls a turn). A tool that spends money pauses the loop with an approval card, and the loop resumes where it stopped.
4. **Thoreau** comes next. His alignment for the turn (−2..+2) is computed by the server from the value tags of the tools that ran. If you spoke to him, he answers. If the scene just opened, or he feels strongly, he speaks. Otherwise he may reply `(silent)`, which is swallowed.
5. When the game master calls `end_beat` and the beat's checkable requirements hold (timber, the frame, the shell), the scene closes with a summary line in the history, and you continue.

The conversation with the game master is kept on the server for the length of a scene, then summarized into the history.

### The game master's tools

`look_around`, `move`, `acquire` (house materials, real prices), `build`, `spend_time`, `adjust_money` (anything else, ±$10 a call), `day_labor`, `gain_item` / `lose_item`, `show_widget`, `pass_to_thoreau`, `propose_side_scene`, `end_beat`.

Guards learned from live play: within a turn, an `adjust_money` that repeats a purchase's price (in either direction) is refused. So is a `spend_time` that repeats the hours `acquire` already counted. The prompt asks the model not to do either, but it sometimes does anyway.

### Debug panel

The `{ }` button in the header, or the `` ` `` key when you're not typing, opens a panel docked on the right. It groups everything by turn:
- what you did;
- each game-master round (time taken, tool calls, and optionally the full system prompt it saw);
- each tool call with its arguments, status (ok / error / refused / awaiting approval / declined), value score and what the rules answered;
- how Thoreau's tone was worked out, and whether he chose silence;
- scenes opening and closing.

The **State** tab shows the raw snapshot. The server sends these as `debug` SSE events (`gm._debug`).

## The numbers

- **Money** is kept in mills (1/1000 of a dollar), so half-cents are exact. You start with $20.00.
- **Hours**: each season has 100 hours of "life". At the end of a season, every 25 unspent hours becomes +1 spirit, and overwork costs spirit.
- **Alignment** comes from what the tools did. Materials carry value tags (the shanty: frugality and self-reliance; sawn boards: convenience). For free-form actions (`spend_time`, `adjust_money`), the game master supplies the tags. The weights reflect what Thoreau cares about. The running sum, the **drift**, sets his mood: kindred, hopeful, uneasy or estranged.
- **House**: frame 25%, walls and roof 45%, chimney 15%, plaster 15%. Rough shanty boards make it *drafty*.

## Under discussion (2026-11-05)

**Economy:** stays at money, hours and the house. No food, fuel or clothing resources.

**Happiness bar** (proposed; it would replace "spirit"): Thoreau's well-being, 0–100, which is separate from his *opinion* of you (drift).
- Rises with what he'd call deliberate living: time in nature, solitude, simple good food, rest, real company in moderation, acting on conscience, free hours left in a season.
- Falls with overwork, debt, the village gauntlet, and **superfluities**, meaning things beyond need.
- **The rabbit hole:** a superfluity feels good for a moment (+) but adds 1 to `wants`. Every season end then drains happiness by `wants`, so each unneeded thing keeps costing. This is *Walden*'s "positive hindrances" idea, played as a mechanic.
- Two new value tags: `wellbeing` and `superfluity`. Happiness is computed by the server from tool tags, like alignment, with its own weights.
- Drift and happiness can disagree. A big Sunday dinner at the Emersons' makes him happier, but he grumbles about it.

**The jail night** (proposed) is a three-beat branch in July 1846:
1. **The Shoemaker's Errand.** In Concord, Sam Staples stops you over unpaid poll tax. You can pay, refuse, argue, or let Staples pay for you. `end_beat` takes an *outcome*, and "refused" queues the next two beats.
2. **A Night in the Concord Jail.** A cellmate accused of burning a barn, the town heard through the window, and Thoreau's ideas on conscience coming alive. That evening someone (a veiled woman) pays your tax, and Staples won't let you out until morning.
3. **Huckleberries.** Released and furious that someone paid, you finish the errand and lead a huckleberry party up the hill. The town looks different now.

This needs **beat outcomes**: a beat declares its possible outcomes, `end_beat(outcome=...)` picks one, and the director queues that outcome's follow-up beats. The poll tax amount would be a game price.

## Next up

- Content for Autumn 1845 → Summer 1847, about 12 more anchors: chimney and plaster before the frost, the first harvest, the woodchopper, winter fuel and the ice-cutters, the jail night (July 1846), John Field at Baker Farm, the second smaller field, and leaving on Sept 6, 1847.
- Give the director its own nudges for side scenes (low fuel, an unmet visitor, a big drift), alongside the game master's proposals.
- An ending that reflects how you lived: your ledger against Thoreau's, his last word on you.
- Persist sessions beyond memory, and add the journal page.
