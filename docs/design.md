# Living with Thoreau — Design

Status: the whole story is playable, from Spring 1845 to leaving on September 6, 1847: 21 anchor beats, the 2-beat jail branch, and any side scenes the game master invents, ending with a written epilogue and Thoreau's last word. Conversational, with Gemini as the game master. See [research.md](research.md) for the sources.

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

Guards learned from live play: within a turn, an `adjust_money` that repeats a purchase's price (in either direction) is refused. So is a `spend_time` that repeats the hours `acquire` already counted. The prompt asks the model not to do either, but it sometimes does anyway. Stray markup in narration (`</i>`, `*emphasis*`) is stripped. An outcome passed for a scene that declares none is ignored.

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
- **Hours**: each season has 100 hours of "life". What's left at season end feeds happiness (see below).
- **Alignment** comes from what the tools did. Materials carry value tags (the shanty: frugality and self-reliance; sawn boards: convenience). For free-form actions (`spend_time`, `adjust_money`), the game master supplies the tags. The weights reflect what Thoreau cares about. The running sum, the **drift**, sets his mood: kindred, hopeful, uneasy or estranged.
- **House**: frame 25%, walls and roof 45%, chimney 15%, plaster 15%. Rough shanty boards make it *drafty*.

## Happiness and the rabbit hole

Happiness replaced "spirit". It runs from 0 to 100, starting at 50, and measures Thoreau's well-being: how well he's actually *living*. That's separate from his opinion of your choices (drift), and the two can disagree. A big Sunday dinner at the Emersons' makes him happier while he grumbles about it.

- **Per action:** every tool's value tags move happiness through `rules.HAPPINESS_WEIGHTS`, by at most ±10 per action. The weights: wellbeing 4, nature 3, conscience 3, solitude 2, simplicity 2, sociability 1.5, self-reliance 1, comfort 1, frugality 0.5, status −2.
- **The two tags added for this:**
  - `wellbeing`: rest, a good simple meal, warmth.
  - `superfluity`: anything beyond need.
- **The rabbit hole:** a superfluity gives a small lift (+3, which is the trap) and adds 1 to `wants`. Every season end drains 3 happiness per want, forever.
- **Thoreau's warnings:** the first want obliges Thoreau to warn you passionately ("this is how it starts… a road downhill"). Each later want gets a shorter, more exasperated warning. He speaks even if the model would rather he stayed silent; an authored line stands in.
- **One want per turn:** the model often tags one purchase on two or three tools (the time spent browsing, paying, the item itself), so a turn adds at most one want.
- **Season end:** free hours left give +1 per 5 hours (max +20), and overwork costs 1 per 2 hours over (max −30). A season with no scenes in it yet passes without changing anything.
- **On screen:** a meter in the header, colored by level, with "· N wants" once you have any.

## Branching: beat outcomes

A beat can declare `outcomes: {name: [follow-up beat ids]}`. The game master must name one in `end_beat(outcome=…)`; an unknown or missing outcome is refused. The director then queues the follow-up beats ahead of the next anchor. Beats reached only this way are marked `branch`.

## The night in jail (July 1846)

The first branch, played live end to end:
1. **The Shoemaker's Errand** (an anchor, in Concord village). Sam Staples asks for $6.00 of back poll tax (a game price).
   - `paid` (you pay, or let Staples pay) → the story goes on.
   - `refused` → the next two beats.
2. **A Night in the Concord Jail.** The cellmate accused of burning a barn, the town heard through the grated window, and Thoreau at his most alive. Partway through, Staples brings news that a veiled woman has paid, but he has his boots off and won't open up until morning.
3. **Huckleberries.** Released at breakfast and furious that someone paid, you collect the mended shoe and lead the huckleberry party up the hill.

The seasons between the bean-field and the errand (Autumn 1845 to Spring 1846) aren't written yet, so for now the story jumps straight there.

## The story's backbone (21 anchors)

| Season | Scenes |
|---|---|
| Spring 1845 | An Axe and Some Pines · Collins's Shanty · A Hole in the Hillside · Into Concord · Raising the Frame · Walls and a Roof |
| Summer 1845 | The Fourth of July · The Bean-Field (outcomes: big_field / small_patch / no_field) |
| Autumn 1845 | The Bean Harvest (sells what was planted) · Fire and Plaster (requires the chimney) |
| Winter 1845–46 | The Pond Freezes (fuel; a drafty house needs more) · The Ice-Cutters (and sounding the "bottomless" pond) · Former Inhabitants |
| Spring 1846 | The Thaw · A Traveler Going North (outcomes: helped / turned_away) |
| Summer 1846 | The Woodchopper (Alek Therien) · The Shoemaker's Errand → jail branch |
| Autumn 1846 | Baker Farm (John Field) |
| Winter 1846–47 | The Second Winter (the stove, old friends) |
| 1847 | A Smaller Field · Leaving the Woods (outcomes: left / stayed) |

Outcomes are remembered in `state.outcomes`, and later scenes see them as `earlier_choices` (the harvest knows what was planted). Two scenes involve real people who were enslaved or escaping slavery: Former Inhabitants (Cato Ingraham, Zilpha, Brister and Fenda Freeman) and A Traveler Going North. Both instruct the model to portray them with dignity, as people with their own voices. The traveler's name is invented, because Thoreau never recorded who he helped. The game master also gets a list of **side-scene ideas** from Thoreau's real life: the ant war, the loon, the woodchuck, the tame mouse, night fishing, Channing and Alcott, Sunday dinner at the Emersons', the melon party, the spark in the bed, Mount Katahdin, and the "woods-burner" gossip.

## The ending

When the last anchor is done, the server sends `ending` with the **final accounts**:
- scenes lived;
- what you spent on the house against Thoreau's $28.12½;
- how much of the house got built, and how drafty it is;
- hours of life spent, and money left;
- happiness and wants;
- how Thoreau feels about you;
- the choices you made.

Then two streamed texts follow: the narrator's **epilogue**, written from the whole history, and **Thoreau's last word**, shaped by your happiness, wants and his mood. Both are written once and kept, so a reload shows the same ending.

## Approvals

Each purchase asks Pay / Don't. **Pay for all of it** also approves any further purchases in the same turn, so a shopping trip you've already described doesn't need five clicks. Each one is still logged in the debug panel.

## Testing aids

The debug panel has **New game at** [scene] → **Start**. It begins a fresh game just before any anchor, as if the earlier scenes went Thoreau's way. That includes ledger entries, so a test ending's accounts are sensible (`director.fast_forward`; `POST /api/game/new {"start": id}`; `GET /api/game/beats`).

## Next up

- Play the whole story through and tune the pacing: how many turns each scene takes, and whether 21 to 23 scenes feels right.
- Check that the "paid" or "refused" outcome matches what happened (for example, "paid" requires the $6.00 to have left your money).
- Give the director its own nudges for side scenes (low happiness, an unmet friend, a big drift), alongside the game master's proposals.
- Persist sessions beyond memory, so a backend restart doesn't end a game in progress. This matters more now that a game is 20+ scenes.
- The journal page (nice-to-have), and visual direction B as an alternate skin.
