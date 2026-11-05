"""The fixed world: seasons, the village, and the house's materials.

Money is kept in *mills* (thousandths of a dollar) so Thoreau's half-cents
($28.12½) are exact. A price marked source="walden" is Thoreau's own figure
from *Walden* ("Economy" and "The Bean-Field"); "game" prices are ours.
The model never sets a price: it narrates what this module says is true.
"""

from typing import Literal

from pydantic import BaseModel


def mills(dollars: float) -> int:
    return round(dollars * 1000)


def fmt_money(m: int, signed: bool = False) -> str:
    """4125 -> "$4.12½", the way Thoreau wrote his accounts."""
    sign = "-" if m < 0 else ("+" if signed and m > 0 else "")
    m = abs(m)
    dollars, rem = divmod(m, 1000)
    cents, frac = divmod(rem, 10)
    half = "½" if frac >= 5 else ""
    return f"{sign}${dollars}.{cents:02d}{half}"


# --- Seasons ---------------------------------------------------------------

SeasonKey = Literal["spring", "summer", "autumn", "winter"]


class Season(BaseModel):
    index: int
    key: SeasonKey
    label: str
    hours: int  # hours of "life" to spend in this season; overwork costs happiness


SEASONS: list[Season] = [
    Season(index=0, key="spring", label="Spring 1845", hours=100),
    Season(index=1, key="summer", label="Summer 1845", hours=100),
    Season(index=2, key="autumn", label="Autumn 1845", hours=100),
    Season(index=3, key="winter", label="Winter 1845–46", hours=100),
    Season(index=4, key="spring", label="Spring 1846", hours=100),
    Season(index=5, key="summer", label="Summer 1846", hours=100),
    Season(index=6, key="autumn", label="Autumn 1846", hours=100),
    Season(index=7, key="winter", label="Winter 1846–47", hours=100),
    Season(index=8, key="spring", label="Spring 1847", hours=100),
    Season(index=9, key="summer", label="Summer 1847", hours=100),
]

START_MILLS = mills(20.00)
START_HAPPINESS = 50
MAX_HAPPINESS = 100


# --- Materials ---------------------------------------------------------------

Where = Literal["scene", "store", "yard"]


class Method(BaseModel):
    """One way to get a material."""

    id: str
    label: str
    cost: int  # mills
    hours: int
    where: Where  # "scene": only offered by a particular scene
    quality: Literal["rough", "sound"] = "sound"
    requires: str | None = None  # "material:method" you must already own
    note: str = ""
    source: Literal["walden", "game"] = "game"
    values: dict[str, int] = {}  # what choosing this says about you (see rules.THOREAU_WEIGHTS)


class Material(BaseModel):
    id: str
    name: str
    thoreau_cost: int  # what Thoreau's own ledger says he paid, in mills
    methods: list[Method]

    def method(self, method_id: str) -> Method | None:
        return next((m for m in self.methods if m.id == method_id), None)


def _mat(id, name, thoreau, methods) -> Material:
    return Material(id=id, name=name, thoreau_cost=mills(thoreau), methods=methods)


MATERIALS: dict[str, Material] = {
    m.id: m
    for m in [
        _mat("boards", "Boards", 8.035, [
            Method(id="shanty", label="Collins's shanty, taken apart", cost=mills(4.25), hours=8, where="scene",
                   quality="rough", note="Weathered boards to bleach and straighten in the sun.", source="walden",
                   values={"frugality": 2, "self_reliance": 1}),
            Method(id="new", label="Sawn boards from the yard", cost=mills(7.00), hours=1, where="yard",
                   note="Clean and square, and costly.", values={"convenience": 1, "frugality": -1}),
        ]),
        _mat("nails", "Nails", 3.90, [
            Method(id="store", label="Nails from the store", cost=mills(3.90), hours=0, where="store", source="walden"),
            Method(id="salvage", label="Pull and straighten the shanty's nails", cost=0, hours=5, where="scene",
                   requires="boards:shanty", note="Free, if you bought the shanty.",
                   values={"frugality": 1, "self_reliance": 1}),
        ]),
        _mat("shingles", "Shingles", 4.00, [
            Method(id="refuse", label="Refuse shingles", cost=mills(4.00), hours=1, where="yard",
                   note="Seconds, a little warped.", source="walden"),
        ]),
        _mat("windows", "Windows", 2.43, [
            Method(id="secondhand", label="Two second-hand windows with glass", cost=mills(2.43), hours=1,
                   where="yard", source="walden"),
        ]),
        _mat("hardware", "Hinges and latch", 0.25, [
            Method(id="store", label="Hinges, screws, a latch and chalk", cost=mills(0.25), hours=0, where="store",
                   source="walden"),
        ]),
        _mat("bricks", "Bricks", 4.00, [
            Method(id="old", label="A thousand old bricks", cost=mills(4.00), hours=6, where="yard",
                   note="Cheap, but they need cleaning, and you carry them.", source="walden"),
        ]),
        _mat("lime", "Lime", 2.40, [
            Method(id="casks", label="Two casks of lime", cost=mills(2.40), hours=1, where="yard",
                   note="Enough for the chimney and the plaster.", source="walden"),
        ]),
        _mat("hair", "Hair for plaster", 0.31, [
            Method(id="store", label="Hair, to bind the plaster", cost=mills(0.31), hours=0, where="store",
                   source="walden"),
        ]),
        _mat("mantle_iron", "Mantle-tree iron", 0.15, [
            Method(id="store", label="A mantle-tree iron", cost=mills(0.15), hours=0, where="store", source="walden"),
        ]),
        _mat("laths", "Laths", 1.25, [
            Method(id="store", label="Laths for the walls", cost=mills(1.25), hours=0, where="store", source="walden"),
        ]),
    ]
}

# Thoreau's house, all told: materials $26.72½ + transportation $1.40.
THOREAU_HOUSE_TOTAL = mills(28.125)
THOREAU_TRANSPORT = mills(1.40)


# --- The house -----------------------------------------------------------------


class Stage(BaseModel):
    id: str
    label: str
    weight: int  # share of "house %"
    materials: list[str] = []
    flags: list[str] = []


STAGES: list[Stage] = [
    Stage(id="frame", label="Frame", weight=25, flags=["timber"]),
    Stage(id="shell", label="Walls and roof", weight=45,
          materials=["boards", "nails", "shingles", "windows", "hardware"]),
    Stage(id="chimney", label="Chimney", weight=15, materials=["bricks", "lime", "mantle_iron"]),
    Stage(id="plaster", label="Plaster", weight=15, materials=["laths", "lime", "hair"]),
]
STAGE_BY_ID = {s.id: s for s in STAGES}


# --- The village (trip planner) ---------------------------------------------------


class Place(BaseModel):
    id: str
    name: str
    blurb: str
    kind: Literal["shop", "labor"]
    stop_hours: int
    pay: int = 0  # mills, for labor


PLACES: dict[str, Place] = {
    p.id: p
    for p in [
        Place(id="store", name="Concord general store", kind="shop", stop_hours=1,
              blurb="Nails, hinges, hair for plaster, laths and iron."),
        Place(id="yard", name="Lumber and brick yard", kind="shop", stop_hours=1,
              blurb="Shingles, second-hand windows, old bricks, lime and sawn boards."),
        Place(id="labor", name="A day's labor", kind="labor", stop_hours=9, pay=mills(1.00),
              blurb="Mending fences or carpentry for a farmer, about a dollar a day."),
    ]
}

# Two miles each way, by the road or along the railroad.
TRIP_WALK_HOURS = 4


# --- Places you can walk to -------------------------------------------------------


class Location(BaseModel):
    id: str
    name: str
    hours: int  # one-way walk from the house site


LOCATIONS: dict[str, Location] = {
    loc.id: loc
    for loc in [
        Location(id="cabin", name="Your house site at Walden Pond", hours=0),
        Location(id="pond", name="The shore of Walden Pond", hours=0),
        Location(id="bean_field", name="The bean-field", hours=0),
        Location(id="railroad", name="The Fitchburg Railroad, by the pond", hours=0),
        Location(id="woods", name="The woods around Walden", hours=1),
        Location(id="flints_pond", name="Flint's Pond", hours=1),
        Location(id="village", name="Concord village", hours=2),
        Location(id="emersons", name="Emerson's house in Concord", hours=2),
        Location(id="baker_farm", name="Baker Farm, past Fair Haven", hours=2),
    ]
}
