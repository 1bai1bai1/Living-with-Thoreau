"""Picks the next beat.

Anchor beats (beats.ANCHORS) are the story's spine and always play. The
game master can queue side scenes it invents (propose_side_scene), which
play before the next anchor, a couple per season at most. The full game
will run between MIN_SCENES and MAX_SCENES.
"""

from . import rules
from .beats import ANCHORS, Beat, get_beat, side_beat
from .state import GameState

MIN_SCENES = 20
MAX_SCENES = 80
SIDE_SCENES_PER_SEASON = 2


def advance(state: GameState) -> Beat | None:
    """Move the state to its next beat and return it, or None when the
    story (for now, this slice) is over."""
    if state.scenes_played >= MAX_SCENES:
        return None
    if state.queued:
        beat_id = state.queued.pop(0)
    elif state.anchor_index < len(ANCHORS):
        beat_id = ANCHORS[state.anchor_index]
        state.anchor_index += 1
    else:
        return None

    beat = get_beat(beat_id, state.side_beats)
    while beat.season_index > state.season_index:
        rules.end_season(state)
    state.beat_id = beat.id
    state.beat_turns = 0
    state.beat_done = False
    state.beat_summary = None
    state.scenes_played += 1
    state.phase = "open"
    return beat


def propose_side_scene(state: GameState, title: str, premise: str, location: str) -> str:
    """Queue a scene the game master invented. Returns its id."""
    used = state.side_scenes_by_season.get(state.season_index, 0)
    if used >= SIDE_SCENES_PER_SEASON:
        raise rules.RuleError("This season already has its side scenes. Keep to the main story for now.")
    if state.scenes_played + len(state.queued) + 1 >= MAX_SCENES:
        raise rules.RuleError("There's no room left in the story for another scene.")
    beat_id = f"side_{len(state.side_beats) + 1}_{rules.slug(title)}"
    beat = side_beat(beat_id, state.season_index, title.strip()[:80], premise.strip()[:600], location.strip()[:80])
    state.side_beats[beat_id] = beat.model_dump()
    state.side_scenes_by_season[state.season_index] = used + 1
    state.queued.append(beat_id)
    return beat_id


def fast_forward(state: GameState, beat_id: str) -> None:
    """For testing: start a new game just before an anchor beat, as if the
    earlier scenes went the way Thoreau would have played them."""
    if beat_id not in ANCHORS:
        raise rules.RuleError(f"'{beat_id}' isn't a scene you can start from. Try: {', '.join(ANCHORS)}.")
    index = ANCHORS.index(beat_id)
    if index == 0:
        return
    for anchor in ANCHORS[:index]:
        state.history.append(f"{get_beat(anchor, {}).title}: (skipped for testing)")
    state.anchor_index = index
    if index > ANCHORS.index("axe"):
        state.items["timber"] = "Hewn pine timbers"
    if index > ANCHORS.index("shanty"):
        state.owned.update({"boards": "shanty", "nails": "salvage"})
        state.money -= 4250
    if index > ANCHORS.index("village_run"):
        state.owned.update({"shingles": "refuse", "windows": "secondhand", "hardware": "store"})
        state.money -= 6680
        state.village_trips = 1
    if index > ANCHORS.index("raising"):
        state.built.append("frame")
    if index > ANCHORS.index("roofing"):
        state.built.append("shell")
    state.scenes_played = index
