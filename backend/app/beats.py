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
    # Possible endings, each with the beats it leads to. If set, end_beat must name one.
    outcomes: dict[str, list[str]] = Field(default_factory=dict)
    branch: bool = False  # only reached through another beat's outcome
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
            goal=("The player decides what to do with the field and plants it (or doesn't). Use adjust_money for plowing "
                  "or seed and spend_time for the labor. End with outcome 'big_field' (two and a half acres or so), "
                  "'small_patch', or 'no_field'."),
            thoreau_stance="Seven and a half dollars for plowing is too much. He'd spade a smaller patch himself and keep his afternoons free.",
            people=["A farmer with a horse and plow for hire"],
            outcomes={"big_field": [], "small_patch": [], "no_field": []},
        ),
        # --- The night in jail (July 1846): a three-beat branch -------------------------
        Beat(
            id="jail_errand",
            season_index=5,
            title="The Shoemaker's Errand",
            when="Late July 1846",
            location="village",
            situation=[
                "Late July, 1846. The player has walked into Concord village to pick up a shoe left at the cobbler's for mending.",
                "Sam Staples steps into the road: Concord's constable, jailer and tax collector, a friendly man the player knows well.",
                "He's collecting overdue poll tax. The player hasn't paid it for several years: $6.00 is owed (a game price).",
                "The poll tax goes to the state of Massachusetts. The player, being Thoreau, believes that state upholds slavery and backs the war on Mexico.",
                "Staples has offered, half joking, to pay it himself if money's the trouble. If the player won't pay, the law says he has to lock them up.",
            ],
            goal=(
                "Resolve the tax. If the player pays (adjust_money -6.00, tag the conscience they're setting aside) or lets "
                "Staples pay for them, end with outcome 'paid'. If they refuse, Staples walks them to the jail across the "
                "square: end with outcome 'refused'."
            ),
            thoreau_stance=(
                "He will not pay. It isn't the money: he won't give a cent to a state that buys and sells men and makes war "
                "on Mexico. He'd rather go to jail, and he wants the player to feel why. Paying would wound him."
            ),
            people=["Sam Staples", "Townsfolk watching from the store porch", "The cobbler, with the mended shoe"],
            outcomes={"paid": [], "refused": ["jail_night", "huckleberries"]},
        ),
        Beat(
            id="jail_night",
            season_index=5,
            title="A Night in the Concord Jail",
            when="That night",
            location="The Middlesex County jail in Concord",
            branch=True,
            situation=[
                "A stone cell with an iron-grated window and a heavy oak door. Staples locked it himself.",
                "The player's cellmate is a quiet man awaiting trial, accused of burning a barn. He says he didn't do it: he fell asleep in it with his pipe.",
                "Through the window come the sounds of Concord at night: the town clock, voices and clatter from the inn kitchen next door.",
                "Sometime this evening, Staples returns with news: someone, a woman with her face veiled, has paid the player's tax. But Staples has his boots off and won't open up again until morning. Bring this in when the moment feels right.",
            ],
            goal=(
                "The night passes. Let the player talk with the cellmate, look out at the town, think, and talk to Thoreau. "
                "Bring in Staples's news partway through. Call spend_time for the night. End when morning comes."
            ),
            thoreau_stance=(
                "This is the most alive he's been. He feels freer in here than the men outside: the walls only hold his "
                "body. He's working out what conscience owes the state, and he wants to talk."
            ),
            people=["Sam Staples, the jailer", "The cellmate", "A veiled woman, never seen"],
        ),
        Beat(
            id="huckleberries",
            season_index=5,
            title="Huckleberries",
            when="The next morning",
            location="village",
            branch=True,
            situation=[
                "Morning. Staples brings breakfast and opens the door. The tax has been paid, and the player is free to go whether they like it or not.",
                "The mended shoe is still waiting at the cobbler's.",
                "A party of friends is heading out to pick huckleberries on a hill a couple of miles off, and they'd welcome a leader who knows the best bushes.",
                "The village looks different this morning.",
            ],
            goal="The player leaves the jail, finishes the errand if they like, and spends the day however they choose, ideally up among the huckleberries. End when the day settles.",
            thoreau_stance=(
                "He's furious that someone paid, and he refuses to let it spoil a good day. Within half an hour he'd rather "
                "be on a hill full of huckleberries than anywhere in the state of Massachusetts."
            ),
            people=["Sam Staples", "Friends bound for the huckleberry hill"],
        ),

        # --- Autumn 1845: before the frost ---------------------------------------------
        Beat(
            id="harvest",
            season_index=2,
            title="The Bean Harvest",
            when="September 1845",
            location="bean_field",
            situation=[
                "September. The beans are ripe. Woodchucks have taken their share, and the rows (if there are rows) stand dry and rattling.",
                "What there is to harvest depends on what the player planted this summer (see earlier_choices: beans).",
                "Thoreau's own big field gave twelve bushels of beans and eighteen of potatoes. Nine bushels and twelve quarts of beans sold for $16.94.",
                "A small hand-spaded patch gives enough to eat through the winter and perhaps $3 to $5 to sell (a game figure). No field means nothing to harvest.",
                "Beans sell in Concord village.",
            ],
            goal=("The player brings in whatever crop there is, and sells some or keeps it. Use spend_time for the "
                  "work and adjust_money (kind 'farm') for any sale, in the village. End when the harvest is in."),
            thoreau_stance=(
                "He's proud of knowing beans, and of how little he needed. The real profit, he says, is what the field "
                "taught him. He'd sell only what they won't eat, and he loves to tally the accounts afterward."
            ),
            people=["Farmers and buyers in Concord", "The woodchucks"],
        ),
        Beat(
            id="chimney",
            season_index=2,
            title="Fire and Plaster",
            when="November 1845",
            location="cabin",
            situation=[
                "November. The first frosts have come, and the house has no chimney. Nights are getting cold.",
                "A chimney needs bricks (a thousand old ones sell for $4.00 at the yard, and they must be cleaned), lime and a mantle-tree iron. Stones for the hearth can come from the pond shore, and sand from the bank.",
                "Plastering the walls needs laths, lime and hair, and it would keep the warmth in.",
                "If the house is drafty (shanty boards), plaster matters even more.",
            ],
            goal=(
                "The chimney gets built: call build('chimney') once the materials are in hand, and build('plaster') if the "
                "player plasters too. Missing materials mean a trip to Concord: show the trip_planner, or the player can walk there."
            ),
            thoreau_stance=(
                "A fire is the soul of a house. Building a chimney with your own hands, of second-hand brick and pond stones, "
                "is the most satisfying work there is. He'd rather plaster too, before the snow."
            ),
            requires_built=["chimney"],
        ),
        # --- Winter 1845-46 ------------------------------------------------------------
        Beat(
            id="freeze",
            season_index=3,
            title="The Pond Freezes",
            when="December 1845",
            location="pond",
            situation=[
                "December 22, 1845: Walden froze over in a single night. Now the ice booms and whoops in the dark like something alive.",
                "The woodpile is low. Fallen wood lies in the forest, waterlogged pitch-pine logs can be dragged across the ice, and old stumps can be dug for their resinous roots.",
                "Farmers sell cordwood in the village, for those who'd rather pay than haul.",
                "A drafty house (shanty boards, no plaster) burns through wood faster. Check house_quality and the house.",
            ],
            goal="The player lays in fuel for the winter, however they choose. Spend the hours honestly (more if the house is drafty). End when the woodpile will last.",
            thoreau_stance="Wood you gather yourself warms you twice: once in the cutting and once in the burning. Buying cordwood is folly when the forest is full of it.",
            people=["A farmer selling cordwood"],
        ),
        Beat(
            id="ice_cutters",
            season_index=3,
            title="The Ice-Cutters",
            when="January 1846",
            location="pond",
            situation=[
                "January. A hundred Irish laborers and their Yankee overseers have come with horses, plows and saws to harvest the ice of Walden.",
                "They cut it into blocks and stack it in a great pile on the shore. Some will be shipped as far as Charleston, New Orleans, Madras, Bombay and Calcutta.",
                "People in town insist that Walden has no bottom. Nobody has ever actually measured it.",
                "The overseer might pay for an extra pair of hands.",
            ],
            goal=(
                "The player spends time among the ice-cutters, or apart from them: watching, working, talking, or "
                "sounding the depth of the pond with a line and stone (it's 102 feet at its deepest). End when the cutters move on."
            ),
            thoreau_stance=(
                "They harvest the pond and he only looks at it; which of them takes the greater crop? He's delighted that "
                "Walden water will be drunk in India. He'd love to prove the bottomless pond has a bottom."
            ),
            people=["The ice-cutters", "Their overseer", "Townsfolk who swear the pond is bottomless"],
        ),
        Beat(
            id="former_inhabitants",
            season_index=3,
            title="Former Inhabitants",
            when="February 1846",
            location="woods",
            situation=[
                "February, deep snow. Walking the old road through the woods, the player passes the cellar holes of houses long gone, with lilacs still growing by their doors.",
                "These woods were home to people pushed to the edge of Concord: Cato Ingraham, enslaved by Duncan Ingraham; Zilpha, a free Black woman who spun linen, whose house was burned by English soldiers on parole in the War of 1812; Brister Freeman, once enslaved by Squire Cummings, and his wife Fenda, who told fortunes.",
                "There were others: the Breed family, and Wyman the potter.",
                "These were real people. Treat them with dignity, as lives, not scenery.",
            ],
            goal="The player walks among the ruins, learns who lived here, and reflects. End when they head home through the snow.",
            thoreau_stance=(
                "He's moved and a little ashamed: these were the woods' first free settlers, living on the margins the town "
                "allowed them, and his own experiment stands on their ground. He wants to remember them."
            ),
        ),
        # --- Spring 1846 ---------------------------------------------------------------
        Beat(
            id="thaw",
            season_index=4,
            title="The Thaw",
            when="Late March 1846",
            location="railroad",
            situation=[
                "The thaw. Along the deep cut where the railroad passes, the sand bank melts and flows down in branching shapes like leaves, veins and coral.",
                "Walden's ice is going out: rotten, gray, then gone in a day, usually in late March or early April.",
                "Geese go over, honking, and the first sparrow sings.",
            ],
            goal="The player witnesses the spring and decides what to make of the new year. End when the ice is out.",
            thoreau_stance="He's ecstatic. The earth isn't dead; it's alive and growing, and he's sure the whole world is made on the pattern of a leaf.",
        ),
        Beat(
            id="runaway",
            season_index=4,
            title="A Traveler Going North",
            when="May 1846",
            location="cabin",
            situation=[
                "A spring evening. A man escaping slavery arrives at the house, sent by friends in Concord. The Thoreau family, especially his mother and sisters, help people traveling the Underground Railroad.",
                "He has come a very long way. He needs food, rest, and help getting safely to the next stop on the way to Canada, likely by the railroad.",
                "Helping him is against federal law, and slave-catchers sometimes come north.",
                "He is a whole person with his own name, history, fears and plans. Let him speak for himself; never make him a prop or a lesson.",
                "Invent his name and story. Don't make him a known historical person (Thoreau never recorded who he helped).",
            ],
            goal=(
                "The player decides how to help, or not. End with outcome 'helped' if they helped him on his way, or "
                "'turned_away' if they didn't."
            ),
            thoreau_stance=(
                "There's no question for him: you help. This is what conscience means, and it's the same reason he won't pay "
                "the state its tax. He'd share everything he has, which isn't much."
            ),
            people=["The traveler", "Friends of the Thoreau family in Concord"],
            outcomes={"helped": [], "turned_away": []},
        ),
        # --- Summer 1846 ---------------------------------------------------------------
        Beat(
            id="therien",
            season_index=5,
            title="The Woodchopper",
            when="June 1846",
            location="woods",
            situation=[
                "June. Alek Therien, a Canadian woodchopper and post-maker about twenty-eight years old, works in the woods nearby. He can hole fifty posts in a day.",
                "He's cheerful from morning to night, eats woodchuck his dog catches, carries a pail of dinner, and laughs at almost anything.",
                "He can barely read, but he loves to hear Homer read aloud, and he asks big questions in the simplest way.",
            ],
            goal="The player spends time with Therien: working alongside him, talking, reading to him, or simply watching how he lives. End when he heads home.",
            thoreau_stance=(
                "He's fascinated. Here's a man with no ambition at all, perfectly content, and he can't decide whether "
                "Therien is wiser than all of Concord or has never woken up. He wants to find out."
            ),
            people=["Alek Therien", "His dog"],
        ),
        # --- Autumn 1846 ---------------------------------------------------------------
        Beat(
            id="baker_farm",
            season_index=6,
            title="Baker Farm",
            when="Autumn 1846",
            location="baker_farm",
            situation=[
                "Out fishing past Fair Haven, the player is caught in a sudden thunderstorm and runs for the nearest roof: John Field's hut at Baker Farm.",
                "John Field is a poor Irish laborer. He, his wife and several children, and the chickens, crowd into the leaky hut.",
                "He works bogging a meadow for a neighboring farmer at ten dollars an acre plus a year's use of the land, and he works very hard for very little.",
                "When the rain stops, a rainbow stands over the field. The only water to drink comes from a muddy well.",
            ],
            goal="The player shelters with the Fields, talks with them, and leaves when the storm passes. End when they're back out under the rainbow.",
            thoreau_stance=(
                "He can't help it: he wants to tell Field that if he gave up tea, coffee, butter and meat he wouldn't have to "
                "work so hard. He means it kindly, but he knows Field won't listen, and part of him knows he's being unfair."
            ),
            people=["John Field", "His wife", "Their children"],
        ),
        # --- Winter 1846-47 ------------------------------------------------------------
        Beat(
            id="second_winter",
            season_index=7,
            title="The Second Winter",
            when="Winter 1846–47",
            location="cabin",
            situation=[
                "The second winter. The player knows the woods and the cold now, and how much wood the house really needs.",
                "A small cast-iron cooking stove can be had in the village (about $5, a game price). It burns far less wood than the open fireplace.",
                "Visitors come through the snow: Ellery Channing, Bronson Alcott, and sometimes a farmer on the way past.",
            ],
            goal="The player gets through the second winter their own way. End when the days start to lengthen.",
            thoreau_stance=(
                "He's torn. The stove is real economy and he'll admit it, but he'd miss seeing a face in the fire. He's "
                "happiest when old friends tramp through the snow to talk until late."
            ),
            people=["Ellery Channing", "Bronson Alcott", "A passing farmer"],
        ),
        # --- 1847 ------------------------------------------------------------------------
        Beat(
            id="second_field",
            season_index=8,
            title="A Smaller Field",
            when="May 1847",
            location="bean_field",
            situation=[
                "Spring 1847. Last year's field taught its lessons (see earlier_choices: beans).",
                "Thoreau himself spaded only about a third of an acre the second year, having learned how little he needed.",
            ],
            goal="The player decides what to plant this year, and how much, and plants it. End when it's in the ground.",
            thoreau_stance="Plant only what we'll eat. He's proud of needing less every year, and a little smug about it.",
        ),
        Beat(
            id="leaving",
            season_index=9,
            title="Leaving the Woods",
            when="September 6, 1847",
            location="cabin",
            situation=[
                "September 1847. It's been two years, two months and two days since the Fourth of July, 1845.",
                "Emerson is about to sail for England to lecture, and Lidian Emerson has asked whether the player will come and stay with her and the children while he's away.",
                "A path is worn from the door to the pond. The house, the bean-field and the woodpile are all just as the player made them.",
            ],
            goal=(
                "The player decides whether to leave the woods, says goodbye in their own way, and goes (or stays). Look "
                "back over the story so far as you narrate. End with outcome 'left' or 'stayed'."
            ),
            thoreau_stance=(
                "He's ready, and he isn't sad: he has several more lives to live, and he wouldn't want to wear a rut into "
                "this one. He leaves the woods for as good a reason as he came."
            ),
            people=["Lidian Emerson, by letter or in person", "Friends who come to help carry things"],
            outcomes={"left": [], "stayed": []},
        ),
    ]
}

# The spine of the story, in order. (Branch beats are reached through outcomes.)
ANCHORS: list[str] = [
    "axe", "shanty", "cellar", "village_run", "raising", "roofing", "move_in", "beans",  # spring-summer 1845
    "harvest", "chimney",  # autumn 1845
    "freeze", "ice_cutters", "former_inhabitants",  # winter 1845-46
    "thaw", "runaway",  # spring 1846
    "therien", "jail_errand",  # summer 1846 (the jail branch follows a refusal)
    "baker_farm",  # autumn 1846
    "second_winter",  # winter 1846-47
    "second_field", "leaving",  # 1847
]


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
