"""One player's game, held on the server.

A game runs for 20-80 scenes, so the server keeps each session's state
between requests (the reference Dungeon Master replayed every request from
the start instead). The model never writes here directly: it calls tools,
and rules.py decides what changes.
"""

from typing import Literal

from pydantic import BaseModel, Field

from .world import SEASONS, START_HAPPINESS, START_MILLS


class LedgerEntry(BaseModel):
    season: str
    label: str
    cost: int  # mills; positive = spent, negative = earned
    hours: int
    kind: Literal["house", "farm", "labor", "tools", "other"]


class GameState(BaseModel):
    session_id: str

    season_index: int = 0
    scenes_played: int = 0

    money: int = START_MILLS  # mills
    hours_left: int = SEASONS[0].hours
    hours_spent: int = 0
    happiness: int = START_HAPPINESS  # 0-100: how well Thoreau is actually living
    wants: int = 0  # superfluities acquired; each drains happiness every season
    drift: int = 0  # running sum of how Thoreau feels about your choices
    village_trips: int = 0

    location: str = "woods"
    location_name: str = "The woods around Walden"
    owned: dict[str, str] = Field(default_factory=dict)  # material id -> method id
    items: dict[str, str] = Field(default_factory=dict)  # anything else: key -> label
    built: list[str] = Field(default_factory=list)  # house stage ids
    ledger: list[LedgerEntry] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)  # one line per finished scene

    # Story flow (see director.py)
    anchor_index: int = 0
    queued: list[str] = Field(default_factory=list)  # beat ids to play before the next anchor
    side_beats: dict[str, dict] = Field(default_factory=dict)  # invented by the game master
    side_scenes_by_season: dict[int, int] = Field(default_factory=dict)
    beat_id: str | None = None
    beat_turns: int = 0
    beat_done: bool = False
    beat_summary: str | None = None
    beat_outcome: str | None = None
    outcomes: dict[str, str] = Field(default_factory=dict)  # beat id -> how it ended, for later scenes
    epilogue: str | None = None  # the ending, once written
    farewell: str | None = None  # Thoreau's last word, once said
    phase: Literal["between", "open", "approval"] = "between"
    finished: bool = False

    @property
    def season(self):
        return SEASONS[self.season_index]
