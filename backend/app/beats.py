"""The story's backbone: beats.

A beat is a situation, not a menu. It tells the game master where the
player is, what's true, what the scene is for (its goal), and what Thoreau
wants here; the game master runs the scene however the player plays it,
and calls `end_beat` once the goal is met. Where a goal can be checked
(the frame is raised), the server checks it before letting the beat end.

The game master can also invent side scenes between beats; those become
beats too (see `side_beat`).
"""

from pydantic import BaseModel, Field


class Beat(BaseModel):
    id: str
    season_index: int
    title: str
    when: str | None = None  # None: the season's label
    location: str  # a world.LOCATIONS id, or a free-form place for side scenes
    situation: list[str]
    goal: str
    thoreau_stance: str
    people: list[str] = Field(default_factory=list)  # who's around
    offers: list[str] = Field(default_factory=list)  # "material:method" for where="scene" methods
    requires_items: list[str] = Field(default_factory=list)  # checked before end_beat
    requires_built: list[str] = Field(default_factory=list)
    side: bool = False


BEATS: dict[str, Beat] = {
    b.id: b
    for b in [
        Beat(
            id="axe",
            season_index=0,
            title="An Axe and Some Pines",
            when="Late March 1845",
            location="woods",
            situation=[
                "Late March, 1845. The player stands in the woods above Walden Pond, on a lot Emerson owns and has said they may use.",
                "The pond is still mostly ice. Tall white pines crowd the hillside where they mean to build.",
                "They need a frame of hewn pine timbers, and they don't own an axe.",
            ],
            goal="The player gets the frame timbers cut and hewn, by whatever means. When they have them, call gain_item('timber').",
            thoreau_stance="He wants to borrow an axe from a neighbor and return it sharper than he got it. Buying one, or paying someone, offends him.",
            people=["Neighbors in Concord who might lend an axe", "Emerson, who owns the land"],
            requires_items=["timber"],
        ),
        Beat(
            id="shanty",
            season_index=0,
            title="Collins's Shanty",
            when="Mid-April 1845",
            location="railroad",
            situation=[
                "Mid-April. Down by the Fitchburg Railroad, James Collins, an Irish railroad worker, is moving on and will sell his shanty for $4.25.",
                "It's a dark little place with a dirt floor, but the boards are sound under the weathering, and they're full of old nails.",
                "Taken apart, the boards could be bleached and straightened in the sun.",
            ],
            goal="The player deals with Collins's offer: buys the shanty (and perhaps salvages its nails) or turns it down.",
            thoreau_stance="He wants the shanty, and to pull and straighten every nail himself. Buying new boards in the village is a waste of life to him.",
            people=["James Collins", "Collins's wife, who is at home"],
            offers=["boards:shanty", "nails:salvage"],
        ),
        Beat(
            id="cellar",
            season_index=0,
            title="A Hole in the Hillside",
            when="Late April 1845",
            location="cabin",
            situation=[
                "Late April. The player has chosen a spot: a slope a short walk up from the shore, where a woodchuck once dug its burrow.",
                "A cellar would keep potatoes from freezing in winter. The ground is soft sand.",
            ],
            goal="The player decides about a cellar and digs it, or decides not to.",
            thoreau_stance="Six feet square, seven deep, about two hours' work. He scorns a big cellar as a palace for potatoes.",
        ),
        Beat(
            id="village_run",
            season_index=0,
            title="Into Concord",
            location="cabin",
            situation=[
                "Concord village is two miles off, by the road or along the railroad tracks.",
                "The general store sells nails, hinges, hair for plaster, laths and iron. The yard has shingles, second-hand windows, old bricks, lime and sawn boards.",
                "A farmer will usually pay about a dollar for a day's labor.",
            ],
            goal=(
                "The player gets what the house still needs from Concord, or decides to make do. Offer the trip_planner "
                "widget early, though they may also walk there and shop in person."
            ),
            thoreau_stance="Go once, with a list. The village is a gauntlet of shops and gossip, and every trip costs half a day.",
            people=["The storekeeper", "Idlers on the store porch", "Farmers looking for a day's help"],
        ),
        Beat(
            id="raising",
            season_index=0,
            title="Raising the Frame",
            when="Early May 1845",
            location="cabin",
            situation=[
                "Early May. The hewn timbers lie in the grass, mortised and ready to fit together.",
                "A frame this size is heavy work for one person. A few acquaintances have said they'd lend a hand.",
                "In Concord, a raising is as much a social occasion as a job.",
            ],
            goal="The frame gets raised. Call build('frame') when it is.",
            thoreau_stance="Ask a few acquaintances, less from need than as a fine excuse to be neighborly. He's no hermit, whatever the village says.",
            people=["Acquaintances from Concord (you may invent them, or use Emerson, Alcott, Ellery Channing)"],
            requires_built=["frame"],
        ),
        Beat(
            id="roofing",
            season_index=0,
            title="Walls and a Roof",
            when="Late May 1845",
            location="cabin",
            situation=[
                "The frame stands on the hillside, open to the sky.",
                "Closing it in takes boards for the walls, nails, shingles for the roof, a pair of windows, and hinges and a latch for the door.",
                "The player would like a roof overhead by the Fourth of July.",
            ],
            goal=(
                "The house gets closed in: call build('shell') once the materials are in hand. If something's missing, "
                "the player will have to get it (walk to the village, or use the trip_planner)."
            ),
            thoreau_stance="Board it, shingle it, and move in. A house doesn't need to be finished to be lived in; the chimney can wait for the frost.",
            requires_built=["shell"],
        ),
        Beat(
            id="move_in",
            season_index=1,
            title="The Fourth of July",
            when="July 4, 1845",
            location="cabin",
            situation=[
                "The Fourth of July, 1845. The house is boarded and roofed, ten feet by fifteen, with no chimney or plaster yet.",
                "Through the open door the pond lies flat and bright down the hill.",
                "Off in the village, people are celebrating Independence Day.",
            ],
            goal="The player spends their first evening and night in the new house, however they choose.",
            thoreau_stance="Independence Day, of course! Don't work tonight. Sit in the doorway and listen to the whippoorwills. That's the whole point.",
        ),
        Beat(
            id="beans",
            season_index=1,
            title="The Bean-Field",
            when="Summer 1845",
            location="bean_field",
            situation=[
                "Summer. About two and a half acres of dry, sandy land lie open near the house, cheap and never manured.",
                "Plowing, harrowing and furrowing that much with a hired horse costs $7.50, and seed beans about $3.12½ more.",
                "Hoeing it would mean working from five in the morning until noon, all summer.",
            ],
            goal="The player decides what to do with the field and plants it (or doesn't). Use adjust_money for plowing or seed and spend_time for the labor.",
            thoreau_stance="Seven and a half dollars for plowing is too much. He'd spade a smaller patch himself and keep his afternoons free.",
            people=["A farmer with a horse and plow for hire"],
        ),
    ]
}

# The spine of the story, in order.
ANCHORS: list[str] = ["axe", "shanty", "cellar", "village_run", "raising", "roofing", "move_in", "beans"]


def side_beat(beat_id: str, season_index: int, title: str, premise: str, location: str) -> Beat:
    """A scene the game master invented."""
    return Beat(
        id=beat_id,
        season_index=season_index,
        title=title,
        location=location,
        situation=[premise],
        goal="Play out this scene the way you imagined it, then end it with a summary.",
        thoreau_stance="React as yourself.",
        side=True,
    )


def get_beat(beat_id: str, side_beats: dict[str, dict]) -> Beat:
    if beat_id in BEATS:
        return BEATS[beat_id]
    return Beat.model_validate(side_beats[beat_id])
